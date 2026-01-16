from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from datetime import datetime
from app.tools.variable import NEXT_VERSION, CODENAME, SYSTEM, ARCH
from app.Language.obtain_language import get_content_name_async


class DevHintWidget(QWidget):
    """开发中提示组件 - 显示在窗口内部左下角"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setup_ui()
        self.setup_position()

    def setup_ui(self):
        """初始化UI"""
        # 获取应用程序字体
        app_font = QApplication.font()

        # 创建主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(2)

        # 创建提示标签
        hint_text = get_content_name_async("dev_hint", "hint_text")
        self.hint_label = QLabel(hint_text)
        hint_font = QFont(app_font)
        hint_font.setBold(True)
        self.hint_label.setFont(hint_font)
        self.hint_label.setStyleSheet("color: #FF6B6B;")
        self.hint_label.setWordWrap(False)

        # 创建版本标签
        version_text = f"SecRandom {NEXT_VERSION} Dev | {CODENAME} ({SYSTEM}-{ARCH})"
        self.version_label = QLabel(version_text)
        version_font = QFont(app_font)
        version_font.setPointSize(8)
        self.version_label.setFont(version_font)
        self.version_label.setStyleSheet("color: #888888;")
        self.version_label.setWordWrap(False)

        # 创建日期标签
        date_text = datetime.now().strftime("%Y-%m-%d")
        self.date_label = QLabel(date_text)
        date_font = QFont(app_font)
        date_font.setPointSize(8)
        self.date_label.setFont(date_font)
        self.date_label.setStyleSheet("color: #888888;")
        self.date_label.setWordWrap(False)

        # 添加到布局
        self.main_layout.addWidget(self.hint_label)
        self.main_layout.addWidget(self.version_label)
        self.main_layout.addWidget(self.date_label)

        # 设置最小宽度和固定大小
        self.setMinimumWidth(400)
        self.adjustSize()
        self.setFixedSize(self.size())

    def setup_position(self):
        """设置位置到父窗口左下角"""
        if self.parent():
            parent_rect = self.parent().rect()
            x = 5
            y = parent_rect.height() - self.height() - 5
            self.move(x, y)

    def update_position(self):
        """更新位置 - 当父窗口大小改变时调用"""
        self.setup_position()

    def update_date(self):
        """更新日期显示"""
        date_text = datetime.now().strftime("%Y-%m-%d")
        self.date_label.setText(date_text)
