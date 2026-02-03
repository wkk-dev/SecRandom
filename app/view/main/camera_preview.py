from __future__ import annotations

import os
import random
from typing import Optional

from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *
from qfluentwidgets import *
from loguru import logger

from app.Language.obtain_language import (
    get_content_description_async,
    get_content_name_async,
    get_content_pushbutton_name_async,
)

from app.common.camera_preview_backend import (
    list_camera_devices,
    OpenCVCaptureWorker,
    FaceDetectorWorker,
    bgr_frame_to_qimage,
)
from app.common.camera_preview_backend.audio_player import camera_preview_audio_player
from app.tools.settings_access import get_settings_signals, readme_settings_async


class CameraPreview(QWidget):
    """带有 OpenCV 捕获和 ONNX 人脸检测的摄像头预览页面。"""

    camera_source_change_requested = Signal(object)
    capture_stop_requested = Signal()
    detector_enabled_changed = Signal(bool)
    detector_type_changed = Signal(object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._devices = []
        self._detection_active = False
        self._has_face_once = False
        self._overlay_rects: list[tuple[int, int, int, int]] = []
        self._overlay_colors: list[QColor] = []
        self._overlay_circles: list[tuple[int, int, int]] = []
        self._latest_frame = None
        self._latest_qimage: Optional[QImage] = None
        self._latest_faces: list[tuple[int, int, int, int]] = []
        self._picker_color: QColor = QColor()
        self._picking_active: bool = False
        self._picking_started: bool = False
        self._picking_step: int = 0
        self._picking_total_steps: int = 32
        self._picking_duration_ms: int = 2000
        self._final_view_active: bool = False
        self._final_selected_rect: Optional[tuple[int, int, int, int]] = None
        self._final_face_pixmap: Optional[QPixmap] = None
        self._audio_loop_started: bool = False
        self._play_process_audio: bool = True
        self._play_result_audio: bool = True
        self._frame_pipeline_connected: bool = False
        self._pick_count: int = 1
        self._pick_max_count: int = 1
        self._pick_minus_button: Optional[QPushButton] = None
        self._pick_plus_button: Optional[QPushButton] = None
        self._pick_count_label: Optional[QLabel] = None
        self._target_pick_count: int = 1
        self._picked_faces: list[tuple[int, int, int, int]] = []
        self._picked_face_pixmaps: list[QPixmap] = []
        self._current_pick_rect: Optional[tuple[int, int, int, int]] = None
        self._commit_pending: bool = False
        self._commit_index: int = 0

        self._capture_thread: Optional[QThread] = None
        self._capture_worker: Optional[OpenCVCaptureWorker] = None
        self._detector_thread: Optional[QThread] = None
        self._detector_worker: Optional[FaceDetectorWorker] = None

        self._clear_timer = QTimer(self)
        self._clear_timer.setSingleShot(True)
        self._clear_timer.timeout.connect(self._stop_detection_and_reset)

        self._no_face_timer = QTimer(self)
        self._no_face_timer.setSingleShot(True)
        self._no_face_timer.timeout.connect(self._on_no_face_timeout)

        self._picking_timer = QTimer(self)
        self._picking_timer.setSingleShot(True)
        self._picking_timer.timeout.connect(self._on_picking_tick)

        self._final_view_timer = QTimer(self)
        self._final_view_timer.setSingleShot(True)
        self._final_view_timer.timeout.connect(self._stop_detection_and_reset)

        self._init_ui()
        self._init_workers()

    def _disconnect_frame_pipeline(self) -> None:
        if self._capture_worker is None:
            self._frame_pipeline_connected = False
            return
        if not self._frame_pipeline_connected:
            return
        try:
            self._capture_worker.frame_ready.disconnect()
        except Exception:
            pass
        self._frame_pipeline_connected = False

    def _connect_frame_pipeline(self) -> None:
        if self._capture_worker is None:
            return
        if self._frame_pipeline_connected:
            return
        try:
            self._capture_worker.frame_ready.connect(self._on_frame_received)
        except Exception:
            pass
        if self._detector_worker is not None:
            try:
                self._capture_worker.frame_ready.connect(
                    self._detector_worker.process_frame
                )
            except Exception:
                pass
        self._frame_pipeline_connected = True

    def _init_ui(self) -> None:
        """初始化 UI 组件。"""
        self.setObjectName("cameraPreviewPage")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)

        self.preview_label = QLabel(self)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.preview_label.setMinimumHeight(320)
        self.preview_label.setStyleSheet(
            "QLabel { background: rgba(0,0,0,0.35); border-radius: 8px; }"
        )

        self._camera_opacity_effect = QGraphicsOpacityEffect(self.preview_label)
        self._camera_opacity_effect.setOpacity(1.0)
        self.preview_label.setGraphicsEffect(self._camera_opacity_effect)

        self.result_label = QLabel(self)
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.result_label.setMinimumHeight(320)
        self.result_label.setStyleSheet(
            "QLabel { background: rgba(0,0,0,0.35); border-radius: 8px; }"
        )

        self.preview_container = QWidget(self)
        self.preview_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.preview_stack = QStackedLayout(self.preview_container)
        self.preview_stack.setContentsMargins(0, 0, 0, 0)
        self.preview_stack.addWidget(self.preview_label)
        self.preview_stack.addWidget(self.result_label)
        self.preview_stack.setCurrentWidget(self.preview_label)

        controls = QWidget(self)
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)

        self.start_button = PrimaryPushButton(
            get_content_pushbutton_name_async("camera_preview", "start_button"),
            self,
        )
        self.start_button.setFixedWidth(180)
        self.start_button.clicked.connect(self._on_start_clicked)

        self._pick_minus_button = QPushButton("-")
        self._pick_plus_button = QPushButton("+")
        self._pick_count_label = QLabel("1")
        self._pick_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._pick_minus_button.setFixedHeight(38)
        self._pick_plus_button.setFixedHeight(38)
        self._pick_count_label.setFixedHeight(38)
        self._pick_count_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        self._pick_minus_button.clicked.connect(lambda: self._change_pick_count(-1))
        self._pick_plus_button.clicked.connect(lambda: self._change_pick_count(1))

        pick_count_widget = QWidget(self)
        pick_count_widget.setFixedWidth(180)
        pick_layout = QHBoxLayout(pick_count_widget)
        pick_layout.setContentsMargins(0, 0, 0, 0)
        pick_layout.setSpacing(0)
        pick_layout.addWidget(self._pick_minus_button)
        pick_layout.addStretch(1)
        pick_layout.addWidget(self._pick_count_label)
        pick_layout.addStretch(1)
        pick_layout.addWidget(self._pick_plus_button)
        self._apply_pick_count_limits()

        self.camera_combo = ComboBox(self)
        self.camera_combo.setFixedWidth(180)
        self.camera_combo.currentIndexChanged.connect(self._on_camera_changed)

        controls_layout.addWidget(self.start_button, 0, Qt.AlignmentFlag.AlignRight)
        controls_layout.addWidget(pick_count_widget, 0, Qt.AlignmentFlag.AlignRight)
        controls_layout.addWidget(self.camera_combo, 0, Qt.AlignmentFlag.AlignRight)

        bottom = QWidget(self)
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(controls, 0, Qt.AlignmentFlag.AlignRight)

        main_layout.addWidget(self.preview_container, 1)
        main_layout.addWidget(bottom, 0)

    def _init_workers(self) -> None:
        """初始化摄像头捕获和检测工作线程。"""
        try:
            import cv2

            _ = cv2.__version__
        except Exception as exc:
            logger.exception("OpenCV 导入失败: {}", exc)
            self._show_message("opencv_missing", details=str(exc))
            self.start_button.setEnabled(False)
            self.camera_combo.setEnabled(False)
            self.preview_label.setText(
                get_content_description_async("camera_preview", "unavailable")
            )
            return

        try:
            import numpy

            _ = numpy.__version__
        except Exception as exc:
            logger.exception("NumPy 导入失败: {}", exc)
            self._show_message("numpy_missing", details=str(exc))
            self.start_button.setEnabled(False)
            self.camera_combo.setEnabled(False)
            self.preview_label.setText(
                get_content_description_async("camera_preview", "unavailable")
            )
            return

        os.environ.setdefault("OPENCV_VIDEOIO_PRIORITY_MSMF", "0")

        self._devices = list_camera_devices()
        if not self._devices:
            self.start_button.setEnabled(False)
            self.camera_combo.setEnabled(False)
            self.preview_label.setText(
                get_content_description_async("camera_preview", "no_camera")
            )
            self._show_message("no_camera")
            return

        self.camera_combo.blockSignals(True)
        self.camera_combo.clear()
        for index, device in enumerate(self._devices):
            self.camera_combo.addItem(device.name)
            try:
                self.camera_combo.setItemData(index, device.source)
            except Exception:
                pass
        self.camera_combo.setCurrentIndex(0)
        self.camera_combo.blockSignals(False)

        default_source = None
        try:
            default_source = self.camera_combo.currentData()
        except Exception:
            default_source = None
        if default_source is None:
            try:
                default_source = self.camera_combo.itemData(0)
            except Exception:
                default_source = None
        if default_source is None and self._devices:
            default_source = self._devices[0].source

        self._capture_thread = QThread(self)
        self._capture_worker = OpenCVCaptureWorker(default_source)
        self._capture_worker.moveToThread(self._capture_thread)
        self._capture_thread.started.connect(self._capture_worker.start)
        self.capture_stop_requested.connect(self._capture_worker.stop)
        self.camera_source_change_requested.connect(
            self._capture_worker.request_source_change
        )
        self._capture_worker.error_occurred.connect(self._on_worker_error)

        self._detector_thread = QThread(self)
        detector_type = readme_settings_async("face_detector_settings", "detector_type")
        self._detector_worker = FaceDetectorWorker()
        self._detector_worker.set_model_filename(detector_type)
        self._detector_worker.moveToThread(self._detector_thread)
        self._detector_thread.started.connect(self._detector_worker.ensure_loaded)
        self.detector_enabled_changed.connect(self._detector_worker.set_enabled)
        self.detector_type_changed.connect(self._detector_worker.set_model_filename)
        self._detector_worker.faces_ready.connect(self._on_faces_detected)
        self._detector_worker.error_occurred.connect(self._on_worker_error)

        try:
            get_settings_signals().settingChanged.connect(self._on_setting_changed)
        except Exception:
            pass

        try:
            self._detector_thread.start()
            self._capture_thread.start()
        except Exception as exc:
            logger.exception("启动摄像头线程失败: {}", exc)
            self._show_message("unavailable", details=str(exc))
            self.start_button.setEnabled(False)
            self.camera_combo.setEnabled(False)
            return

        self._connect_frame_pipeline()

    def _on_start_clicked(self) -> None:
        """启动人脸检测流程。"""
        if self._detector_worker is None or self._capture_worker is None:
            self._show_message("unavailable")
            return

        try:
            v = readme_settings_async(
                "face_detector_settings", "picking_duration_seconds"
            )
            seconds = int(v) if v is not None else 2
            seconds = max(1, min(seconds, 10))
            self._picking_duration_ms = int(seconds * 1000)
        except Exception:
            self._picking_duration_ms = 2000

        try:
            v = readme_settings_async("face_detector_settings", "play_process_audio")
            self._play_process_audio = True if v is None else bool(v)
        except Exception:
            self._play_process_audio = True

        try:
            v = readme_settings_async("face_detector_settings", "play_result_audio")
            self._play_result_audio = True if v is None else bool(v)
        except Exception:
            self._play_result_audio = True

        self.start_button.setEnabled(False)
        self._detection_active = True
        self._has_face_once = False
        self._overlay_rects = []
        self._overlay_colors = []
        self._overlay_circles = []
        self._latest_faces = []
        self._picker_color = QColor()
        self._picking_active = True
        self._picking_started = False
        self._picking_step = 0
        self._final_view_active = False
        self._final_selected_rect = None
        self._final_face_pixmap = None
        self._audio_loop_started = False
        self._picked_faces = []
        self._picked_face_pixmaps = []
        self._current_pick_rect = None
        self._commit_pending = False
        self._commit_index = 0
        self._target_pick_count = (
            int(self._pick_count) if int(self._pick_count) > 0 else 1
        )
        self._connect_frame_pipeline()
        try:
            self._camera_opacity_effect.setOpacity(1.0)
        except Exception:
            pass
        try:
            self.result_label.clear()
        except Exception:
            pass
        try:
            self.preview_stack.setCurrentWidget(self.preview_label)
        except Exception:
            pass
        self.detector_enabled_changed.emit(True)

        self._no_face_timer.start(10_000)

    def _on_setting_changed(
        self, first_level_key: str, second_level_key: str, value: object
    ) -> None:
        if first_level_key != "face_detector_settings":
            return
        if second_level_key != "detector_type":
            return
        self.detector_type_changed.emit(value)

    def _stop_detection_and_reset(self) -> None:
        """停止检测，清除覆盖层，并恢复 UI 状态。"""
        self._detection_active = False
        self.detector_enabled_changed.emit(False)
        self._overlay_rects = []
        self._overlay_colors = []
        self._overlay_circles = []
        self._picking_active = False
        self._picking_started = False
        self._picking_timer.stop()
        self._final_view_timer.stop()
        self._final_view_active = False
        self._final_selected_rect = None
        self._final_face_pixmap = None
        self._picked_faces = []
        self._picked_face_pixmaps = []
        self._current_pick_rect = None
        self._commit_pending = False
        self._commit_index = 0
        self._connect_frame_pipeline()
        try:
            self._camera_opacity_effect.setOpacity(1.0)
        except Exception:
            pass
        try:
            self.result_label.clear()
        except Exception:
            pass
        try:
            self.preview_stack.setCurrentWidget(self.preview_label)
        except Exception:
            pass
        if self._audio_loop_started:
            try:
                camera_preview_audio_player.stop(wait=False)
            except Exception:
                pass
            self._audio_loop_started = False
        self.start_button.setEnabled(True)

    def _on_no_face_timeout(self) -> None:
        """处理短时间内未检测到人脸的情况。"""
        if not self._detection_active or self._has_face_once:
            return

        self._stop_detection_and_reset()
        self._show_message("no_face_detected")

    def _on_camera_changed(self, _index: int) -> None:
        """切换当前摄像头设备。"""
        if self._capture_worker is None:
            return

        self._stop_detection_and_reset()
        self._no_face_timer.stop()
        self._clear_timer.stop()

        source = None
        try:
            source = self.camera_combo.currentData()
        except Exception:
            source = None
        if source is None:
            try:
                source = self.camera_combo.itemData(self.camera_combo.currentIndex())
            except Exception:
                source = None
        if source is None and self._devices:
            source = self._devices[0].source
        if source is None:
            self._show_message("camera_open_failed")
            return
        self.camera_source_change_requested.emit(source)

    def _on_frame_received(self, frame_bgr) -> None:
        """在 UI 中渲染新帧。"""
        self._latest_frame = frame_bgr
        try:
            if self.preview_stack.currentWidget() is not self.preview_label:
                return
        except Exception:
            pass
        try:
            qimage = bgr_frame_to_qimage(frame_bgr)
        except Exception as exc:
            logger.exception("帧转换失败: {}", exc)
            return
        self._latest_qimage = qimage

        pixmap = QPixmap.fromImage(qimage)
        if self._detection_active and self._overlay_circles:
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.fillRect(
                QRect(0, 0, pixmap.width(), pixmap.height()),
                QColor(0, 0, 0, 110),
            )
            for circle, color in zip(
                self._overlay_circles, self._overlay_colors, strict=True
            ):
                pen = QPen(color, 6)
                painter.setPen(pen)
                cx, cy, r = circle
                painter.drawEllipse(QPointF(float(cx), float(cy)), float(r), float(r))
            painter.end()

        target = self.preview_label.size()
        if target.width() > 0 and target.height() > 0:
            pixmap = pixmap.scaled(
                target,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self.preview_label.setPixmap(pixmap)

    def _update_result_pixmap(self) -> None:
        pix = self._final_face_pixmap
        if pix is None:
            return
        target = self.result_label.size()
        if target.width() <= 0 or target.height() <= 0:
            return
        scaled = pix.scaled(
            target,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.result_label.setPixmap(scaled)

    def resizeEvent(self, event: QResizeEvent) -> None:
        try:
            if self.preview_stack.currentWidget() is self.result_label:
                self._update_result_pixmap()
        except Exception:
            pass
        super().resizeEvent(event)

    def _on_faces_detected(self, rects: list[tuple[int, int, int, int]]) -> None:
        """从检测线程接收人脸矩形。"""
        if not self._detection_active:
            return

        self._latest_faces = rects or []
        self._pick_max_count = max(1, len(self._latest_faces))
        self._apply_pick_count_limits()

        if (
            self._commit_pending
            and self._current_pick_rect is not None
            and self._latest_faces
        ):
            best = self._find_best_match_rect(
                self._current_pick_rect, self._latest_faces
            )
            if best is not None:
                self._current_pick_rect = best
        if self._picking_active and not self._picking_started and self._latest_faces:
            self._has_face_once = True
            self._no_face_timer.stop()
            self._picking_started = True
            self._picking_step = 0
            self._load_picker_settings()
            if self._play_process_audio and not self._audio_loop_started:
                try:
                    started = camera_preview_audio_player.play(
                        "face/process.wav", loop=True, volume=1.0
                    )
                    self._audio_loop_started = True if started else False
                except Exception:
                    self._audio_loop_started = False
            self._schedule_next_pick_tick()

    def _on_worker_error(self, key: str, _title: str, details: str) -> None:
        """处理来自工作线程的错误。"""
        logger.error("CameraPreview 工作线程错误 {}: {}", key, details)
        self._stop_detection_and_reset()
        self._show_message(key, details=details)

    def _change_pick_count(self, change: int) -> None:
        try:
            self._pick_count = int(self._pick_count) + int(change)
        except Exception:
            self._pick_count = 1
        self._apply_pick_count_limits()

    def _apply_pick_count_limits(self) -> None:
        max_count = int(self._pick_max_count) if int(self._pick_max_count) > 0 else 1
        try:
            self._pick_count = int(self._pick_count)
        except Exception:
            self._pick_count = 1
        self._pick_count = max(1, min(self._pick_count, max_count))

        if self._pick_count_label is not None:
            self._pick_count_label.setText(str(self._pick_count))
        if self._pick_minus_button is not None:
            self._pick_minus_button.setEnabled(self._pick_count > 1)
        if self._pick_plus_button is not None:
            self._pick_plus_button.setEnabled(self._pick_count < max_count)

    def _rect_iou(
        self, a: tuple[int, int, int, int], b: tuple[int, int, int, int]
    ) -> float:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        ax2 = ax + aw
        ay2 = ay + ah
        bx2 = bx + bw
        by2 = by + bh

        ix1 = max(ax, bx)
        iy1 = max(ay, by)
        ix2 = min(ax2, bx2)
        iy2 = min(ay2, by2)
        iw = ix2 - ix1
        ih = iy2 - iy1
        if iw <= 0 or ih <= 0:
            return 0.0
        inter = float(iw * ih)
        union = float(aw * ah + bw * bh - inter)
        if union <= 0:
            return 0.0
        return inter / union

    def _find_best_match_rect(
        self,
        anchor: tuple[int, int, int, int],
        rects: list[tuple[int, int, int, int]],
        min_iou: float = 0.15,
    ) -> Optional[tuple[int, int, int, int]]:
        best_rect: Optional[tuple[int, int, int, int]] = None
        best_score = 0.0
        for rect in rects:
            score = self._rect_iou(anchor, rect)
            if score > best_score:
                best_score = score
                best_rect = rect
        if best_rect is None or best_score < float(min_iou):
            return None
        return best_rect

    def _load_picker_settings(self) -> None:
        try:
            value = readme_settings_async(
                "face_detector_settings", "picker_frame_color"
            )
            text = str(value).strip() if value is not None else ""
            c = QColor(text) if text else QColor()
            if not c.isValid():
                c = QColor(
                    random.randint(20, 235),
                    random.randint(20, 235),
                    random.randint(20, 235),
                )
            self._picker_color = c
        except Exception:
            self._picker_color = QColor(
                random.randint(20, 235),
                random.randint(20, 235),
                random.randint(20, 235),
            )

    def _compute_circle_from_rect(
        self, rect: tuple[int, int, int, int]
    ) -> tuple[int, int, int]:
        x, y, w, h = rect
        cx = int(x + w / 2)
        cy = int(y + h / 2)
        r = int(max(w, h) / 2) + 4
        return cx, cy, r

    def _schedule_next_pick_tick(self) -> None:
        if not self._picking_active or not self._picking_started:
            return
        total = int(self._picking_total_steps)
        duration = int(self._picking_duration_ms)
        if total <= 0:
            total = 1
        if duration <= 0:
            duration = 2000
        interval_ms = int(round(duration / float(total)))
        self._picking_timer.start(max(10, interval_ms))

    def _on_picking_tick(self) -> None:
        if (
            not self._detection_active
            or not self._picking_active
            or not self._picking_started
        ):
            return
        candidates = self._latest_faces or []
        if not candidates:
            self._schedule_next_pick_tick()
            return

        if self._commit_pending:
            self._commit_locked_face()
            return

        if self._picking_step >= self._picking_total_steps - 1:
            self._begin_commit_sequence(candidates)
            return

        rect = random.choice(candidates)
        self._set_overlay_for_rect(rect)
        self._picking_step += 1
        self._schedule_next_pick_tick()

    def _set_overlay_for_rect(self, rect: tuple[int, int, int, int]) -> None:
        self._current_pick_rect = rect
        self._overlay_circles = [self._compute_circle_from_rect(rect)]
        self._overlay_colors = [
            self._picker_color
            if self._picker_color.isValid()
            else QColor(255, 255, 255)
        ]

    def _begin_commit_sequence(
        self, candidates: list[tuple[int, int, int, int]]
    ) -> None:
        target = int(self._target_pick_count) if int(self._target_pick_count) > 0 else 1
        target = max(1, min(target, len(candidates) if candidates else 1))

        try:
            selected = random.sample(list(candidates), k=target)
        except Exception:
            selected = [random.choice(candidates)]

        self._picked_faces = list(selected)
        self._picked_face_pixmaps = []
        self._commit_index = 0
        self._commit_pending = True
        self._lock_current_commit_target()

    def _lock_current_commit_target(self) -> None:
        if self._commit_index >= len(self._picked_faces):
            self._finish_commit_sequence()
            return
        rect = self._picked_faces[self._commit_index]
        self._set_overlay_for_rect(rect)
        self._picking_timer.start(220)

    def _commit_locked_face(self) -> None:
        if self._commit_index >= len(self._picked_faces):
            self._finish_commit_sequence()
            return

        rect = self._current_pick_rect or self._picked_faces[self._commit_index]

        qimage: Optional[QImage] = None
        try:
            if self._latest_frame is not None:
                qimage = bgr_frame_to_qimage(self._latest_frame)
        except Exception:
            qimage = None
        if (
            qimage is None
            and self._latest_qimage is not None
            and not self._latest_qimage.isNull()
        ):
            qimage = self._latest_qimage

        if qimage is not None:
            try:
                self._picked_face_pixmaps.append(self._crop_face_pixmap(qimage, rect))
            except Exception:
                pass

        self._commit_index += 1
        self._lock_current_commit_target()

    def _finish_commit_sequence(self) -> None:
        self._commit_pending = False
        self._picking_active = False
        self._picking_timer.stop()
        self._overlay_circles = []
        self._overlay_colors = []

        pixmap = self._compose_result_pixmap(self._picked_face_pixmaps)
        rect = self._picked_faces[0] if self._picked_faces else None
        self._show_final_result(pixmap, rect)

    def _compose_result_pixmap(self, pixmaps: list[QPixmap]) -> Optional[QPixmap]:
        items = [p for p in pixmaps if p is not None and not p.isNull()]
        if not items:
            return None
        if len(items) == 1:
            return items[0]

        import math

        count = len(items)
        cols = int(math.ceil(math.sqrt(count)))
        rows = int(math.ceil(count / float(cols)))
        cell = 240
        spacing = 12
        width = cols * cell + (cols - 1) * spacing
        height = rows * cell + (rows - 1) * spacing
        canvas = QPixmap(int(width), int(height))
        canvas.fill(QColor(0, 0, 0, 0))

        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        for idx, pix in enumerate(items):
            r = idx // cols
            c = idx % cols
            x = c * (cell + spacing)
            y = r * (cell + spacing)
            target = QRect(int(x), int(y), int(cell), int(cell))
            scaled = pix.scaled(
                target.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            dx = target.x() + int((target.width() - scaled.width()) / 2)
            dy = target.y() + int((target.height() - scaled.height()) / 2)
            painter.drawPixmap(dx, dy, scaled)

        painter.end()
        return canvas

    def _show_final_result(
        self, pixmap: Optional[QPixmap], rect: Optional[tuple[int, int, int, int]]
    ) -> None:
        self._final_selected_rect = rect
        self._final_face_pixmap = pixmap

        self._detection_active = False
        try:
            self.detector_enabled_changed.emit(False)
        except Exception:
            pass
        try:
            self._camera_opacity_effect.setOpacity(0.0)
        except Exception:
            pass
        try:
            self.preview_stack.setCurrentWidget(self.result_label)
            self._update_result_pixmap()
        except Exception:
            pass

        if self._audio_loop_started:
            try:
                camera_preview_audio_player.stop(wait=False)
            except Exception:
                pass
            self._audio_loop_started = False

        if self._play_result_audio:
            try:
                camera_preview_audio_player.play(
                    "face/result.wav", loop=False, volume=1.0
                )
            except Exception:
                pass

        self._final_view_timer.start(2500)

    def _crop_face_pixmap(
        self, qimage: QImage, rect: tuple[int, int, int, int]
    ) -> QPixmap:
        x, y, w, h = rect
        frame_rect = QRect(0, 0, qimage.width(), qimage.height())
        base_rect = QRect(int(x), int(y), int(w), int(h)).intersected(frame_rect)
        try:
            ex = int(max(8, round(float(w) * 0.30)))
            ey = int(max(8, round(float(h) * 0.20)))
            top_extra = int(max(8, round(float(h) * 0.45)))
        except Exception:
            ex, ey, top_extra = 8, 8, 12
        crop_rect = QRect(
            int(x) - ex,
            int(y) - top_extra,
            int(w) + ex * 2,
            int(h) + ey + top_extra,
        ).intersected(frame_rect)
        if crop_rect.width() <= 2 or crop_rect.height() <= 2:
            crop_rect = base_rect
        if crop_rect.width() <= 2 or crop_rect.height() <= 2:
            return QPixmap.fromImage(qimage)

        face_img = qimage.copy(crop_rect)
        return QPixmap.fromImage(face_img)

    def _set_final_selection(self, rect: tuple[int, int, int, int]) -> None:
        self._picking_active = False
        self._picking_timer.stop()
        self._overlay_circles = []
        self._overlay_colors = []
        self._final_selected_rect = rect
        self._final_view_active = False

        qimage: Optional[QImage] = None
        try:
            if self._latest_frame is not None:
                qimage = bgr_frame_to_qimage(self._latest_frame)
        except Exception:
            qimage = None

        if (
            qimage is None
            and self._latest_qimage is not None
            and not self._latest_qimage.isNull()
        ):
            qimage = self._latest_qimage

        self._final_face_pixmap = None
        if qimage is not None:
            try:
                self._final_face_pixmap = self._crop_face_pixmap(qimage, rect)
            except Exception:
                self._final_face_pixmap = None

        self._detection_active = False
        try:
            self.detector_enabled_changed.emit(False)
        except Exception:
            pass
        try:
            self._camera_opacity_effect.setOpacity(0.0)
        except Exception:
            pass
        try:
            self.preview_stack.setCurrentWidget(self.result_label)
            self._update_result_pixmap()
        except Exception:
            pass

        if self._audio_loop_started:
            try:
                camera_preview_audio_player.stop(wait=False)
            except Exception:
                pass
            self._audio_loop_started = False

        if self._play_result_audio:
            try:
                camera_preview_audio_player.play(
                    "face/result.wav", loop=False, volume=1.0
                )
            except Exception:
                pass

        self._final_view_timer.start(2500)

    def _show_message(self, key: str, details: str = "") -> None:
        """显示友好的错误消息框，可选包含诊断信息。"""
        title = get_content_name_async("camera_preview", key)
        message = get_content_description_async("camera_preview", key)

        if not title:
            title = get_content_name_async("camera_preview", "diagnostic_title") or ""
        if not message:
            message = (
                details
                or get_content_description_async("camera_preview", "diagnostic_title")
                or ""
            )

        if details and message and details not in message:
            message = f"{message}\n\n{details}"

        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(message)
        box.setIcon(QMessageBox.Icon.Warning)
        box.exec()

    def closeEvent(self, event: QCloseEvent) -> None:
        """页面关闭时释放资源。"""
        self._clear_timer.stop()
        self._no_face_timer.stop()
        self._picking_timer.stop()
        self._final_view_timer.stop()
        self.detector_enabled_changed.emit(False)
        if self._capture_worker is not None:
            if self._capture_thread is not None and self._capture_thread.isRunning():
                QMetaObject.invokeMethod(
                    self._capture_worker,
                    "stop",
                    Qt.ConnectionType.BlockingQueuedConnection,
                )
            else:
                try:
                    self._capture_worker.stop()
                except Exception:
                    pass
        else:
            self.capture_stop_requested.emit()

        for thread in [self._capture_thread, self._detector_thread]:
            if thread is None:
                continue
            try:
                thread.quit()
                thread.wait(1500)
            except Exception as exc:
                logger.exception("线程关闭失败: {}", exc)

        super().closeEvent(event)
