import os
import sqlite3
from dotenv import load_dotenv
from db_helper import create_tables, get_connection
from utils import hash_password

def initialize_database():
    # ۱) ساخت جداول
    create_tables()

    # ۲) بررسی اینکه اگر جدول users خالی است، کاربر ادمین پیش‌فرض را اضافه کن
    load_dotenv()
    admin_mobile = os.getenv("ADMIN_MOBILE")
    admin_password = os.getenv("ADMIN_PASSWORD")
    hashed = hash_password(admin_password)

    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        try:
            user_count = c.fetchone()[0]
        except (TypeError, IndexError):
            user_count = 0

        if user_count == 0:
            c.execute(
                "INSERT INTO users (mobile, password) VALUES (?, ?)",
                (admin_mobile, hashed)
            )
            conn.commit()
