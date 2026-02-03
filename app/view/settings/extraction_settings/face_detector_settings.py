import os

from loguru import logger
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import (
    ComboBox,
    ColorConfigItem,
    ColorSettingCard,
    GroupHeaderCardWidget,
    PushButton,
    SpinBox,
    SwitchButton,
)

from app.Language.obtain_language import (
    get_content_description_async,
    get_content_name_async,
    get_content_switchbutton_name_async,
)
from app.tools.path_utils import get_data_path
from app.tools.personalised import get_theme_icon
from app.tools.settings_access import readme_settings_async, update_settings
from app.tools.variable import WIDTH_SPINBOX


class face_detector_settings(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(10)

        self.basic_settings_widget = face_detector_basic_settings(self)
        self.vBoxLayout.addWidget(self.basic_settings_widget)

        self.animation_settings_widget = face_detector_animation_settings(self)
        self.vBoxLayout.addWidget(self.animation_settings_widget)


class _ModelComboBox(ComboBox):
    def __init__(self, refresh_callback, parent=None):
        super().__init__(parent)
        self._refresh_callback = refresh_callback

    def showPopup(self):
        try:
            if self._refresh_callback is not None:
                self._refresh_callback()
        except Exception:
            pass
        return super().showPopup()


class face_detector_basic_settings(GroupHeaderCardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle(
            get_content_name_async("face_detector_settings", "basic_settings")
        )
        self.setBorderRadius(8)

        self.detector_type_combo = _ModelComboBox(self._refresh_model_list)
        self._refresh_model_list()
        self._apply_saved_selection()

        self.detector_type_combo.currentTextChanged.connect(
            lambda: update_settings(
                "face_detector_settings",
                "detector_type",
                self.detector_type_combo.currentText().strip(),
            )
        )

        self.open_model_folder_button = PushButton(
            get_content_name_async("face_detector_settings", "open_model_folder")
        )
        self.open_model_folder_button.clicked.connect(self.open_model_folder)

        self.addGroup(
            get_theme_icon("ic_fluent_scan_object_20_filled"),
            get_content_name_async("face_detector_settings", "detector_type"),
            get_content_description_async("face_detector_settings", "detector_type"),
            self.detector_type_combo,
        )

        self.addGroup(
            get_theme_icon("ic_fluent_folder_open_20_filled"),
            get_content_name_async("face_detector_settings", "open_model_folder"),
            get_content_description_async(
                "face_detector_settings", "open_model_folder"
            ),
            self.open_model_folder_button,
        )

    def _model_dir(self):
        return get_data_path("cv_models")

    def _list_model_names(self) -> list[str]:
        model_dir = self._model_dir()
        try:
            if not model_dir.exists():
                os.makedirs(model_dir, exist_ok=True)
        except Exception:
            pass

        try:
            items = []
            for p in sorted(model_dir.glob("*.onnx")):
                if p.is_file():
                    items.append(p.name)
            return items
        except Exception:
            return []

    def _refresh_model_list(self) -> None:
        current = (self.detector_type_combo.currentText() or "").strip()
        items = self._list_model_names()
        self.detector_type_combo.blockSignals(True)
        self.detector_type_combo.clear()
        self.detector_type_combo.addItems(items)
        if current:
            idx = self.detector_type_combo.findText(current)
            if idx >= 0:
                self.detector_type_combo.setCurrentIndex(idx)
        self.detector_type_combo.blockSignals(False)

    def _apply_saved_selection(self) -> None:
        saved = readme_settings_async("face_detector_settings", "detector_type")
        saved_text = ""
        try:
            if isinstance(saved, int):
                idx = int(saved)
                if 0 <= idx < self.detector_type_combo.count():
                    saved_text = self.detector_type_combo.itemText(idx)
            else:
                saved_text = str(saved).strip() if saved is not None else ""
        except Exception:
            saved_text = ""

        if saved_text:
            idx = self.detector_type_combo.findText(saved_text)
            if idx >= 0:
                self.detector_type_combo.setCurrentIndex(idx)
                return

        if self.detector_type_combo.count() > 0:
            self.detector_type_combo.setCurrentIndex(0)

    def open_model_folder(self) -> None:
        folder_path = self._model_dir()
        try:
            if not folder_path.exists():
                os.makedirs(folder_path, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder_path)))
        except Exception:
            logger.exception("无法打开模型文件夹: {}", folder_path)


