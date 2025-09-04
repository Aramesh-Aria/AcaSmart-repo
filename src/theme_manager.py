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

        # فقط آیکن سفید برنامه؛ فرمت‌های موجود را اینجا لیست کن
        # توجه: icns را برای macOS اضافه کرده‌ای (white_background_icon.icns)
        self.app_icon_candidates = [
            "white_background_icon.icns",  # macOS preferred
            "white_background_icon.ico",   # Windows preferred
            "white_background_icon.png",   # Fallback for Linux/others
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
        Robust path resolution for both dev & packaged.
        Tries (in order): MEIPASS/static, MEIPASS root, cwd/static, exe dir/static,
        project_root/static (sibling of AcaSmart-repo), repo_root/static, and next to exe.
        """
        candidates: list[Path] = []
        base = self._get_base_path()

        # 1) PyInstaller MEIPASS (اگر بسته شده)
        if getattr(sys, "frozen", False):
            meipass = Path(sys._MEIPASS)  # type: ignore[attr-defined]
            candidates += [
                meipass / "static" / filename,
                meipass / filename,
            ]
            # مسیر کنار executable/app
            exe_dir = Path(sys.executable).resolve().parent
            candidates += [
                exe_dir / "static" / filename,
                exe_dir / filename,
            ]

        # 2) حالت توسعه: paths بر اساس ساختار شما
        # .../AcaSmart-repo/src → ریشه پروژه: parents[2] = AcaSmart-repo, parents[3] = ACASMART
        parents = base.parents
        project_root = parents[2] if len(parents) >= 3 else base  # .../ACASMART
        repo_root = parents[1] if len(parents) >= 2 else base     # .../AcaSmart-repo

        candidates += [
            project_root / "static" / filename,  # ✅ ریشه پروژه/static/...
            repo_root / "static" / filename,     # اگر static را بعداً داخل repo آوردی
            Path.cwd() / "static" / filename,    # اجرای نسبی
            base / "static" / filename,          # اگر src/static داشته باشی
            base / filename,                     # اگر فایل کنار src کپی شد
        ]

        # اولین مسیر موجود را برگردان
        for p in candidates:
            if p.exists():
                return p

        # اگر هیچ‌کدام نبود، برای پیام خطا اولین کاندید را برگردان
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
        """Always choose the WHITE app icon, best format per platform."""
        # ترتیب ترجیح بر اساس پلتفرم
        if sys.platform == "darwin":
            order = ["white_background_icon.icns", "white_background_icon.png", "white_background_icon.ico"]
        elif os.name == "nt":
            order = ["white_background_icon.ico", "white_background_icon.png", "white_background_icon.icns"]
        else:
            order = ["white_background_icon.png", "white_background_icon.ico", "white_background_icon.icns"]

        # اگر فایل‌ها را جایی دیگر گذاشتی، _get_resource_path همه مسیرهای رایج را چک می‌کند
        for name in order:
            path = self._get_resource_path(name)
            if path.exists():
                return QIcon(str(path))

        # آخرین تلاش: از لیست کلی کاندیدها
        for name in self.app_icon_candidates:
            path = self._get_resource_path(name)
            if path.exists():
                return QIcon(str(path))

        print("⚠️ No white app icon found. Returning empty QIcon().")
        return QIcon()

    def get_theme_icon(self, theme: str | None = None) -> QIcon:
        """For app icon, ignore theme and always return WHITE icon."""
        return self._choose_icon_for_platform()

    def apply_theme_icon(self, window=None) -> str:
        """Apply WHITE app icon regardless of system theme."""
        theme = self.detect_system_theme()  # برای استفاده احتمالی در جاهای دیگر
        icon = self.get_theme_icon(theme=None)

        if window:
            window.setWindowIcon(icon)
        if self.app:
            self.app.setWindowIcon(icon)

        print("🎨 Applied WHITE app icon (theme ignored).")
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
        print(f"   Detected system theme (for UI only): {self.detect_system_theme()}")
        print(f"   Base path: {self.base_path}")
        for name, (p, ok) in self.get_available_icons_debug().items():
            print(f"   {name}: {'✅' if ok else '❌'} {p}")

# Global theme manager instance
_theme_manager = None

def get_theme_manager() -> ThemeManager:
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager

def apply_theme_icon(window=None):
    return get_theme_manager().apply_theme_icon(window)
