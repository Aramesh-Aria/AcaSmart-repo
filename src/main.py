import sys
import traceback
import logging
from datetime import datetime, timedelta
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ---------- Global Error Handler ----------

# مسیر مطمئن برای ذخیره لاگ (داخل پوشه‌ی کاربر)
log_dir = Path.home() / "AppData" / "Local" / "Amoozeshgah"
log_dir.mkdir(parents=True, exist_ok=True)
log_path = log_dir / "error.log"

logging.basicConfig(
    filename=str(log_path),
    level=logging.ERROR,
    format='%(asctime)s - %(message)s',
    encoding='utf-8'
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

from PyQt5.QtWidgets import QApplication
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

    if should_cleanup():
        try:
            clear_local_log_file()
            update_cleanup_timestamp()
        except Exception as e:
            logging.error(f"❌ Error during cleanup: {e}")
    initialize_database()
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())