class face_detector_animation_settings(GroupHeaderCardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle(
            get_content_name_async(
                "face_detector_settings", "picker_animation_settings"
            )
        )
        self.setBorderRadius(8)

        self.picking_duration_spin = SpinBox()
        self.picking_duration_spin.setFixedWidth(WIDTH_SPINBOX)
        self.picking_duration_spin.setRange(1, 10)
        self.picking_duration_spin.setSingleStep(1)
        self.picking_duration_spin.setSuffix("s")
        try:
            current = readme_settings_async(
                "face_detector_settings", "picking_duration_seconds"
            )
            self.picking_duration_spin.setValue(
                int(current) if current is not None else 2
            )
        except Exception:
            self.picking_duration_spin.setValue(2)
        self.picking_duration_spin.valueChanged.connect(
            lambda: update_settings(
                "face_detector_settings",
                "picking_duration_seconds",
                int(self.picking_duration_spin.value()),
            )
        )

        self.play_process_audio_switch = SwitchButton()
        self.play_process_audio_switch.setOffText(
            get_content_switchbutton_name_async(
                "face_detector_settings", "play_process_audio", "disable"
            )
        )
        self.play_process_audio_switch.setOnText(
            get_content_switchbutton_name_async(
                "face_detector_settings", "play_process_audio", "enable"
            )
        )
        _process_audio = readme_settings_async(
            "face_detector_settings", "play_process_audio"
        )
        self.play_process_audio_switch.setChecked(
            True if _process_audio is None else bool(_process_audio)
        )
        self.play_process_audio_switch.checkedChanged.connect(
            lambda state: update_settings(
                "face_detector_settings", "play_process_audio", bool(state)
            )
        )

        self.play_result_audio_switch = SwitchButton()
        self.play_result_audio_switch.setOffText(
            get_content_switchbutton_name_async(
                "face_detector_settings", "play_result_audio", "disable"
            )
        )
        self.play_result_audio_switch.setOnText(
            get_content_switchbutton_name_async(
                "face_detector_settings", "play_result_audio", "enable"
            )
        )
        _result_audio = readme_settings_async(
            "face_detector_settings", "play_result_audio"
        )
        self.play_result_audio_switch.setChecked(
            True if _result_audio is None else bool(_result_audio)
        )
        self.play_result_audio_switch.checkedChanged.connect(
            lambda state: update_settings(
                "face_detector_settings", "play_result_audio", bool(state)
            )
        )

        self.addGroup(
            get_theme_icon("ic_fluent_timer_20_filled"),
            get_content_name_async(
                "face_detector_settings", "picking_duration_seconds"
            ),
            get_content_description_async(
                "face_detector_settings", "picking_duration_seconds"
            ),
            self.picking_duration_spin,
        )

        self.addGroup(
            get_theme_icon("ic_fluent_speaker_2_20_filled"),
            get_content_name_async("face_detector_settings", "play_process_audio"),
            get_content_description_async(
                "face_detector_settings", "play_process_audio"
            ),
            self.play_process_audio_switch,
        )

        self.addGroup(
            get_theme_icon("ic_fluent_speaker_edit_20_filled"),
            get_content_name_async("face_detector_settings", "play_result_audio"),
            get_content_description_async(
                "face_detector_settings", "play_result_audio"
            ),
            self.play_result_audio_switch,
        )

        self.frame_color_item = ColorConfigItem(
            "face_detector_settings",
            "picker_frame_color",
            readme_settings_async("face_detector_settings", "picker_frame_color"),
        )
        self.frame_color_item.valueChanged.connect(
            lambda color: update_settings(
                "face_detector_settings", "picker_frame_color", color.name()
            )
        )

        self.frame_color_card = ColorSettingCard(
            self.frame_color_item,
            get_theme_icon("ic_fluent_text_color_20_filled"),
            self.tr(
                get_content_name_async("face_detector_settings", "picker_frame_color")
            ),
            self.tr(
                get_content_description_async(
                    "face_detector_settings", "picker_frame_color"
                )
            ),
            self,
        )
        self.vBoxLayout.addWidget(self.frame_color_card)
