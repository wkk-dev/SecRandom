from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Union

from loguru import logger


CameraSource = Union[int, str]


@dataclass(frozen=True)
class CameraDeviceInfo:
    """从 Qt 枚举并映射到 OpenCV 捕获源的摄像头设备。"""

    name: str
    source: CameraSource
    qt_id: str


def _qt_device_id_to_string(device_id: Any) -> str:
    """将 Qt 摄像头 id 对象（通常是 QByteArray）转换为可读字符串。"""
    try:
        raw = bytes(device_id)
    except Exception:
        try:
            raw = str(device_id).encode("utf-8", errors="ignore")
        except Exception:
            return ""

    try:
        return raw.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _infer_opencv_source(qt_id: str, fallback_index: int) -> CameraSource:
    """从 Qt 摄像头 id 推断 OpenCV VideoCapture 源。"""
    if qt_id.startswith("/dev/"):
        return qt_id

    match = re.search(r"video(\d+)", qt_id, flags=re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except Exception:
            return fallback_index

    return fallback_index


def list_camera_devices() -> list[CameraDeviceInfo]:
    """通过 PySide6 QtMultimedia 枚举本地摄像头设备。

    Returns:
        摄像头设备列表。当没有可用摄像头或 QtMultimedia 在当前环境中
        不可用时，此列表可能为空。
    """
    try:
        from PySide6.QtMultimedia import QMediaDevices  # type: ignore

        qt_devices = list(QMediaDevices.videoInputs())
    except Exception as exc:
        logger.exception("通过 QtMultimedia 枚举摄像头失败: {}", exc)
        return []

    results: list[CameraDeviceInfo] = []
    for index, device in enumerate(qt_devices):
        try:
            name = device.description() or f"Camera {index}"
        except Exception:
            name = f"Camera {index}"

        try:
            qt_id = _qt_device_id_to_string(device.id())
        except Exception:
            qt_id = ""

        source = _infer_opencv_source(qt_id, fallback_index=index)
        results.append(CameraDeviceInfo(name=name, source=source, qt_id=qt_id))

    return results
