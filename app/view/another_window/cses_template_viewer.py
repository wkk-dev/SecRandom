# ==================================================
# 导入库
# ==================================================
from loguru import logger
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *
from qfluentwidgets import *

from app.tools.variable import *
from app.tools.path_utils import *
from app.tools.personalised import *
from app.Language.obtain_language import *
from app.common.extraction.extract import get_cses_import_template


class CsesTemplateViewerWindow(QWidget):
    """CSES模板查看器窗口"""

    def __init__(self, parent=None):
        """初始化CSES模板查看器窗口"""
        super().__init__(parent)
        self.parent_window = parent
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        # 设置窗口标题
        self.setWindowTitle(get_content_name_async("time_settings", "template_title"))

        # 创建主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 创建标题标签
        title_label = BodyLabel(
            get_content_name_async("time_settings", "template_title")
        )

        # 创建文本编辑器
        self.text_edit = TextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont(load_custom_font(), 10))

        # 获取并设置模板内容
        try:
            template_content = get_cses_import_template()
            self.text_edit.setPlainText(template_content)
        except Exception as e:
            logger.error(f"获取模板内容失败: {e}")
            self.text_edit.setPlainText(f"无法加载模板: {str(e)}")

        # 创建按钮布局
        button_layout = QHBoxLayout()

        # 复制到剪贴板按钮
        self.copy_button = PushButton(
            get_content_name_async("time_settings", "copy_to_clipboard")
        )
        self.copy_button.setIcon(get_theme_icon("ic_fluent_copy_20_filled"))
        self.copy_button.clicked.connect(self.on_copy_clicked)

        # 保存为文件按钮
        self.save_button = PushButton(
            get_content_name_async("time_settings", "save_as_file")
        )
        self.save_button.setIcon(get_theme_icon("ic_fluent_save_20_filled"))
        self.save_button.clicked.connect(self.on_save_clicked)

        # 关闭按钮
        self.close_button = PushButton(get_content_name_async("time_settings", "close"))
        self.close_button.clicked.connect(self.close)

        button_layout.addWidget(self.copy_button)
        button_layout.addWidget(self.save_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)

        # 添加到主布局
        self.main_layout.addWidget(title_label)
        self.main_layout.addWidget(self.text_edit)
        self.main_layout.addLayout(button_layout)

    def on_copy_clicked(self):
        """复制到剪贴板"""
        try:
            content = self.text_edit.toPlainText()
            clipboard = QApplication.clipboard()
            clipboard.setText(content)

            InfoBar.success(
                title=get_content_name_async("time_settings", "copy_success"),
                content=get_content_name_async("time_settings", "template_copied"),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
        except Exception as e:
            logger.error(f"复制到剪贴板失败: {e}")
            InfoBar.error(
                title=get_content_name_async("time_settings", "import_failed"),
                content=get_content_name_async("time_settings", "copy_failed").format(
                    str(e)
                ),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )

    def on_save_clicked(self):
        """保存为文件"""
        try:
            # 打开保存文件对话框
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                get_content_name_async("time_settings", "save_template"),
                get_content_name_async("time_settings", "cses_template"),
                f"{get_content_name_async('time_settings', 'yaml_files')};;{get_content_name_async('time_settings', 'all_files')}",
            )

            if file_path:
                content = self.text_edit.toPlainText()
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                InfoBar.success(
                    title=get_content_name_async("time_settings", "save_success"),
                    content=get_content_name_async(
                        "time_settings", "template_saved"
                    ).format(file_path),
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self,
                )

        except Exception as e:
            logger.error(f"保存模板文件失败: {e}")
            InfoBar.error(
                title=get_content_name_async("time_settings", "import_failed"),
                content=get_content_name_async("time_settings", "save_failed").format(
                    str(e)
                ),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )

    def closeEvent(self, event):
        """处理窗口关闭事件"""
        event.accept()

    def close(self):
        """关闭窗口"""
        self.closeEvent(QCloseEvent())
        super().close()
