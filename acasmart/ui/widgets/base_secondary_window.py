"""
پنجرهٔ پایه برای تمام پنجره‌های فرعی با تولبار بازگشت.
وقتی کاربر دکمهٔ بازگشت را می‌زند، پنجره بسته می‌شود و پنجرهٔ مقصد (داشبورد یا والد) جلوی کاربر قرار می‌گیرد.
کلید ESC نیز همان کار دکمه بازگشت را انجام می‌دهد.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QToolBar
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeyEvent

from acasmart.ui.widgets.theme_manager import ThemeManager


class BaseSecondaryWindow(QWidget):
    """
    پنجرهٔ فرعی با تولبار حاوی دکمهٔ بازگشت.
    Subclassها باید ویجت‌های خود را به content_layout() اضافه کنند.
    """

    def __init__(self, title: str, return_target: QWidget | None = None):
        super().__init__()
        self.setWindowTitle(title)
        self._return_target = return_target

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # تولبار بازگشت
        self._toolbar = QToolBar(self)
        self._toolbar.setObjectName("BackToolbar")
        self._toolbar.setMovable(False)
        self._toolbar.setFloatable(False)
        self._toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        act_back = QAction("← بازگشت", self)
        act_back.triggered.connect(self._on_back)
        self._toolbar.addAction(act_back)

        root.addWidget(self._toolbar)

        # ناحیهٔ محتوا
        self._content = QWidget(self)
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(16, 16, 16, 16)
        self._content_layout.setSpacing(10)
        root.addWidget(self._content)

        try:
            ThemeManager.repolish(self._toolbar)
        except Exception:
            pass

    def content_layout(self) -> QVBoxLayout:
        """Layout برای اضافه کردن ویجت‌های محتوای پنجره."""
        return self._content_layout

    def keyPressEvent(self, event: QKeyEvent):
        """هندل کردن کلیدهای صفحه‌کلید: ESC برای بازگشت."""
        if event.key() == Qt.Key_Escape:
            self._on_back()
            event.accept()
        else:
            super().keyPressEvent(event)

    def _on_back(self):
        """دکمه بازگشت: پنجره مقصد را جلو بیاور و این پنجره را ببند."""
        if self._return_target and self._return_target.isVisible():
            self._return_target.raise_()
            self._return_target.activateWindow()
        self.close()
