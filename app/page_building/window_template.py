# ==================================================
# 导入库
# ==================================================
from typing import Dict, Optional, Type

from loguru import logger
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *
from PySide6.QtNetwork import *
from qfluentwidgets import *
from qframelesswindow import *

from app.tools.variable import *
from app.tools.settings_access import *
from app.tools.path_utils import *
from app.tools.personalised import *
from app.Language.obtain_language import *


class SimpleWindowTemplate(FramelessWindow):
    """简单窗口模板类

    提供一个更简单的窗口模板，不包含导航栏，适用于简单的对话框或弹出窗口。
    该类继承自FramelessWindow，提供了页面管理功能，可以动态添加、切换和移除页面。

    特性:
    - 无边框窗口设计，带有标准标题栏
    - 支持多页面管理，使用QStackedWidget实现页面切换
    - 提供页面添加、移除和切换的便捷方法
    - 支持从页面模板或已有控件创建页面
    - 窗口关闭时发出windowClosed信号

    使用示例:
        # 创建简单窗口
        window = SimpleWindowTemplate("我的窗口", parent=None)

        # 从页面模板添加页面
        page_instance = window.add_page_from_template("settings", SettingsPage)

        # 从已有控件添加页面
        custom_widget = QWidget()
        window.add_page_from_widget("custom", custom_widget)

        # 切换到指定页面
        window.switch_to_page("settings")

        # 显示窗口
        window.show()

    信号:
        windowClosed: 窗口关闭时发出，无参数

    属性:
        parent_window: 父窗口引用
        pages: 页面类字典 {page_name: page_class}
        page_instances: 页面实例字典 {page_name: page_instance}
        stacked_widget: 页面堆叠窗口控件
        main_layout: 主布局
    """

    # 信号定义
    windowClosed = Signal()
    _DEFAULT_TITLEBAR_HEIGHT = 32
    _TITLEBAR_LEFT_OFFSET_PX = 5

    def __init__(
        self,
        title: str = "窗口",
        width: int = 700,
        height: int = 500,
        parent: Optional[QWidget] = None,
    ):
        """
        初始化简单窗口模板

        Args:
            title: 窗口标题
            width: 窗口宽度
            height: 窗口高度
            parent: 父窗口
        """
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        # 保存父窗口引用
        self.parent_window = parent

        # 存储页面
        self.pages: Dict[str, Type] = {}
        self.page_instances: Dict[str, QWidget] = {}

        # 创建主布局
        self.main_layout = QVBoxLayout(self)
        self._sync_layout_margins_with_titlebar()
        self.main_layout.setSpacing(0)

        # 创建堆叠窗口
        self.stacked_widget = QStackedWidget(self)
        self.main_layout.addWidget(self.stacked_widget)

        # 连接信号
        self.__connectSignalToSlot()

        # 直接创建UI组件，不使用延迟初始化
        self.create_ui_components()

        # 初始化窗口
        self.initWindow(title, width, height)

    def _sync_layout_margins_with_titlebar(self) -> None:
        top = 0
        try:
            top = int(self.titleBar.height()) if self.titleBar else 0
        except Exception:
            top = 0

        if top <= 1:
            try:
                top = int(self.titleBar.sizeHint().height()) if self.titleBar else 0
            except Exception:
                top = 0

        if top <= 1:
            top = self._DEFAULT_TITLEBAR_HEIGHT

        self.main_layout.setContentsMargins(0, top, 0, 0)

    def _apply_titlebar_font(self) -> None:
        custom_font = load_custom_font()
        try:
            if getattr(self, "_sr_title_text_label", None) is not None:
                if custom_font:
                    self._sr_title_text_label.setFont(QFont(custom_font, 9))
                else:
                    f = self._sr_title_text_label.font()
                    f.setPointSize(9)
                    self._sr_title_text_label.setFont(f)
        except Exception:
            pass

        for child in self.titleBar.findChildren(QLabel):
            if not isinstance(child, QLabel):
                continue
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

    def _ensure_sr_title_overlay(self) -> None:
        if getattr(self, "_sr_title_overlay", None) is not None:
            return

        self._sr_title_overlay = QWidget(self.titleBar)
        self._sr_title_overlay.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
        self._sr_title_overlay.setObjectName("srTitleOverlay")

        layout = QHBoxLayout(self._sr_title_overlay)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._sr_title_icon_label = QLabel(self._sr_title_overlay)
        self._sr_title_icon_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
        self._sr_title_icon_label.setObjectName("srTitleIcon")
        self._sr_title_icon_label.setFixedSize(16, 16)

        self._sr_title_text_label = QLabel(self._sr_title_overlay)
        self._sr_title_text_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
        self._sr_title_text_label.setObjectName("srTitleLabel")
        self._sr_title_text_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )

        layout.addWidget(self._sr_title_icon_label, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._sr_title_text_label, 0, Qt.AlignmentFlag.AlignVCenter)

        try:
            self.windowTitleChanged.connect(self._update_sr_title_overlay)
            self.windowIconChanged.connect(self._update_sr_title_overlay)
        except Exception:
            pass

    def _update_sr_title_overlay(self, *args) -> None:
        try:
            if getattr(self, "_sr_title_text_label", None) is None:
                return

            title = self.windowTitle() or ""
            self._sr_title_text_label.setText(title)

            icon = self.windowIcon()
            pixmap = None
            try:
                if icon and not icon.isNull():
                    pixmap = icon.pixmap(16, 16)
            except Exception:
                pixmap = None

            if pixmap is not None and not pixmap.isNull():
                self._sr_title_icon_label.setPixmap(pixmap)
                self._sr_title_icon_label.show()
            else:
                self._sr_title_icon_label.hide()

            self._sr_title_overlay.adjustSize()
        except Exception as e:
            logger.exception(f"更新自定义标题栏失败: {e}")

    def _position_sr_title_overlay(self) -> None:
        try:
            if getattr(self, "_sr_title_overlay", None) is None:
                return
            self._sr_title_overlay.adjustSize()
            x = int(self._TITLEBAR_LEFT_OFFSET_PX)
            y = max(
                0, int((self.titleBar.height() - self._sr_title_overlay.height()) / 2)
            )
            self._sr_title_overlay.move(x, y)
            self._sr_title_overlay.raise_()
        except Exception as e:
            logger.exception(f"定位自定义标题栏失败: {e}")

    def _rebuild_titlebar_title_and_icon(self) -> None:
        try:
            if not self.titleBar:
                return

            current_title = self.windowTitle() or ""
            for child in self.titleBar.findChildren(QLabel):
                if child.objectName() in {"srTitleIcon", "srTitleLabel"}:
                    continue

                try:
                    pixmap = child.pixmap()
                except Exception:
                    pixmap = None

                label_text = child.text() if hasattr(child, "text") else ""
                is_original_icon = pixmap is not None and not pixmap.isNull()
                is_original_title = bool(current_title) and label_text == current_title

                if is_original_icon or is_original_title:
                    child.hide()

            self._ensure_sr_title_overlay()
            self._update_sr_title_overlay()
            self._apply_titlebar_font()
            self._position_sr_title_overlay()
        except Exception as e:
            logger.exception(f"重建标题栏标题失败: {e}")

    def _apply_titlebar_left_offset(self) -> None:
        try:
            for child in self.titleBar.findChildren(QWidget):
                if (
                    isinstance(child, QWidget)
                    and child.property("srTitleOffset") is not None
                ):
                    child.setProperty("srTitleOffset", None)

            icon_label = None
            title_label = None

            labels = self.titleBar.findChildren(QLabel)
            current_title = self.windowTitle() or ""

            for child in labels:
                try:
                    pixmap = child.pixmap()
                except Exception:
                    pixmap = None

                if pixmap is not None and not pixmap.isNull():
                    icon_label = child

                label_text = child.text() if hasattr(child, "text") else ""
                if current_title and label_text == current_title:
                    title_label = child
                if label_text and title_label is None:
                    title_label = child

            if icon_label is None and title_label is None:
                return

            offset = int(self._TITLEBAR_LEFT_OFFSET_PX)
            if icon_label is not None:
                icon_label.setProperty("srTitleOffset", "true")
                m = icon_label.contentsMargins()
                icon_label.setContentsMargins(offset, m.top(), m.right(), m.bottom())
            if title_label is not None:
                title_label.setProperty("srTitleOffset", "true")
                m = title_label.contentsMargins()
                title_label.setContentsMargins(offset, m.top(), m.right(), m.bottom())
            self.titleBar.style().unpolish(self.titleBar)
            self.titleBar.style().polish(self.titleBar)
        except Exception as e:
            logger.exception(f"设置标题栏偏移失败: {e}")

    def initWindow(self, title: str, width: int = 700, height: int = 500) -> None:
        """初始化窗口"""
        self.setTitleBar(FluentTitleBar(self))
        try:
            fixed_h = max(
                int(self.titleBar.sizeHint().height()), self._DEFAULT_TITLEBAR_HEIGHT
            )
            self.titleBar.setFixedHeight(fixed_h)
        except Exception:
            self.titleBar.setFixedHeight(self._DEFAULT_TITLEBAR_HEIGHT)

        self._sync_layout_margins_with_titlebar()
        self.setMinimumSize(MINIMUM_WINDOW_SIZE[0], MINIMUM_WINDOW_SIZE[1])
        self.resize(width, height)
        window_icon = QIcon(
            str(get_data_path("assets/icon", "secrandom-icon-paper.png"))
        )
        self.setWindowIcon(window_icon)
        self.setWindowTitle(title)
        self.titleBar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.titleBar.raise_()
        self._apply_titlebar_font()
        self._rebuild_titlebar_title_and_icon()

        # 确保在设置标题栏后应用当前主题和自定义字体
        self._apply_current_theme()

        if self.parent_window is None:
            screen = QApplication.primaryScreen().availableGeometry()
            w, h = screen.width(), screen.height()
            self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self._sync_layout_margins_with_titlebar)
        QTimer.singleShot(0, self._rebuild_titlebar_title_and_icon)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_layout_margins_with_titlebar()
        self._position_sr_title_overlay()

    def __connectSignalToSlot(self) -> None:
        """连接信号与槽"""
        try:
            qconfig.themeChanged.connect(self._on_theme_changed)
        except Exception as e:
            logger.exception(f"连接信号时发生未知错误: {e}")

    def _on_theme_changed(self) -> None:
        """主题变化时自动更新窗口背景"""
        try:
            # 强制刷新窗口背景
            self._apply_current_theme()
            pass
        except Exception as e:
            logger.exception(f"主题变化时更新窗口背景失败: {e}")

    def _is_dark_mode_by_settings(self) -> bool:
        try:
            current_theme = readme_settings("basic_settings", "theme")
            if current_theme == "DARK":
                return True
            if current_theme == "AUTO":
                try:
                    from darkdetect import isDark

                    return bool(isDark())
                except Exception as e:
                    logger.exception(
                        "Error detecting dark mode with darkdetect (fallback to light): {}",
                        e,
                    )
                    return False
            return False
        except Exception:
            return False

    def _apply_current_theme(self) -> None:
        """应用当前主题设置到窗口"""
        try:
            current_theme = readme_settings("basic_settings", "theme")
            is_dark = self._is_dark_mode_by_settings()
            background_color = "#202020" if is_dark else "#ffffff"

            self.setStyleSheet(f"background-color: {background_color};")
            self.default_page.setStyleSheet("background-color: transparent;")

            self._set_titlebar_colors(is_dark)

            logger.debug(f"窗口主题已更新为: {current_theme}")
        except Exception as e:
            logger.exception(f"应用主题时出错: {e}")
            # 设置默认的浅色背景作为备选
            self.setStyleSheet("background-color: #ffffff;")
            self.default_page.setStyleSheet("background-color: transparent;")

    def _set_titlebar_colors(self, is_dark: bool) -> None:
        """设置标题栏颜色"""
        try:
            if is_dark:
                title_color = "#ffffff"  # 白色文字
                background_color = "#202020"
            else:
                title_color = "#000000"  # 黑色文字
                background_color = "#ffffff"

            if hasattr(self.titleBar, "setTitle") and hasattr(self.titleBar, "setIcon"):
                titlebar_style = f"""
                    QWidget {{
                        background-color: {background_color};
                    }}
                    QLabel {{
                        background-color: transparent;
                    }}
                    QLabel#srTitleLabel {{
                        color: {title_color};
                        background-color: transparent;
                    }}
                    *[srTitleOffset="true"] {{
                        margin-left: {self._TITLEBAR_LEFT_OFFSET_PX}px;
                    }}
                """
            else:
                titlebar_style = f"""
                    QWidget {{
                        color: {title_color};
                        background-color: {background_color};
                    }}
                    QLabel {{
                        color: {title_color};
                        background-color: transparent;
                    }}
                    QLabel#srTitleLabel {{
                        color: {title_color};
                        background-color: transparent;
                    }}
                    *[srTitleOffset="true"] {{
                        margin-left: {self._TITLEBAR_LEFT_OFFSET_PX}px;
                    }}
                    QPushButton {{
                        color: {title_color};
                        background-color: transparent;
                    }}
                    QToolButton {{
                        color: {title_color};
                        background-color: transparent;
                    }}
                    QAbstractButton {{
                        color: {title_color};
                        background-color: transparent;
                    }}
                    #minimizeButton, #maximizeButton, #closeButton,
                    #minBtn, #maxBtn, #closeBtn,
                    #minimizeBtn, #maximizeBtn, #closeBtn {{
                        color: {title_color};
                        background-color: transparent;
                    }}
                    #minimizeButton:hover, #maximizeButton:hover, #closeButton:hover,
                    #minBtn:hover, #maxBtn:hover, #closeBtn:hover,
                    #minimizeBtn:hover, #maximizeBtn:hover, #closeBtn:hover {{
                        background-color: rgba(255, 255, 255, 0.1);
                    }}
                    #closeButton:hover, #closeBtn:hover {{
                        background-color: rgba(232, 17, 35, 0.8);
                    }}
                """

            self.titleBar.setStyleSheet(titlebar_style)

            logger.debug(
                f"标题栏颜色已设置: 文字色={title_color}, 背景色={background_color}"
            )
        except Exception as e:
            logger.exception(f"设置标题栏颜色失败: {e}")

    def create_ui_components(self) -> None:
        """创建UI组件"""
        try:
            # 创建默认页面
            self.default_page = QWidget()
            default_layout = QVBoxLayout(self.default_page)
            default_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # 添加默认页面到堆叠窗口
            self.stacked_widget.addWidget(self.default_page)
        except Exception as e:
            logger.exception(f"创建UI组件时出错: {e}")
            raise

    def add_page_from_template(
        self, page_name: str, page_class: Type, **kwargs
    ) -> Optional[QWidget]:
        """
        从页面模板添加页面

        Args:
            page_name: 页面名称（唯一标识）
            page_class: 页面类
            **kwargs: 传递给页面类构造函数的额外参数

        Returns:
            页面实例，如果创建失败则返回None
        """
        # 输入验证
        if not page_name or not isinstance(page_name, str):
            logger.exception("页面名称必须是非空字符串")
            return None

        if page_name in self.page_instances:
            logger.warning(f"页面 {page_name} 已存在，将返回现有实例")
            return self.page_instances[page_name]

        try:
            # 创建页面实例，传递额外参数
            page_instance = page_class(self, **kwargs)

            # 设置对象名称
            page_instance.setObjectName(page_name)

            # 添加到堆叠窗口
            self.stacked_widget.addWidget(page_instance)

            # 存储页面
            self.page_instances[page_name] = page_instance
            self.pages[page_name] = page_class
            return page_instance
        except Exception as e:
            logger.exception(f"创建页面 {page_name} 时出错: {e}")
            return None

    def add_page_from_widget(self, page_name: str, widget: QWidget) -> QWidget:
        """
        从控件添加页面

        Args:
            page_name: 页面名称（唯一标识）
            widget: 页面控件

        Returns:
            页面控件

        Raises:
            ValueError: 如果输入参数无效
        """
        # 输入验证
        if not page_name or not isinstance(page_name, str):
            raise ValueError("页面名称必须是非空字符串")

        if page_name in self.page_instances:
            logger.warning(f"页面 {page_name} 已存在，将返回现有实例")
            return self.page_instances[page_name]

        # 设置对象名称
        widget.setObjectName(page_name)

        try:
            # 添加到堆叠窗口
            self.stacked_widget.addWidget(widget)

            # 存储页面
            self.page_instances[page_name] = widget
            return widget
        except Exception as e:
            logger.exception(f"添加页面 {page_name} 到堆叠窗口时出错: {e}")
            raise

    def get_page(self, page_name: str) -> Optional[QWidget]:
        """
        获取页面实例

        Args:
            page_name: 页面名称

        Returns:
            页面实例，如果不存在则返回None
        """
        # 输入验证
        if not page_name or not isinstance(page_name, str):
            logger.warning("页面名称必须是非空字符串")
            return None

        page = self.page_instances.get(page_name, None)
        if page is None:
            logger.debug(f"请求的页面 {page_name} 不存在")

        return page

    def remove_page(self, page_name: str) -> bool:
        """
        移除页面

        Args:
            page_name: 页面名称

        Returns:
            是否成功移除页面
        """
        # 输入验证
        if not page_name or not isinstance(page_name, str):
            logger.exception("页面名称必须是非空字符串")
            return False

        if page_name not in self.page_instances:
            logger.warning(f"尝试移除不存在的页面: {page_name}")
            return False

        try:
            page = self.page_instances[page_name]

            # 如果当前显示的是要删除的页面，先切换到默认页面
            if self.stacked_widget.currentWidget() == page:
                if self.default_page:
                    self.stacked_widget.setCurrentWidget(self.default_page)
                else:
                    logger.warning(
                        f"删除当前显示的页面 {page_name} 但没有默认页面可切换"
                    )

            # 从堆叠窗口中移除
            self.stacked_widget.removeWidget(page)

            # 从存储中移除
            del self.page_instances[page_name]
            if page_name in self.pages:
                del self.pages[page_name]
            return True
        except Exception as e:
            logger.exception(f"移除页面 {page_name} 时出错: {e}")
            return False

    def switch_to_page(self, page_name: str) -> bool:
        """
        切换到指定页面

        Args:
            page_name: 页面名称

        Returns:
            是否成功切换到页面
        """
        # 输入验证
        if not page_name or not isinstance(page_name, str):
            logger.exception("页面名称必须是非空字符串")
            return False

        if page_name not in self.page_instances:
            logger.warning(f"尝试切换到不存在的页面: {page_name}")
            return False

        try:
            target_page = self.page_instances[page_name]
            current_page = self.stacked_widget.currentWidget()

            # 检查是否已经在目标页面
            if current_page == target_page:
                return True

            # 切换页面
            self.stacked_widget.setCurrentWidget(target_page)
            return True
        except Exception as e:
            logger.exception(f"切换到页面 {page_name} 时出错: {e}")
            return False

    def closeEvent(self, event) -> None:
        """窗口关闭事件处理"""
        try:
            qconfig.themeChanged.disconnect(self._on_theme_changed)
        except Exception:
            pass
        self.windowClosed.emit()
        super().closeEvent(event)
