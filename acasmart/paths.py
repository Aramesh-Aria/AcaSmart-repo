from pathlib import Path
import platform, os, sys

APP_NAME = "AcaSmart"

def get_app_data_dir() -> Path:
    sysname = platform.system()
    if sysname == "Windows":
        base = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / APP_NAME
    elif sysname == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / APP_NAME
    else: # Linux / others
        base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        return base / APP_NAME

APP_DATA_DIR = get_app_data_dir()
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = APP_DATA_DIR / "acasmart.db"

def resource_path(*parts: str) -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", "."))
    else:
        base = Path(__file__).resolve().parent
    return (base / Path(*parts)).resolve()
