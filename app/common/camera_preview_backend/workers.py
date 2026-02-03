from __future__ import annotations

import sys
import time
from typing import Optional, Union

from loguru import logger
from PySide6.QtCore import QObject, Signal, Slot, QTimer, Qt

from app.common.camera_preview_backend.detection import (
    create_onnx_face_detector,
    detect_faces_onnx,
    list_onnx_model_filenames,
    resolve_onnx_model_path,
)


CameraSource = Union[int, str]


class OpenCVCaptureWorker(QObject):
    """从 OpenCV VideoCapture 读取帧的后台工作线程。"""

    frame_ready = Signal(object)
    error_occurred = Signal(str, str, str)
    opened = Signal(object)
    closed = Signal()

    def __init__(
        self,
        source: Optional[CameraSource],
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._source: CameraSource = 0 if source is None else source
        self._running = False
        self._pending_source: Optional[CameraSource] = None
        self._cap = None
        self._timer: Optional[QTimer] = None
        self._last_ok = 0.0
        self._consecutive_failures = 0
        self._last_emit = 0.0
        self._emit_interval_s = 1.0 / 20.0

        try:
            import cv2  # type: ignore

            self._cv2 = cv2
        except Exception as exc:
            self._cv2 = None
            logger.exception("OpenCV 导入失败: {}", exc)

    @Slot()
    def start(self) -> None:
        """在此线程的事件循环中开始捕获帧。"""
        if self._cv2 is None:
            self.error_occurred.emit(
                "opencv_missing", "OpenCV missing", "cv2 import failed"
            )
            return

        if self._running:
            return

        self._running = True
        self._last_ok = time.monotonic()
        self._consecutive_failures = 0
        self._last_emit = 0.0

        try:
            self._ensure_open(self._source)
        except Exception as exc:
            logger.exception("摄像头打开失败: {}", exc)
            self.error_occurred.emit(
                "camera_open_failed",
                "Failed to open camera",
                str(exc),
            )
            self._running = False
            self._release()
            return

        if self._timer is None:
            self._timer = QTimer(self)
            self._timer.setTimerType(Qt.TimerType.PreciseTimer)
            self._timer.timeout.connect(self._read_once)
        self._timer.start(15)

    @Slot()
    def stop(self) -> None:
        """停止捕获并释放摄像头。"""
        self._running = False
        timer = self._timer
        if timer is not None and timer.isActive():
            timer.stop()
        self._release()

    @Slot(object)
    def request_source_change(self, source: object) -> None:
        """请求切换摄像头源。"""
        if source is None:
            self._pending_source = 0
            return
        if isinstance(source, (int, str)):
            self._pending_source = source
            return
        self._pending_source = 0

    @Slot()
    def _read_once(self) -> None:
        if not self._running:
            self.stop()
            return

        pending = self._pending_source
        if pending is not None:
            self._pending_source = None
            try:
                self._switch_source(pending)
            except Exception as exc:
                logger.exception("摄像头切换失败: {}", exc)
                self.error_occurred.emit(
                    "camera_open_failed",
                    "Failed to open camera",
                    str(exc),
                )
                self.stop()
                return

        cap = self._cap
        if cap is None:
            self._consecutive_failures += 1
            if (
                time.monotonic() - self._last_ok > 2.0
                or self._consecutive_failures >= 20
            ):
                self.error_occurred.emit(
                    "camera_open_failed",
                    "Frame read timeout",
                    "Failed to read frames from camera",
                )
                self.stop()
            return

        ok, frame = cap.read()
        if not ok or frame is None:
            self._consecutive_failures += 1
            if (
                time.monotonic() - self._last_ok > 2.0
                or self._consecutive_failures >= 20
            ):
                self.error_occurred.emit(
                    "camera_open_failed",
                    "Frame read timeout",
                    "Failed to read frames from camera",
                )
                self.stop()
            return

        try:
            h, w = frame.shape[:2]
            if int(w) != 640 or int(h) != 480:
                frame = self._cv2.resize(frame, (640, 480))  # type: ignore[union-attr]
        except Exception:
            pass

        self._consecutive_failures = 0
        self._last_ok = time.monotonic()
        now = time.monotonic()
        if self._last_emit <= 0.0 or (now - self._last_emit) >= self._emit_interval_s:
            self._last_emit = now
            self.frame_ready.emit(frame)

    def _ensure_open(self, source: CameraSource) -> None:
        if self._cap is not None:
            return
        self._cap = self._open_capture(source)
        if self._cap is None:
            raise RuntimeError(f"OpenCV VideoCapture open failed: {source!r}")
        self.opened.emit(source)

    def _switch_source(self, source: CameraSource) -> None:
        self._release()
        self._source = source
        self._cap = self._open_capture(source)
        if self._cap is None:
            raise RuntimeError(f"OpenCV VideoCapture open failed: {source!r}")
        self.opened.emit(source)

    def _open_capture(self, source: CameraSource):
        cv2 = self._cv2
        if cv2 is None:
            return None

        backend_candidates: list[int] = []
        if isinstance(source, int):
            if sys.platform.startswith("win"):
                backend_candidates = [
                    getattr(cv2, "CAP_DSHOW", cv2.CAP_ANY),
                    getattr(cv2, "CAP_MSMF", cv2.CAP_ANY),
                    cv2.CAP_ANY,
                ]
            elif sys.platform.startswith("linux"):
                backend_candidates = [
                    getattr(cv2, "CAP_V4L2", cv2.CAP_ANY),
                    cv2.CAP_ANY,
                ]
            elif sys.platform == "darwin":
                backend_candidates = [
                    getattr(cv2, "CAP_AVFOUNDATION", cv2.CAP_ANY),
                    cv2.CAP_ANY,
                ]
            else:
                backend_candidates = [cv2.CAP_ANY]
        else:
            backend_candidates = [cv2.CAP_ANY]

        for backend in backend_candidates:
            try:
                if backend == cv2.CAP_ANY:
                    cap = cv2.VideoCapture(source)
                else:
                    cap = cv2.VideoCapture(source, backend)
            except Exception:
                continue

            if cap is None or not cap.isOpened():
                try:
                    if cap is not None:
                        cap.release()
                except Exception:
                    pass
                continue

            try:
                cap.set(getattr(cv2, "CAP_PROP_BUFFERSIZE", 38), 1)
            except Exception:
                pass
            try:
                cap.set(getattr(cv2, "CAP_PROP_FRAME_WIDTH", 3), 640)
                cap.set(getattr(cv2, "CAP_PROP_FRAME_HEIGHT", 4), 480)
            except Exception:
                pass

            return cap

        return None

    def _release(self) -> None:
        cap = self._cap
        self._cap = None
        if cap is None:
            return
        try:
            cap.release()
        except Exception as exc:
            logger.exception("摄像头释放失败: {}", exc)
        self.closed.emit()


class FaceDetectorWorker(QObject):
    faces_ready = Signal(object)
    error_occurred = Signal(str, str, str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._enabled = False
        self._model_filename = ""
        self._last_detect = 0.0
        self._last_load_attempt = 0.0

        self._detector_state = None

        try:
            import cv2  # type: ignore

            self._cv2 = cv2
        except Exception as exc:
            self._cv2 = None
            logger.exception("OpenCV 导入失败: {}", exc)

    @Slot(bool)
    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)

    @Slot(object)
    def set_model_filename(self, model_filename: object) -> None:
        value = ""
        try:
            value = str(model_filename).strip() if model_filename is not None else ""
        except Exception:
            value = ""
        if value.isdigit():
            value = ""
        if value == self._model_filename:
            return
        self._model_filename = value
        self._detector_state = None
        self._last_load_attempt = 0.0

    @Slot()
    def ensure_loaded(self) -> None:
        if self._cv2 is None:
            self.error_occurred.emit(
                "opencv_missing", "OpenCV missing", "cv2 import failed"
            )
            return
        now = time.monotonic()
        if now - self._last_load_attempt < 2.0:
            return
        self._last_load_attempt = now
        if self._detector_state is not None:
            return

        filename = self._model_filename
        if not filename:
            candidates = list_onnx_model_filenames()
            if not candidates:
                self.error_occurred.emit(
                    "model_missing",
                    "Model missing",
                    "No ONNX models found in data/cv_models",
                )
                return
            filename = candidates[0]

        try:
            model_path = resolve_onnx_model_path(filename)
        except FileNotFoundError as exc:
            logger.exception("模型缺失: {}", exc)
            self._detector_state = None
            self.error_occurred.emit("model_missing", "Model missing", str(exc))
            return

        try:
            self._detector_state = create_onnx_face_detector(model_path=model_path)
        except Exception as exc:
            logger.exception("模型不兼容: {}", exc)
            self._detector_state = None
            self.error_occurred.emit(
                "model_incompatible", "Model incompatible", str(exc)
            )

    @Slot(object)
    def process_frame(self, frame_bgr) -> None:
        if not self._enabled:
            return
        if self._cv2 is None:
            return

        now = time.monotonic()
        if now - self._last_detect < 0.05:
            return
        self._last_detect = now

        self.ensure_loaded()

        try:
            state = self._detector_state
            if state is None:
                return
            results = detect_faces_onnx(frame_bgr, detector_state=state)
        except Exception as exc:
            logger.exception("人脸检测失败: {}", exc)
            key = "detect_failed"
            msg = str(exc)
            if (
                "Unsupported ONNX model outputs" in msg
                or "Invalid detector state" in msg
            ):
                key = "model_incompatible"
            self.error_occurred.emit(key, "Face detection failed", msg)
            return

        self.faces_ready.emit(results)
