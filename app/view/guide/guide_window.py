# ==================================================
# 导入库
# ==================================================
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import QFont, QIcon
from qfluentwidgets import *
from qframelesswindow import FramelessWindow
from app.view.guide.pages import *
from app.Language.obtain_language import get_any_position_value_async
from app.tools.settings_access import update_settings
from app.tools.personalised import load_custom_font
from app.tools.path_utils import get_data_path


# ==================================================
# 引导窗口类
# ==================================================
class GuideWindow(FramelessWindow):
    guideFinished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowIcon(
            QIcon(str(get_data_path("assets/icon", "secrandom-icon-paper.png")))
        )
        self.setWindowTitle("SecRandom Setup")
        self.resize(800, 600)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # 标题栏
        self.titleBar.raise_()
        self._apply_titlebar_font()

        # 主布局
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(0, 32, 0, 0)  # 留出标题栏高度

        # 页面容器
        self.stackedWidget = QStackedWidget(self)
        self.vBoxLayout.addWidget(self.stackedWidget)

        self._page_transition_anim = None
        self._page_transition_target_index = None
        self._initial_show_anim = None
        self._initial_show_animated = False
        self._guide_finished = False

        # 底部导航栏
        self.bottomBar = QWidget(self)
        self.bottomLayout = QHBoxLayout(self.bottomBar)
        self.bottomLayout.setContentsMargins(20, 10, 20, 20)

        self.prevBtn = PushButton(
            get_any_position_value_async("guide", "previous"), self
        )
        self.nextBtn = PrimaryPushButton(
            get_any_position_value_async("guide", "next"), self
        )
        self.bottomLayout.addStretch(1)
        self.bottomLayout.addWidget(self.prevBtn)
        self.bottomLayout.addWidget(self.nextBtn)

        self.vBoxLayout.addWidget(self.bottomBar)

        # 初始化页面
        self.init_pages()

        # 连接信号
        self.prevBtn.clicked.connect(self.prev_page)
        self.nextBtn.clicked.connect(self.next_page)

        self.update_nav_buttons()
        self._on_page_changed(self.current_index)

    def showEvent(self, event):
        super().showEvent(event)
        if self._initial_show_animated:
            return
        self._initial_show_animated = True
        QTimer.singleShot(0, self._start_initial_show_animation)

    def _start_initial_show_animation(self):
        if self.current_index != 0:
            return

        if (
            self._page_transition_anim is not None
            and self._page_transition_anim.state() == QAbstractAnimation.State.Running
        ):
            return

        if (
            self._initial_show_anim is not None
            and self._initial_show_anim.state() == QAbstractAnimation.State.Running
        ):
            self._initial_show_anim.stop()
            self._initial_show_anim.deleteLater()
            self._initial_show_anim = None

        effect = QGraphicsOpacityEffect(self.stackedWidget)
        effect.setOpacity(0.0)
        self.stackedWidget.setGraphicsEffect(effect)

        opacity_anim = QPropertyAnimation(effect, b"opacity", self)
        opacity_anim.setDuration(520)
        opacity_anim.setStartValue(0.0)
        opacity_anim.setEndValue(1.0)
        opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        start_pos = self.stackedWidget.pos()
        pos_anim = QPropertyAnimation(self.stackedWidget, b"pos", self)
        pos_anim.setDuration(520)
        pos_anim.setStartValue(QPoint(start_pos.x(), start_pos.y() + 14))
        pos_anim.setEndValue(start_pos)
        pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(opacity_anim)
        group.addAnimation(pos_anim)

        def cleanup():
            self._initial_show_anim = None
            self.stackedWidget.setGraphicsEffect(None)

        group.finished.connect(cleanup)
        self._initial_show_anim = group
        group.start()

    def _apply_titlebar_font(self):
        custom_font = load_custom_font()
        for child in self.titleBar.children():
            if isinstance(child, QLabel):
                label_text = child.text() if hasattr(child, "text") else ""
                if not label_text:
                    continue
                if custom_font:
                    child.setFont(QFont(custom_font, 9))
                else:
                    f = child.font()
                    f.setPointSize(9)
                    child.setFont(f)
                break

    def _start_page_transition(self, target_index: int):
        if target_index < 0 or target_index >= len(self.pages):
            return

        if self.stackedWidget.currentIndex() == target_index:
            return

        if (
            self._page_transition_anim is not None
            and self._page_transition_anim.state() == QAbstractAnimation.State.Running
        ):
            self._page_transition_anim.stop()
            self._page_transition_anim.deleteLater()
            self._page_transition_anim = None

        if (
            self._initial_show_anim is not None
            and self._initial_show_anim.state() == QAbstractAnimation.State.Running
        ):
            self._initial_show_anim.stop()
            self._initial_show_anim.deleteLater()
            self._initial_show_anim = None
            self.stackedWidget.setGraphicsEffect(None)

        self._page_transition_target_index = target_index
        self.prevBtn.setEnabled(False)
        self.nextBtn.setEnabled(False)

        effect = self.stackedWidget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(self.stackedWidget)
            self.stackedWidget.setGraphicsEffect(effect)
        effect.setOpacity(1.0)
        normal_pos = self.stackedWidget.pos()

        fade_out = QPropertyAnimation(effect, b"opacity", self)
        fade_out.setDuration(140)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.OutCubic)

        fade_in = QPropertyAnimation(effect, b"opacity", self)
        fade_in.setDuration(220)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        pos_anim = QPropertyAnimation(self.stackedWidget, b"pos", self)
        pos_anim.setDuration(220)
        pos_anim.setStartValue(QPoint(normal_pos.x(), normal_pos.y() + 14))
        pos_anim.setEndValue(normal_pos)
        pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        fade_in_group = QParallelAnimationGroup(self)
        fade_in_group.addAnimation(fade_in)
        fade_in_group.addAnimation(pos_anim)

        group = QSequentialAnimationGroup(self)
        group.addAnimation(fade_out)
        group.addAnimation(QPauseAnimation(50, self))
        group.addAnimation(fade_in_group)

        def apply_index():
            target = self._page_transition_target_index
            if target is None:
                return
            self.current_index = target
            self.stackedWidget.setCurrentIndex(target)
            self.stackedWidget.move(normal_pos.x(), normal_pos.y() + 14)
            if self.current_index == len(self.pages) - 1:
                self.nextBtn.setText(get_any_position_value_async("guide", "finish"))
            else:
                self.nextBtn.setText(get_any_position_value_async("guide", "next"))
            self.prevBtn.setEnabled(False)
            self.nextBtn.setEnabled(False)

        def cleanup():
            self._page_transition_target_index = None
            self._page_transition_anim = None
            self.stackedWidget.setGraphicsEffect(None)
            self.stackedWidget.move(normal_pos)
            self._on_page_changed(self.current_index)
            self.update_nav_buttons()

        fade_out.finished.connect(apply_index)
        group.finished.connect(cleanup)

        self._page_transition_anim = group
        group.start()

    def init_pages(self):
        self.welcomePage = WelcomePage(self)
        self.languagePage = LanguagePage(self)
        self.licensePage = LicensePage(self)
        self.migrationPage = MigrationPage(self)
        self.basicSettingsPage = BasicSettingsPage(self)
        self.listPage = ListPage(self)
        self.enhancedPage = EnhancedPage(self)
        self.testPage = TestPage(self)
        self.linksPage = LinksPage(self)

        self.pages = [
            self.welcomePage,
            self.languagePage,
            self.licensePage,
            self.migrationPage,
            self.basicSettingsPage,
            self.listPage,
            self.enhancedPage,
            self.testPage,
            self.linksPage,
        ]

        for page in self.pages:
            self.stackedWidget.addWidget(page)

        self.current_index = 0

        # 许可协议页面逻辑
        self.licensePage.licenseAccepted.connect(self._on_license_accepted)

        # 页面切换监听
        self.stackedWidget.currentChanged.connect(self._on_page_changed)

    def _on_page_changed(self, index):
        self.bottomBar.setVisible(self.pages[index] != self.welcomePage)
        if self.pages[index] == self.licensePage:
            self.nextBtn.setEnabled(self.licensePage.is_accepted())
        else:
            self.nextBtn.setEnabled(True)

    def _on_license_accepted(self, accepted):
        if self.pages[self.current_index] == self.licensePage:
            self.nextBtn.setEnabled(accepted)

    def next_page(self):
        next_idx = self.current_index + 1

        if next_idx < len(self.pages):
            self._start_page_transition(next_idx)
        else:
            update_settings("basic_settings", "guide_completed", True)
            self._guide_finished = True
            self.guideFinished.emit()
            self.close()

    def prev_page(self):
        prev_idx = self.current_index - 1

        if prev_idx >= 0:
            self._start_page_transition(prev_idx)

    def update_nav_buttons(self):
        self.prevBtn.setEnabled(self.current_index > 0)
        is_last_page = self.current_index == len(self.pages) - 1
        self.nextBtn.setVisible(not is_last_page)

        if is_last_page:
            self.nextBtn.setText(get_any_position_value_async("guide", "finish"))
        else:
            self.nextBtn.setText(get_any_position_value_async("guide", "next"))

    def closeEvent(self, event):
        if self._guide_finished:
            event.accept()
            return super().closeEvent(event)

        dialog = MessageBox(
            get_any_position_value_async("guide", "exit_confirm", "title"),
            get_any_position_value_async("guide", "exit_confirm", "content"),
            self,
        )
        dialog.yesButton.setText(
            get_any_position_value_async("guide", "exit_confirm", "exit_button")
        )
        dialog.cancelButton.setText(
            get_any_position_value_async("guide", "exit_confirm", "cancel_button")
        )

        if dialog.exec():
            event.accept()
            super().closeEvent(event)
            QApplication.quit()
        else:
            event.ignore()
