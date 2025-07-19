import os
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSettings

class ThemeManager:
    """Manages application theme and icon based on system theme"""
    
    def __init__(self):
        self.app = QApplication.instance()
        self.base_path = self._get_base_path()
        self.icon_paths = {
            'dark': {
                'ico': self._get_resource_path('black_background_icon.ico'),
                'png': self._get_resource_path('black_background_icon.png')
            },
            'light': {
                'ico': self._get_resource_path('white_background_icon.ico'),
                'png': self._get_resource_path('white_background_icon.png')
            }
        }
    
    def _get_base_path(self):
        """Get the base path for resources (works for both development and compiled)"""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            return Path(sys._MEIPASS)
        else:
            # Running in development - look in parent directory where icons are
            return Path(__file__).parent.parent.parent  # Go up to Amoozeshgah_App directory
    
    def _get_resource_path(self, filename):
        """Get the full path to a resource file"""
        return self.base_path / filename
    
    def detect_system_theme(self):
        """Detect the current system theme"""
        try:
            # Method 1: Check Windows registry for theme setting
            settings = QSettings("HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize", 
                               QSettings.NativeFormat)
            apps_use_light_theme = settings.value("AppsUseLightTheme", 1, type=int)
            
            if apps_use_light_theme == 0:
                return 'dark'
            else:
                return 'light'
                
        except Exception as e:
            print(f"⚠️ Could not detect system theme: {e}")
            # Fallback: check if we're in dark mode by examining the application style
            try:
                style = self.app.style().objectName().lower()
                if 'dark' in style or 'fusion' in style:
                    return 'dark'
                else:
                    return 'light'
            except:
                # Default to light theme if all else fails
                return 'light'
    
    def get_theme_icon(self, theme=None):
        """Get the appropriate icon for the given theme"""
        if theme is None:
            theme = self.detect_system_theme()
        
        icon_path = self.icon_paths[theme]['ico']
        
        if not icon_path.exists():
            # Fallback to PNG if ICO doesn't exist
            icon_path = self.icon_paths[theme]['png']
        
        if icon_path.exists():
            return QIcon(str(icon_path))
        else:
            print(f"⚠️ Icon not found for theme '{theme}': {icon_path}")
            # Return a default icon if none found
            return QIcon()
    
    def apply_theme_icon(self, window=None):
        """Apply the appropriate icon based on system theme"""
        theme = self.detect_system_theme()
        icon = self.get_theme_icon(theme)
        
        if window:
            window.setWindowIcon(icon)
        
        # Also set the application icon
        self.app.setWindowIcon(icon)
        
        print(f"🎨 Applied {theme} theme icon")
        return theme
    
    def get_available_themes(self):
        """Get list of available themes with their icon paths"""
        themes = {}
        for theme, paths in self.icon_paths.items():
            themes[theme] = {
                'ico': paths['ico'].exists(),
                'png': paths['png'].exists(),
                'ico_path': str(paths['ico']),
                'png_path': str(paths['png'])
            }
        return themes
    
    def print_theme_info(self):
        """Print debug information about theme detection and available icons"""
        print("🔍 Theme Detection Debug Info:")
        print(f"   System theme detected: {self.detect_system_theme()}")
        print(f"   Base path: {self.base_path}")
        
        available_themes = self.get_available_themes()
        for theme, info in available_themes.items():
            print(f"   {theme} theme:")
            print(f"     ICO: {'✅' if info['ico'] else '❌'} {info['ico_path']}")
            print(f"     PNG: {'✅' if info['png'] else '❌'} {info['png_path']}")

# Global theme manager instance
theme_manager = None

def get_theme_manager():
    """Get the global theme manager instance"""
    global theme_manager
    if theme_manager is None:
        theme_manager = ThemeManager()
    return theme_manager

def apply_theme_icon(window=None):
    """Convenience function to apply theme icon"""
    return get_theme_manager().apply_theme_icon(window) 