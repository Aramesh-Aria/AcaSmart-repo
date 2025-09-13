import sys, os
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSettings

class ThemeManager:
    """Manages application theme and ensures app icon is always WHITE"""

    def __init__(self):
        self.app = QApplication.instance()
        self.base_path = self._get_base_path()

        self.app_icon_candidates = [
            "AppIcon.icns",  # macOS preferred
            "AppIcon.ico",   # Windows preferred
            "AppIcon.png",   # Fallback for Linux/others
        ]

    def _get_base_path(self) -> Path:
        """Base path around this file; not used directly for icons."""
        if getattr(sys, "frozen", False):
            # PyInstaller runtime temp dir
            return Path(sys._MEIPASS)  # type: ignore[attr-defined]
        # .../AcaSmart-repo/src  → برگردان همین مسیر
        return Path(__file__).resolve().parent

    def _get_resource_path(self, filename: str) -> Path:
        """
        مسیر‌یابی robust در dev و packaged.
        """
        candidates: list[Path] = []
        base = Path(__file__).resolve()
        src_dir  = base.parent                                # .../AcaSmart-repo/src
        repo_dir = src_dir.parent                             # .../AcaSmart-repo
        proj_dir = repo_dir.parent                            # .../AcaSmart
        exe_dir  = Path(sys.executable).resolve().parent if hasattr(sys, "executable") else Path.cwd()

        # 1) PyInstaller MEIPASS (اگر بسته شده)
        if getattr(sys, "frozen", False):
            meipass = Path(sys._MEIPASS)  # type: ignore[attr-defined]
            candidates += [
                meipass / "static" / filename,
                meipass / filename,
                exe_dir / "static" / filename,
                exe_dir / filename,
            ]

        # 2) حالت توسعه: دقیقاً مطابق ساختار تو
        candidates += [
            proj_dir / "static" / filename,  # /Users/aria/Documents/AcaSmart/static
            repo_dir / "static" / filename,  
            src_dir  / "static" / filename,
            Path.cwd() / "static" / filename,
            src_dir / filename,
        ]

        for p in candidates:
            if p.exists():
                return p
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
        # ترتیب ترجیح
        if sys.platform == "darwin":
            order = ["AppIcon.icns", "AppIcon.png", "AppIcon.ico"]
        elif os.name == "nt":
            order = ["AppIcon.ico", "AppIcon.png", "AppIcon.icns"]
        else:
            order = ["AppIcon.png", "AppIcon.ico", "AppIcon.icns"]

        for name in order:
            path = self._get_resource_path(name)
            if path.exists():
                return QIcon(str(path))

        for name in self.app_icon_candidates:
            path = self._get_resource_path(name)
            if path.exists():
                return QIcon(str(path))
        print("⚠️ No app icon found. Returning empty QIcon().")
        return QIcon()

    def get_theme_icon(self, theme: str | None = None) -> QIcon:
        """For app icon, ignore theme and always return WHITE icon."""
        return self._choose_icon_for_platform()

    def apply_theme_icon(self, window=None) -> str:
        """
        در dev هم آیکن Dock را ست می‌کند.
        - روی macOS: ابتدا QIcon ست می‌شود؛ اگر PyObjC موجود باشد،
        آیکن Dock با NSApplication هم ست می‌شود.
        """
        theme = self.detect_system_theme()
        icon = self.get_theme_icon(theme=None)

        # ست پیش‌فرض Qt
        if window:
            window.setWindowIcon(icon)
        if self.app:
            self.app.setWindowIcon(icon)

        # ست مستقیم Dock با Cocoa (اختیاری، اگر PyObjC نصب باشد)
        if sys.platform == "darwin":
            try:
                from AppKit import NSApplication, NSImage
                icns_path = self._get_resource_path("AppIcon.icns")
                if icns_path.exists():
                    nsimg = NSImage.alloc().initWithContentsOfFile_(str(icns_path))
                    NSApplication.sharedApplication().setApplicationIconImage_(nsimg)
            except Exception:
                # PyObjC نصب نیست یا خطایی رخ داده؛ اشکالی ندارد، Qt کار می‌کند.
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

# Global theme manager instance
_theme_manager = None

def get_theme_manager() -> ThemeManager:
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager

def apply_theme_icon(window=None):
    return get_theme_manager().apply_theme_icon(window)
