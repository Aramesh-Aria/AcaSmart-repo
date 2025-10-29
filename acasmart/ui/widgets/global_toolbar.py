from __future__ import annotations
try:
    from PySide6.QtGui import QAction, QActionGroup
except Exception:
    from PySide6.QtWidgets import QAction, QActionGroup

from PySide6.QtWidgets import QToolBar, QApplication, QWidget, QMenu, QToolButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from acasmart.ui.widgets.theme_manager import ThemeManager

class GlobalToolbar(QToolBar):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("GlobalToolbar")
        self.setMovable(False)
        self.setFloatable(False)
        self.setToolButtonStyle(Qt.ToolButtonIconOnly)

        app = QApplication.instance()

        # ---- فقط یک دکمه با منو ----
        self.menu_theme = QMenu("تم", self)
        self.grp_theme  = QActionGroup(self.menu_theme)

        # انتخاب مستقیم Light/Dark
        self.act_light = QAction("روشن (Light)", self.grp_theme)
        self.act_dark  = QAction("تاریک (Dark)",  self.grp_theme)
        self.act_light.setCheckable(True)
        self.act_dark.setCheckable(True)

        self.act_light.triggered.connect(lambda: self._apply_mode("light"))
        self.act_dark.triggered.connect(lambda: self._apply_mode("dark"))

        self.menu_theme.addAction(self.act_light)
        self.menu_theme.addAction(self.act_dark)

        # دکمهٔ منو روی تولبار
        self.btn_menu = QToolButton(self)
        self.btn_menu.setText("تم")
        # اگر آیکن داری: self.btn_menu.setIcon(QIcon(":/icons/theme.svg"))
        self.btn_menu.setPopupMode(QToolButton.InstantPopup)
        self.btn_menu.setMenu(self.menu_theme)
        self.addWidget(self.btn_menu)

        # همگام‌سازی وضعیت چک‌مارک‌ها
        self._sync_checks()

    # -------- helpers --------
    def _sync_checks(self):
        mode = ThemeManager.current_mode()
        self.act_light.setChecked(mode == "light")
        self.act_dark.setChecked(mode == "dark")

    def _apply_mode(self, mode: str):
        ThemeManager.apply(QApplication.instance(), mode)
        self._sync_checks()

    def _toggle_and_sync(self, app):
        ThemeManager.toggle(app)
        self._sync_checks()
