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
    
    # Create a file handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    file_handler.setFormatter(formatter)
    
    # Configure root logger
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    
    # Only add console handler if we have access to original stdout
    if hasattr(sys, '__stdout__') and sys.__stdout__ is not None:
        try:
            console_handler = logging.StreamHandler(sys.__stdout__)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            root.addHandler(console_handler)
        except Exception as e:
            # If console handler fails, just log to file
            logging.warning(f"Could not create console handler: {e}")
    elif not getattr(sys, 'frozen', False):
        # For non-frozen apps, try regular stdout
        try:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            root.addHandler(console_handler)
        except Exception as e:
            logging.warning(f"Could not create console handler: {e}")

_ensure_logging()

class LoggerWriter:
    def __init__(self, level):
        self.level = level
        self._original_stdout = sys.__stdout__
        self._original_stderr = sys.__stderr__
    
    def write(self, message):
        if message.strip():
            # Write to original stdout/stderr to avoid recursion
            if self.level == logging.info:
                self._original_stdout.write(message)
            else:
                self._original_stderr.write(message)
            # Also log it
            self.level(message)
    
    def flush(self):
        if self.level == logging.info:
            self._original_stdout.flush()
        else:
            self._original_stderr.flush()

# Only redirect stdout/stderr if not frozen (i.e., not in PyInstaller bundle)
# and if we have access to the original streams
if not getattr(sys, 'frozen', False) and hasattr(sys, '__stdout__') and hasattr(sys, '__stderr__'):
    try:
        sys.stdout = LoggerWriter(logging.info)
        sys.stderr = LoggerWriter(logging.error)
    except Exception as e:
        logging.warning(f"Could not redirect stdout/stderr: {e}")

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
