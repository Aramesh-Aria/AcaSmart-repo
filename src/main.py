import sys
import traceback
import logging
from datetime import datetime, timedelta
from pathlib import Path

from paths import APP_DATA_DIR, DB_PATH, resource_path
from dotenv import load_dotenv
from PySide6.QtWidgets import QApplication

from app_init import initialize_database
from login_window import LoginWindow

# ---------- setuptools patch ----------
def patch_setuptools_file_access():
    try:
        import pkg_resources
        original_get_distribution = pkg_resources.get_distribution
        def safe_get_distribution(name):
            try:
                return original_get_distribution(name)
            except (FileNotFoundError, OSError):
                class DummyDistribution:
                    def __init__(self):
                        self.project_name = name
                        self.version = "0.0.0"
                    def __getattr__(self, _):
                        return None
                return DummyDistribution()
        pkg_resources.get_distribution = safe_get_distribution
        print("🔧 Patched setuptools file access")
    except Exception as e:
        print(f"⚠️ Could not patch setuptools: {e}")

patch_setuptools_file_access()

# ---------- Environment ----------
env_path = resource_path(".env")
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

def _ensure_logging():
    root = logging.getLogger()
    if root.handlers:
        return  # respect existing setup
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    log_file = APP_DATA_DIR / "acasmart.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

_ensure_logging()

class LoggerWriter:
    def __init__(self, level):
        self.level = level
    def write(self, message):
        if message.strip():
            self.level(message)
    def flush(self):
        pass

sys.stdout = LoggerWriter(logging.info)
sys.stderr = LoggerWriter(logging.error)

# ---------- Uncaught Exception Handler ----------
def log_uncaught_exceptions(exctype, value, tb):
    error_message = "".join(traceback.format_exception(exctype, value, tb))
    logging.error(error_message)

sys.excepthook = log_uncaught_exceptions

# ---------- Cleanup ----------
CLEANUP_FILE = APP_DATA_DIR / ".last_cleanup.txt"

def should_cleanup() -> bool:
    if not CLEANUP_FILE.exists():
        return True
    try:
        last_cleanup = datetime.strptime(CLEANUP_FILE.read_text().strip(), "%Y-%m-%d")
    except ValueError:
        return True
    return datetime.today() - last_cleanup >= timedelta(days=3)

def update_cleanup_timestamp():
    CLEANUP_FILE.write_text(datetime.today().strftime("%Y-%m-%d"))

def clear_local_log_file():
    try:
        with open(APP_DATA_DIR / "error.log", "w", encoding="utf-8") as f:
            f.truncate(0)
        print("🧹 Cleared local error.log file.")
    except Exception as e:
        logging.error(f"❌ Error clearing local log file: {e}")

# ---------- Main ----------
if __name__ == "__main__":
    try:
        print("🚀 Starting AcaSmart application...")
        print(f"📁 Data dir: {APP_DATA_DIR}")
        print(f"📁 DB path : {DB_PATH}")
        print(f"📁 CWD     : {Path.cwd()}")

        if should_cleanup():
            try:
                clear_local_log_file()
                update_cleanup_timestamp()
            except Exception as e:
                logging.error(f"❌ Error during cleanup: {e}")

        print("🔧 Initializing database...")
        initialize_database()
        print("✅ Database initialized successfully")

        print("🎨 Starting GUI...")
        app = QApplication(sys.argv)

        try:
            from theme_manager import apply_theme_icon
            theme = apply_theme_icon()
            print(f"🎨 Applied {theme} theme icon")
        except Exception as e:
            print(f"⚠️ Could not apply theme icon: {e}")

        window = LoginWindow()
        window.show()
        print("✅ GUI started successfully")

        # سازگار با PySide6 قدیمی/جدید
        exit_code = app.exec() if hasattr(app, "exec") else app.exec_()
        sys.exit(exit_code)

    except Exception as e:
        print(f"❌ Critical error during startup: {e}")
        logging.error(f"Critical error during startup: {e}")
        traceback.print_exc()
        raise
