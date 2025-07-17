import sys
import traceback
import logging
from datetime import datetime, timedelta
import os
from pathlib import Path

# Fix for setuptools file access issue
def patch_setuptools_file_access():
    """Monkey patch to prevent setuptools from trying to access vendor files"""
    try:
        import pkg_resources
        original_get_distribution = pkg_resources.get_distribution
        
        def safe_get_distribution(name):
            try:
                return original_get_distribution(name)
            except (FileNotFoundError, OSError):
                # Return a dummy distribution if file not found
                class DummyDistribution:
                    def __init__(self):
                        self.project_name = name
                        self.version = "0.0.0"
                    def __getattr__(self, name):
                        return None
                return DummyDistribution()
        
        pkg_resources.get_distribution = safe_get_distribution
        print("🔧 Patched setuptools file access")
    except Exception as e:
        print(f"⚠️ Could not patch setuptools: {e}")

# Apply the patch early
patch_setuptools_file_access()

# Fix for PyInstaller runtime hook issue
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    # noinspection PyUnresolvedReferences
    os.chdir(sys._MEIPASS)
    print(f"📁 Changed working directory to: {os.getcwd()}")

from dotenv import load_dotenv

load_dotenv()

# ---------- Global Error Handler ----------

# مسیر مطمئن برای ذخیره لاگ (داخل پوشه‌ی کاربر)
log_dir = Path.home() / "AppData" / "Local" / "AcaSmart"
log_dir.mkdir(parents=True, exist_ok=True)
log_path = log_dir / "error.log"

# Create a custom handler with UTF-8 encoding for Python 3.8 compatibility
class UTF8FileHandler(logging.FileHandler):
    def __init__(self, filename, mode='a', encoding='utf-8'):
        super().__init__(filename, mode, encoding=encoding)

# Configure logging for Python 3.8 compatibility
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(message)s',
    handlers=[UTF8FileHandler(str(log_path))]
)

# هدایت همه‌ی پرینت‌ها و ارورها به لاگ
class LoggerWriter:
    def __init__(self, level):
        self.level = level

    def write(self, message):
        if message.strip():
            self.level(message)

    def flush(self):
        pass

sys.stdout = LoggerWriter(logging.error)
sys.stderr = LoggerWriter(logging.error)

from PySide6.QtWidgets import QApplication
from login_window import LoginWindow
from app_init import initialize_database

# ---------- Uncaught Exception Handler ----------
def log_uncaught_exceptions(exctype, value, tb):
    error_message = "".join(traceback.format_exception(exctype, value, tb))
    logging.error(error_message)

sys.excepthook = log_uncaught_exceptions

# ---------- clean up error log ----------
CLEANUP_FILE = str(log_dir / ".last_cleanup.txt")

def should_cleanup():
    if not os.path.exists(CLEANUP_FILE):
        return True

    with open(CLEANUP_FILE, "r") as f:
        last_cleanup_str = f.read().strip()
        try:
            last_cleanup = datetime.strptime(last_cleanup_str, "%Y-%m-%d")
        except ValueError:
            return True

    return datetime.today() - last_cleanup >= timedelta(days=3)

def update_cleanup_timestamp():
    with open(CLEANUP_FILE, "w") as f:
        f.write(datetime.today().strftime("%Y-%m-%d"))

def clear_local_log_file():
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            f.truncate(0)
        print("🧹 Cleared local error.log file.")
    except Exception as e:
        logging.error(f"❌ Error clearing local log file: {e}")

# ---------- Main App ----------
if __name__ == "__main__":
    try:
        print("🚀 Starting AcaSmart application...")
        print(f"📁 Log directory: {log_dir}")
        print(f"📁 Current working directory: {os.getcwd()}")
        
        # Check for any suspicious files
        current_dir = Path(os.getcwd())
        txt_files = list(current_dir.glob("*.txt"))
        print(f"📄 .txt files in current directory: {txt_files}")
        
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
        window = LoginWindow()
        window.show()
        print("✅ GUI started successfully")
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"❌ Critical error during startup: {e}")
        logging.error(f"Critical error during startup: {e}")
        # Print the full traceback to help debug
        traceback.print_exc()
        raise
