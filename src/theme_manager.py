import sys, os
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSettings

class ThemeManager:
    """Manages application theme and ensures app icon is always WHITE"""

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
                if icns_path.exists():
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

# Global theme manager instance
_theme_manager = None

def get_theme_manager() -> ThemeManager:
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager

def apply_theme_icon(window=None):
    return get_theme_manager().apply_theme_icon(window)
