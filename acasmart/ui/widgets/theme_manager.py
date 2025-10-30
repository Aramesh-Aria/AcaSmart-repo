from __future__ import annotations
import sys, os
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSettings
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt
from acasmart.style import theme as THEME
from acasmart.style.qss import build_qss
from PySide6.QtGui import QFontDatabase, QFont
from acasmart.paths import resource_path

APP_ORG  = "AcaSmart"
APP_NAME = "AcaSmart"
SETTINGS_KEY = "ui/theme"  # "light" | "dark"

class ThemeManager:
    """Manages application theme and ensures app icon is always WHITE"""
    
    _current_mode = "light"
    _tokens = THEME.LIGHT
    # Preserve base app font across theme toggles
    _base_font_family: str | None = None
    _base_point_size: int | None = None
    _qt_style_set: bool = False

    def __init__(self):
        self.app = QApplication.instance()

        self.app_icon_candidates = [
            "AppIcon.icns",  # macOS preferred
            "AppIcon.ico",   # Windows preferred
            "AppIcon.png",   # Fallback for Linux/others
        ]
    def _build_platform_icon(self) -> QIcon:
        """
        macOS:  icns → png → ico
        Windows: QIcon شامل ICO + PNG
        Linux/Others: png → ico → icns
        (بدون return زودهنگام؛ فقط یک return در انتهای تابع)
        """
        qicon = QIcon()

        if sys.platform == "darwin":
            icns = self._get_resource_path("AppIcon.icns")
            png  = self._get_resource_path("AppIcon.png")
            ico  = self._get_resource_path("AppIcon.ico")

            if icns.exists():
                qicon = QIcon(str(icns))
            elif png.exists():
                qicon = QIcon(str(png))
            elif ico.exists():
                qicon = QIcon(str(ico))

        elif os.name == "nt":
            ico = self._get_resource_path("AppIcon.ico")
            png = self._get_resource_path("AppIcon.png")
            icns = self._get_resource_path("AppIcon.icns")

            # آیکن اجرایی از ICO می‌آید؛ PNG را هم برای تایتل‌بار اضافه می‌کنیم
            if ico.exists():
                qicon.addFile(str(ico))
            if png.exists():
                qicon.addFile(str(png))
            # اگر هیچ‌کدام نبود، fallback به icns (به‌ندرت)
            if qicon.isNull() and icns.exists():
                qicon.addFile(str(icns))

        else:
            # Linux / others
            png  = self._get_resource_path("AppIcon.png")
            ico  = self._get_resource_path("AppIcon.ico")
            icns = self._get_resource_path("AppIcon.icns")

            if png.exists():
                qicon = QIcon(str(png))
            elif ico.exists():
                qicon = QIcon(str(ico))
            elif icns.exists():
                qicon = QIcon(str(icns))

        return qicon

    def _get_resource_path(self, filename: str) -> Path:
        """Robust lookup for resources in dev and packaged modes.
        Prioritize acasmart/resources/static and acasmart/resources via resource_path.
        """
        # Packaged (PyInstaller): resource_path already points to package dir
        candidates: list[Path] = []
        try:
            candidates += [
                resource_path("resources", "static", filename),
                resource_path("resources", filename),
            ]
        except Exception:
            pass

        # Fallbacks: walk up from this file and try to locate acasmart/resources
        base = Path(__file__).resolve()
        for parent in [base.parent, *base.parents]:
            candidates += [
                parent / "resources" / "static" / filename,
                parent / "resources" / filename,
                parent / "acasmart" / "resources" / "static" / filename,
                parent / "acasmart" / "resources" / filename,
            ]

        # Last-resort: current working dir and executable dir
        exe_dir = Path(sys.executable).resolve().parent if hasattr(sys, "executable") else Path.cwd()
        candidates += [
            exe_dir / filename,
            Path.cwd() / filename,
        ]

        for p in candidates:
            try:
                if p and p.exists():
                    return p
            except Exception:
                continue
        return candidates[0]

    def detect_system_theme(self) -> str:
        """Keep theme detection for other UI needs; NOT used for app icon."""
        try:
            settings = QSettings(
                r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                QSettings.NativeFormat,
            )
            apps_use_light_theme = settings.value("AppsUseLightTheme", 1, type=int)
            return "dark" if apps_use_light_theme == 0 else "light"
        except Exception:
            try:
                style = self.app.style().objectName().lower()
                return "dark" if ("dark" in style or "fusion" in style) else "light"
            except Exception:
                return "light"

    def _choose_icon_for_platform(self) -> QIcon:
        return self._build_platform_icon()

    def get_theme_icon(self, theme: str | None = None) -> QIcon:
        # تم نادیده گرفته می‌شود؛ فقط سفید
        return self._build_platform_icon()

    def apply_theme_icon(self, window=None) -> str:
        """
        در dev هم آیکن Dock را ست می‌کند.
        - روی macOS: ابتدا QIcon ست می‌شود؛ اگر PyObjC موجود باشد،
        آیکن Dock با NSApplication هم ست می‌شود.
        """
        theme = self.detect_system_theme()
        icon  = self._build_platform_icon()

        if window:
            window.setWindowIcon(icon)
        if self.app:
            self.app.setWindowIcon(icon)

        if sys.platform == "darwin":
            try:
                from AppKit import NSApplication, NSImage
                icns_path = self._get_resource_path("AppIcon.icns")
                if not icns_path.exists():
                    # fallback to PNG if ICNS missing
                    icns_path = self._get_resource_path("AppIcon.png")
                if icns_path and icns_path.exists():
                    nsimg = NSImage.alloc().initWithContentsOfFile_(str(icns_path))
                    NSApplication.sharedApplication().setApplicationIconImage_(nsimg)
            except Exception:
                pass

        print("🎨 Applied App icon.")
        return theme

    def get_available_icons_debug(self) -> dict:
        """Small helper for debugging available white icon files."""
        info = {}
        for name in self.app_icon_candidates:
            p = self._get_resource_path(name)
            info[name] = str(p), p.exists()
        return info

    def print_theme_info(self):
        print("🔍 Theme Debug:")
        print(f"   Detected system theme: {self.detect_system_theme()}")
        print(f"   Base file: {Path(__file__).resolve()}")
        for name in self.app_icon_candidates:
            p = self._get_resource_path(name)
            print(f"   {name}: {'✅' if p.exists() else '❌'} {p}")

    @classmethod
    def load_last(cls) -> str:
        s = QSettings(APP_ORG, APP_NAME)
        return s.value(SETTINGS_KEY, "light")

    @classmethod
    def save(cls, mode: str):
        s = QSettings(APP_ORG, APP_NAME)
        s.setValue(SETTINGS_KEY, mode)

    @classmethod
    def tokens(cls) -> dict:
        return cls._tokens

    @staticmethod
    def repolish(widget):
        # وقتی property تغییر می‌دهی (مثلاً variant/status) لازم می‌شود
        if widget is None: return
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        try:
            widget.update()
        except TypeError:
            # fallback امن‌تر
            widget.repaint()
    @classmethod
    def apply(cls, app: QApplication, mode: str | None = None):
        """
        اعمال تم به کل اپ: Fusion + QPalette + QSS
        اگر mode=None باشد، آخرین حالت ذخیره‌شده را می‌خواند.
        """
        if mode is None:
            mode = cls.load_last()

        mode = mode if mode in ("light", "dark") else "light"
        cls._current_mode = mode
        cls._tokens = THEME.DARK if mode == "dark" else THEME.LIGHT

        # یکدست کردن رندر (به‌خصوص در ویندوز/لینوکس)
        try:
            if not cls._qt_style_set:
                app.setStyle("Fusion")
                cls._qt_style_set = True
            cls._ensure_app_font(app)
        except Exception as e:
            print(f"error in {e}")
        
        # Set application metadata so Dock/task switcher shows proper name/icon
        try:
            app.setOrganizationName(APP_ORG)
            app.setApplicationName(APP_NAME)
            app.setApplicationDisplayName(APP_NAME)
            if sys.platform.startswith("linux"):
                try:
                    app.setDesktopFileName("acasmart")
                except Exception:
                    pass
        except Exception:
            pass

        # On macOS, try to set process name for better Alt-Tab label when not bundled
        if sys.platform == "darwin":
            try:
                from AppKit import NSProcessInfo
                NSProcessInfo.processInfo().setProcessName_(APP_NAME)
            except Exception:
                pass


        t = cls._tokens
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor(t["bg"]))
        pal.setColor(QPalette.Base, QColor(t["surface"]))
        pal.setColor(QPalette.AlternateBase, QColor(t["rowHover"]))
        pal.setColor(QPalette.Text, QColor(t["text"]))
        pal.setColor(QPalette.WindowText, QColor(t["text"]))
        pal.setColor(QPalette.Button, QColor(t["surface"]))
        pal.setColor(QPalette.ButtonText, QColor(t["text"]))
        pal.setColor(QPalette.Highlight, QColor(t["primary"]))
        pal.setColor(QPalette.HighlightedText, QColor(t["onPrimary"]))
        pal.setColor(QPalette.ToolTipBase, QColor(t["surface"]))
        pal.setColor(QPalette.ToolTipText, QColor(t["text"]))
        pal.setColor(QPalette.PlaceholderText, QColor(t["muted"]))
        app.setPalette(pal)

        # QSS سراسری از روی توکن‌ها
        app.setStyleSheet(build_qss(t))

        cls.save(mode)
    @classmethod
    def current_mode(cls) -> str:
        return cls._current_mode

    @classmethod
    def toggle(cls, app: QApplication):
        new_mode = "dark" if cls._current_mode == "light" else "light"
        cls.apply(app, new_mode)

    @staticmethod
    def _ensure_app_font(app: QApplication):
        """Load Vazirmatn font if available, fallback to system fonts."""
        try:
            from acasmart.paths import resource_path
            font_dir = resource_path("resources/fonts")
            for style in ["Vazirmatn-Regular.ttf", "Vazirmatn-Medium.ttf", "Vazirmatn-Bold.ttf"]:
                font_path = font_dir / style
                if font_path.exists():
                    QFontDatabase.addApplicationFont(str(font_path))
            # Keep original point size stable across toggles
            if ThemeManager._base_point_size is None:
                current_size = app.font().pointSize()
                ThemeManager._base_point_size = current_size if current_size > 0 else 10
            target_family = "Vazirmatn"
            ThemeManager._base_font_family = ThemeManager._base_font_family or target_family
            app.setFont(QFont(target_family, ThemeManager._base_point_size))
            return target_family
        except Exception as e:
            print(f"⚠️ Could not load Vazirmatn font: {e}")
            fallback_font = (".SF NS Text" if sys.platform == "darwin" else "Segoe UI")
            if ThemeManager._base_point_size is None:
                current_size = app.font().pointSize()
                ThemeManager._base_point_size = current_size if current_size > 0 else 10
            ThemeManager._base_font_family = ThemeManager._base_font_family or fallback_font
            app.setFont(QFont(fallback_font, ThemeManager._base_point_size))
            return ThemeManager._base_font_family
        

# Global theme manager instance
_theme_manager = None

def get_theme_manager() -> ThemeManager:
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager

def apply_theme_icon(window=None):
    return get_theme_manager().apply_theme_icon(window)
