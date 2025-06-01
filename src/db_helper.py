import sqlite3
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDateEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)

from pathlib import Path
import shutil
import os
import sys
import sqlite3

# محل مناسب برای ذخیره دیتابیس در AppData
APP_DATA_DIR = Path.home() / "AppData" / "Local" / "Amoozeshgah"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_NAME = APP_DATA_DIR / "academy.db"

# تعیین مسیر فایل template (از حالت فشرده شده یا دایرکتوری فعلی)
if getattr(sys, 'frozen', False):
    base_path = Path(sys._MEIPASS)  # هنگام اجرای exe
else:
    base_path = Path(__file__).parent  # هنگام اجرای مستقیم

TEMPLATE_DB_PATH = os.path.join(base_path, 'academy_template.db')

# کپی اولیه در صورت نبود فایل دیتابیس
if not DB_NAME.exists():
    shutil.copy(TEMPLATE_DB_PATH, DB_NAME)

# تابع اتصال به دیتابیس
def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def create_tables():
    """Create all tables with FKs, UNIQUE constraints, indexes, and audit columns."""
    with get_connection() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        c = conn.cursor()

        # Teachers table
        c.execute("""
            CREATE TABLE IF NOT EXISTS teachers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                national_code TEXT UNIQUE NOT NULL,
                teaching_card_number TEXT,
                gender TEXT,
                phone TEXT,
                birth_date TEXT,
                card_number TEXT,
                iban TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                updated_at TEXT DEFAULT (datetime('now','localtime'))
            );
        """)
        # teachers instruments table
        c.execute("""CREATE TABLE IF NOT EXISTS teacher_instruments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NOT NULL,
                instrument TEXT NOT NULL,
                FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
                UNIQUE(teacher_id, instrument)
                );  
        """)
        # Students table
        c.execute("""CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                birth_date TEXT NOT NULL,
                gender TEXT NOT NULL,
                national_code TEXT UNIQUE NOT NULL,
                phone TEXT,
                father_name TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                updated_at TEXT DEFAULT (datetime('now','localtime'))
            );

        """)

        # Classes table
        c.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                teacher_id INTEGER NOT NULL,
                day TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                room TEXT,
                instrument TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                updated_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY(teacher_id)
                  REFERENCES teachers(id)
                  ON DELETE CASCADE
                  ON UPDATE CASCADE,
                UNIQUE(teacher_id, day, start_time, end_time, room)
            );
        """)

        # Sessions table
        # Sessions table
        c.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                term_id INTEGER,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                duration INTEGER DEFAULT 30,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                updated_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY(class_id)
                    REFERENCES classes(id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE,
                FOREIGN KEY(student_id)
                    REFERENCES students(id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE,
                FOREIGN KEY(term_id)
                    REFERENCES student_terms(id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE,
                UNIQUE(class_id, student_id, date, time)
            );
        """)

        # Student terms table
        c.execute("""
          CREATE TABLE IF NOT EXISTS student_terms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            class_id INTEGER NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(student_id)
              REFERENCES students(id)
              ON DELETE CASCADE
              ON UPDATE CASCADE,
            FOREIGN KEY(class_id)
              REFERENCES classes(id)
              ON DELETE CASCADE
              ON UPDATE CASCADE
          );
        """)

        # Payments table
        c.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                class_id INTEGER NOT NULL,
                term_id INTEGER,
                amount INTEGER NOT NULL,
                payment_date TEXT NOT NULL,
                payment_type TEXT DEFAULT 'tuition',  -- 'tuition' or 'extra'
                description TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                updated_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY(term_id) REFERENCES student_terms(id) ON DELETE CASCADE ON UPDATE CASCADE
            );
        """)

        # Settings table
        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        # Users table
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              mobile TEXT UNIQUE,
              password TEXT
            );
        ''')

        # Attendance table
        c.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            class_id INTEGER NOT NULL,
            term_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            is_present INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY(term_id) REFERENCES student_terms(id) ON DELETE CASCADE ON UPDATE CASCADE,
            UNIQUE(student_id, class_id, date)
        );
        """)
            # جدول ثبت ترم‌هایی که پیام پایان ترم‌شان قبلاً نمایش داده شده
        c.execute("""
                    CREATE TABLE IF NOT EXISTS notified_terms (
                        term_id INTEGER PRIMARY KEY,
                        student_id INTEGER NOT NULL,
                        class_id INTEGER NOT NULL,
                        FOREIGN KEY(term_id) REFERENCES student_terms(id) ON DELETE CASCADE,
                        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
                        FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE
                    );
                """)
        # جدول ثبت پیام‌های ارسال‌شده برای یادآوری تمدید ترم
        c.execute("""
            CREATE TABLE IF NOT EXISTS sms_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                term_id INTEGER NOT NULL,
                sent_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY(term_id) REFERENCES student_terms(id) ON DELETE CASCADE,
                UNIQUE(student_id, term_id)
            );
        """)

        # Indexes for faster lookups
        # برای ارتباط سریع‌تر هنرجو با کلاس‌ها
        c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_student_id ON sessions(student_id);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_class_id ON sessions(class_id);")

        # برای ارتباط کلاس با استاد
        c.execute("CREATE INDEX IF NOT EXISTS idx_classes_teacher_id ON classes(teacher_id);")

        # اگر زیاد جستجو می‌کنی بر اساس روز کلاس
        c.execute("CREATE INDEX IF NOT EXISTS idx_classes_day ON classes(day);")

        # اگر مرتب پرداخت‌ها را بر اساس هنرجو یا کلاس یا تاریخ می‌خواهی
        c.execute("CREATE INDEX IF NOT EXISTS idx_payments_student_id ON payments(student_id);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_payments_class_id ON payments(class_id);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(payment_date);")

        # مقداردهی اولیه تنظیمات فقط یکبار هنگام ساخت دیتابیس جدید
        c.execute("DELETE FROM settings")  # فقط اگر می‌خوای تنظیمات رو همیشه از صفر بنویسی
        c.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("currency_unit", "toman"))
        c.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("sms_enabled", "فعال"))
        c.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("term_session_count", "12"))
        c.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("term_tuition", "6000000"))

        conn.commit()
# <-------------------------------  Utility Functions  ------------------------------------------------->

def is_national_code_exists(table, national_code):
    '''برای جلوگیری از ورود تکراری'''
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(f"SELECT COUNT(*) FROM {table} WHERE national_code = ?", (national_code,))
        return c.fetchone()[0] > 0


def is_national_code_exists_for_other(table, national_code, current_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(f"""
            SELECT COUNT(*) FROM {table}
            WHERE national_code = ? AND id != ?
        """, (national_code, current_id))
        return c.fetchone()[0] > 0

# Settings Functions

def set_setting(key, value):
    """Insert or update a setting key/value pair."""
    with get_connection() as conn:
        conn.execute(
            "REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value))
        )
        conn.commit()


def get_setting(key, default=None):
    """Retrieve a setting value by key, or return default."""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = c.fetchone()
        return row[0] if row else default
# <-------------------------------  Notifications  ------------------------------------------------->
def get_unnotified_expired_terms():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT s.id, c.id, s.name, s.national_code, c.name, c.day, t.id AS term_id
            FROM student_terms t
            JOIN students s ON s.id = t.student_id
            JOIN classes c ON c.id = t.class_id
            WHERE t.end_date IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM notified_terms n
                  WHERE n.term_id = t.id
              )
        """)
        return c.fetchall()


def mark_terms_as_notified(term_info_list):
    """
    term_info_list = list of (term_id, student_id, class_id)
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.executemany("""
            INSERT OR IGNORE INTO notified_terms (term_id, student_id, class_id)
            VALUES (?, ?, ?)
        """, term_info_list)
        conn.commit()

def has_renew_sms_been_sent(student_id, term_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*) FROM sms_notifications
            WHERE student_id = ? AND term_id = ?
        """, (student_id, term_id))
        return c.fetchone()[0] > 0

def mark_renew_sms_sent(student_id, term_id):
    with get_connection() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO sms_notifications (student_id, term_id)
            VALUES (?, ?)
        """, (student_id, term_id))
        conn.commit()
# <-------------------------------  Teachers Functions  ------------------------------------------------->

def fetch_teachers():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id, name FROM teachers")  # بدون instrument
        return c.fetchall()


def fetch_teachers_simple():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id, name FROM teachers")
        return c.fetchall()

def insert_teacher(name, national_code, teaching_card_number, gender, phone, birth_date, card_number=None, iban=None):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO teachers (name, national_code, teaching_card_number, gender, phone, birth_date, card_number, iban)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, national_code, teaching_card_number, gender, phone, birth_date, card_number, iban)
        )
        conn.commit()


def delete_teacher_by_id(teacher_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM teachers WHERE id=?", (teacher_id,))
        conn.commit()

def fetch_students_with_teachers():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT students.id, students.national_code, students.name,
                   COALESCE(GROUP_CONCAT(DISTINCT teachers.name), '—')
            FROM students
            LEFT JOIN sessions ON students.id = sessions.student_id
            LEFT JOIN classes ON sessions.class_id = classes.id
            LEFT JOIN teachers ON classes.teacher_id = teachers.id
            GROUP BY students.id
            ORDER BY students.name COLLATE NOCASE
        """)
        return c.fetchall()


def is_teacher_assigned_to_students(teacher_id):
    conn = get_connection()
    c = conn.cursor()

    # مرحله 1: گرفتن کلاس‌هایی که استاد تدریس می‌کند
    c.execute("SELECT id FROM classes WHERE teacher_id = ?", (teacher_id,))
    class_ids = [row[0] for row in c.fetchall()]

    # اگر اصلاً کلاس ندارد، یعنی به هیچ هنرجویی هم مرتبط نیست
    if not class_ids:
        conn.close()
        return False

    # مرحله 2: بررسی اینکه آیا برای هیچ‌کدام از این کلاس‌ها جلسه‌ای ثبت شده یا نه
    placeholders = ",".join("?" * len(class_ids))  # برای query امن
    query = f"SELECT COUNT(*) FROM sessions WHERE class_id IN ({placeholders})"
    c.execute(query, class_ids)
    session_count = c.fetchone()[0]

    conn.close()
    return session_count > 0

def update_teacher_by_id(teacher_id, name, national_code, teaching_card_number, gender, phone, birth_date, card_number=None, iban=None):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE teachers
            SET name=?, national_code=?, teaching_card_number=?, gender=?, phone=?, birth_date=?, card_number=?, iban=?, updated_at=datetime('now','localtime')
            WHERE id=?
            """,
            (name, national_code, teaching_card_number, gender, phone, birth_date, card_number, iban, teacher_id)
        )
        conn.commit()


def get_teacher_by_id(teacher_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT name, national_code, teaching_card_number, gender, phone, birth_date, card_number, iban
            FROM teachers
            WHERE id=?
        """, (teacher_id,))
        return c.fetchone()


def get_teacher_id_by_national_code(national_code):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM teachers WHERE national_code = ?", (national_code,))
        row = c.fetchone()
        return row[0] if row else None

# <-------------------------------  teachers instruments Functions  ------------------------------------------------->

def add_instrument_to_teacher(teacher_id, instrument):
    with get_connection() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO teacher_instruments (teacher_id, instrument)
            VALUES (?, ?)
        """, (teacher_id, instrument))
        conn.commit()

def remove_instrument_from_teacher(teacher_id, instrument):
    with get_connection() as conn:
        conn.execute("""
            DELETE FROM teacher_instruments
            WHERE teacher_id = ? AND instrument = ?
        """, (teacher_id, instrument))
        conn.commit()

def get_instruments_for_teacher(teacher_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT instrument FROM teacher_instruments
            WHERE teacher_id = ?
        """, (teacher_id,))
        return [row[0] for row in c.fetchall()]

def fetch_teachers_with_instruments():
    """
    بازگرداندن لیست اساتید به همراه سازهای تدریسی، برای استفاده در مدیریت کلاس‌ها.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT t.id, t.name, GROUP_CONCAT(ti.instrument, '/') as instruments
            FROM teachers t
            LEFT JOIN teacher_instruments ti ON t.id = ti.teacher_id
            GROUP BY t.id
        """)
        return c.fetchall()
# <----------------------  Student Functions  --------------------------------------------->

def insert_student(name, birth_date, gender, national_code, phone, father_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO students (name, birth_date, gender, national_code, phone, father_name)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, birth_date, gender, national_code, phone, father_name))
    conn.commit()
    conn.close()




def student_national_code_exists(national_code):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM students WHERE national_code=?", (national_code,))
        return c.fetchone()[0] > 0



def get_student_by_id(student_id):
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT name, birth_date, gender, national_code, phone, father_name FROM students WHERE id=?",
            (student_id,)
        )
        return cursor.fetchone()


def update_student_by_id(student_id, name, birth_date, gender, national_code, phone, father_name):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE students
            SET name=?, birth_date=?, gender=?, national_code=?, phone=?, father_name=?, updated_at=datetime('now','localtime')
            WHERE id=?
            """,
            (name, birth_date, gender, national_code, phone, father_name, student_id)
        )
        conn.commit()

def delete_student_by_id(student_id):
    """Delete a student by ID."""
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM students WHERE id=?",
            (student_id,)
        )
        conn.commit()

def fetch_students():
    """Fetch all students with full details needed for UI filtering and sorting."""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, name, gender, birth_date, national_code 
            FROM students
            ORDER BY name COLLATE NOCASE
        """)
        return c.fetchall()


#<-----------------------------  Classes Functions  --------------------------------------->

def create_class(name, teacher_id, day, start_time, end_time, room, instrument):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO classes (name, teacher_id, day, start_time, end_time, room, instrument) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, teacher_id, day, start_time, end_time, room, instrument)
        )
        conn.commit()


def fetch_classes():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT classes.id,
                   classes.name,
                   teachers.name,
                   classes.instrument,
                   classes.day,
                   classes.start_time,
                   classes.end_time,
                   classes.room
            FROM classes
            JOIN teachers ON classes.teacher_id = teachers.id
            ORDER BY classes.id DESC
        """)
        return c.fetchall()



def delete_class_by_id(class_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE class_id=?", (class_id,))
        conn.execute("DELETE FROM classes WHERE id=?", (class_id,))
        conn.commit()

def is_class_has_sessions(class_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM sessions WHERE class_id=?", (class_id,))
        return c.fetchone()[0] > 0

def class_exists(teacher_id, day, start_time, end_time, room):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*) FROM classes
            WHERE teacher_id = ? AND day = ? AND start_time = ? AND end_time = ? AND room = ?
        """, (teacher_id, day, start_time, end_time, room))
        return c.fetchone()[0] > 0

def get_class_by_id(class_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT name, teacher_id, instrument, day, start_time, end_time, room
            FROM classes WHERE id = ?
        """, (class_id,))
        return c.fetchone()

def update_class_by_id(class_id, name, teacher_id, day, start_time, end_time, room, instrument):
    with get_connection() as conn:
        conn.execute("""
            UPDATE classes
            SET name=?, teacher_id=?, instrument=?, day=?, start_time=?, end_time=?, room=?, updated_at=datetime('now','localtime')
            WHERE id=?
        """, (name, teacher_id, instrument, day, start_time, end_time, room, class_id))
        conn.commit()

def fetch_classes_for_student(student_id):
    """
    همه کلاس‌هایی که هنرجو می‌تونه در اون‌ها شرکت کنه، صرف‌نظر از استاد خاص.
    این کلاس‌ها باید برای افزودن جلسه به این هنرجو در دسترس باشن.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT DISTINCT c.id, c.name, t.name, c.day
            FROM classes c
            JOIN teachers t ON c.teacher_id = t.id
            ORDER BY c.name COLLATE NOCASE
        """)
        return c.fetchall()

def get_day_and_time_for_class(class_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT day, start_time FROM classes WHERE id = ?", (class_id,))
        return c.fetchone() or (None, None)

def insert_student_term_if_not_exists(student_id, class_id, start_date):
    """
    اگر هنرجو قبلاً در این کلاس ترمی نداشته یا ترمش به پایان رسیده، ترم جدید ایجاد می‌شود.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT end_date FROM student_terms
            WHERE student_id=? AND class_id=?
        """, (student_id, class_id))
        row = c.fetchone()
        if row:
            # اگر end_date خالیه، یعنی ترم هنوز فعاله و نیازی به ترم جدید نیست
            if row[0] is None:
                return

        # اگر ترمی وجود نداره یا ترم قبلی تمام شده، ترم جدید بساز
        c.execute("""
            INSERT INTO student_terms (student_id, class_id, start_date, end_date)
            VALUES (?, ?, ?, NULL)
        """, (student_id, class_id, start_date))
        conn.commit()

def delete_future_sessions(student_id, class_id, session_date):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM sessions WHERE student_id=? AND class_id=? AND date>=?",
            (student_id, class_id, session_date)
        )
        conn.commit()



def check_and_set_term_end(student_id, class_id, session_date):
    """
    بررسی می‌کند که آیا تعداد جلسات حضور و غیاب برای ترم جاری به حد نصاب رسیده،
    و در صورت رسیدن، تاریخ پایان ترم را ثبت می‌کند و جلسات آینده‌ی همان ترم را حذف می‌کند.
    """
    term_id = get_term_id_by_student_and_class(student_id, class_id)
    if not term_id:
        return

    with get_connection() as conn:
        c = conn.cursor()

        # گرفتن start_date از ترم فعال
        c.execute("SELECT start_date FROM student_terms WHERE id=?", (term_id,))
        row = c.fetchone()
        if not row:
            return
        start_date = row[0]

        # شمارش جلسات از تاریخ شروع ترم
        c.execute("""
            SELECT COUNT(*) FROM attendance
            WHERE student_id=? AND class_id=? AND date >= ?
        """, (student_id, class_id, start_date))
        count = c.fetchone()[0]

        # مقایسه با سقف جلسات ترم
        term_limit = int(get_setting("term_session_count", 12))

        if count == term_limit:
            # ثبت پایان ترم
            c.execute("""
                UPDATE student_terms
                SET end_date=?, updated_at=datetime('now','localtime')
                WHERE id=?
            """, (session_date, term_id))

            # حذف جلسات آینده مربوط به همان ترم
            c.execute("""
                DELETE FROM sessions
                WHERE student_id=? AND class_id=? AND date >= ? AND term_id=?
            """, (student_id, class_id, session_date, term_id))

            conn.commit()

def does_teacher_have_time_conflict(teacher_id, day, start_time, end_time, exclude_class_id=None):
    with get_connection() as conn:
        c = conn.cursor()
        query = """
            SELECT COUNT(*) FROM classes
            WHERE teacher_id = ?
              AND day = ?
              AND (
                  (start_time < ? AND end_time > ?) -- تداخل کامل یا جزئی
                  OR (start_time >= ? AND start_time < ?)
              )
        """
        params = [teacher_id, day, end_time, start_time, start_time, end_time]

        if exclude_class_id:
            query += " AND id != ?"
            params.append(exclude_class_id)

        c.execute(query, params)
        return c.fetchone()[0] > 0

#<-----------------------------  SESSION FUNCTIONS  --------------------------------------->

def add_session(class_id, student_id, date, time):
    conn = get_connection()
    c = conn.cursor()

    term_id = get_term_id_by_student_and_class(student_id, class_id)
    if not term_id:
        term_id = insert_student_term_if_not_exists(student_id, class_id, date)

    c.execute("""
        INSERT INTO sessions (class_id, student_id, term_id, date, time)
        VALUES (?, ?, ?, ?, ?)
    """, (class_id, student_id, term_id, date, time))

    conn.commit()
    conn.close()


def fetch_sessions_by_class(class_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT sessions.id, students.name, date, time, duration
            FROM sessions
            JOIN students ON sessions.student_id = students.id
            WHERE class_id = ?
            ORDER BY date, time
        """, (class_id,))
        return c.fetchall()

def delete_session(session_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
        conn.commit()

def get_student_term(student_id, class_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT start_date, end_date
            FROM student_terms
            WHERE student_id=? AND class_id=?
        """, (student_id, class_id))
        return c.fetchone()

def has_weekly_time_conflict(student_id, class_day, session_time, exclude_session_id=None):
    """
    بررسی می‌کند آیا هنرجو در این روز و ساعت، در کلاس دیگری جلسه دارد یا نه.
    """
    with get_connection() as conn:
        c = conn.cursor()
        query = """
            SELECT s.id
            FROM sessions s
            JOIN classes c ON s.class_id = c.id
            WHERE s.student_id = ?
              AND c.day = ?
              AND s.time = ?
        """
        params = [student_id, class_day, session_time]

        if exclude_session_id:
            query += " AND s.id != ?"
            params.append(exclude_session_id)

        c.execute(query, params)
        return c.fetchone() is not None

def update_session(session_id, class_id, student_id, date, time, duration=30):
    term_id = get_term_id_by_student_and_class(student_id, class_id)
    with get_connection() as conn:
        conn.execute("""
            UPDATE sessions
            SET class_id = ?, student_id = ?, term_id = ?, date = ?, time = ?, duration = ?, updated_at = datetime('now','localtime')
            WHERE id = ?
        """, (class_id, student_id, term_id, date, time, duration, session_id))
        conn.commit()


def is_class_slot_taken(class_id, date, time):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*) FROM sessions
            WHERE class_id = ? AND date = ? AND time = ?
        """, (class_id, date, time))
        return c.fetchone()[0] > 0

def get_all_expired_terms():
    """
    برمی‌گرداند لیست تمام ترم‌هایی که end_date آن‌ها مقدار دارد (یعنی به پایان رسیده‌اند).
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT s.name, s.national_code, c.name, c.day
            FROM student_terms t
            JOIN students s ON s.id = t.student_id
            JOIN classes c ON c.id = t.class_id
            WHERE t.end_date IS NOT NULL
        """)
        return c.fetchall()

def delete_sessions_for_expired_terms():
    """
    فقط جلساتی که مربوط به ترم‌های پایان‌یافته‌اند را حذف می‌کند.
    از بازه start_date تا end_date برای هر ترم منقضی استفاده می‌کند.
    """
    with get_connection() as conn:
        c = conn.cursor()

        # دریافت ترم‌هایی که end_date دارند
        c.execute("""
            SELECT student_id, class_id, start_date, end_date
            FROM student_terms
            WHERE end_date IS NOT NULL
        """)
        expired_terms = c.fetchall()

        for student_id, class_id, start_date, end_date in expired_terms:
            c.execute("""
                DELETE FROM sessions
                WHERE student_id = ? AND class_id = ?
                AND date >= ? AND date <= ?
            """, (student_id, class_id, start_date, end_date))

        conn.commit()


def get_student_count_per_class():
    """
    تعداد هنرجویانی که برای هر کلاس جلسه دارند (بدون تکرار).
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT class_id, COUNT(DISTINCT student_id)
            FROM sessions
            GROUP BY class_id
        """)
        return dict(c.fetchall())

def fetch_students_with_teachers_for_class(class_id):
    """
    فقط هنرجویانی که برای کلاس خاص جلسه ثبت‌شده دارند، همراه با نامشان و استاد.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT DISTINCT students.id, students.name, teachers.name
            FROM students
            JOIN sessions ON students.id = sessions.student_id
            JOIN classes ON sessions.class_id = classes.id
            JOIN teachers ON classes.teacher_id = teachers.id
            WHERE classes.id = ?
            ORDER BY students.name COLLATE NOCASE
        """, (class_id,))
        return c.fetchall()

def delete_student_term(student_id, class_id):
    with get_connection() as conn:
        conn.execute("""
            DELETE FROM student_terms
            WHERE student_id = ? AND class_id = ? AND end_date IS NULL
        """, (student_id, class_id))
        conn.commit()


#<-----------------------------  PAYMENT FUNCTIONS  --------------------------------------->

def insert_payment(student_id, class_id, term_id, amount, payment_date, payment_type='tuition', description=None):
    """
    ثبت پرداخت با ترم و نوع پرداخت.
    """
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO payments (student_id, class_id, term_id, amount, payment_date, payment_type, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (student_id, class_id, term_id, amount, payment_date, payment_type, description)
        )
        conn.commit()


def fetch_payments(student_id=None, class_id=None, date_from=None, date_to=None, term_id=None):
    """
    دریافت لیست پرداخت‌ها با فیلترهای اختیاری.
    """
    query = """
        SELECT payments.id, students.name, classes.name,
               payments.amount, payments.payment_date, payments.description, payments.payment_type
        FROM payments
        JOIN students ON payments.student_id = students.id
        JOIN classes ON payments.class_id = classes.id
    """
    conditions = []
    params = []

    if student_id:
        conditions.append("payments.student_id = ?")
        params.append(student_id)
    if class_id:
        conditions.append("payments.class_id = ?")
        params.append(class_id)
    if term_id:
        conditions.append("payments.term_id = ?")
        params.append(term_id)
    if date_from:
        conditions.append("payments.payment_date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("payments.payment_date <= ?")
        params.append(date_to)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY payments.payment_date DESC"

    with get_connection() as conn:
        c = conn.cursor()
        c.execute(query, tuple(params))
        return c.fetchall()


def get_total_paid_for_term(term_id, payment_type='tuition'):
    """
    جمع مبلغ پرداختی برای یک ترم مشخص (پیش‌فرض فقط شهریه).
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM payments
            WHERE term_id = ? AND payment_type = ?
            """,
            (term_id, payment_type)
        )
        return c.fetchone()[0]

def delete_payment(payment_id):
    """
    Delete a payment record by its ID.
    """
    with get_connection() as conn:
        conn.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
        conn.commit()

def get_term_id_by_student_and_class(student_id, class_id):
    """
    آخرین ترم فعال (end_date=NULL) برای هنرجو در یک کلاس خاص را برمی‌گرداند.
    اگر ترمی وجود نداشته باشد، None بازمی‌گرداند.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id FROM student_terms
            WHERE student_id = ? AND class_id = ? AND end_date IS NULL
            ORDER BY id DESC LIMIT 1
        """, (student_id, class_id))
        row = c.fetchone()
        return row[0] if row else None

def fetch_extra_payments_for_term(term_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT amount, payment_date, description
            FROM payments
            WHERE term_id = ? AND payment_type = 'extra'
            ORDER BY payment_date
        """, (term_id,))
        return c.fetchall()

def fetch_registered_classes_for_student(student_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT classes.id, classes.name, teachers.name, classes.instrument,
               classes.day, classes.start_time, classes.end_time, classes.room
        FROM classes
        JOIN teachers ON classes.teacher_id = teachers.id
        JOIN student_terms ON classes.id = student_terms.class_id
        WHERE student_terms.student_id = ?
        ORDER BY classes.day
    """, (student_id,))
    result = c.fetchall()
    conn.close()
    return result

def delete_term_if_no_payments(student_id, class_id, term_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) FROM payments
        WHERE student_id = ? AND class_id = ? AND term_id = ?
    """, (student_id, class_id, term_id))
    has_payments = c.fetchone()[0] > 0

    if has_payments:
        conn.close()
        return False

    # حذف ترم و تمام جلسات آن ترم
    c.execute("""
        DELETE FROM sessions WHERE student_id = ? AND class_id = ? AND term_id = ?
    """, (student_id, class_id, term_id))

    c.execute("""
        DELETE FROM student_terms WHERE student_id = ? AND class_id = ? AND id = ?
    """, (student_id, class_id, term_id))

    conn.commit()
    conn.close()
    return True

def update_payment_by_id(payment_id, amount, date, payment_type, description):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        UPDATE payments
        SET amount = ?, payment_date = ?, payment_type = ?, description = ?, updated_at = datetime('now','localtime')
        WHERE id = ?
    """, (amount, date, payment_type, description, payment_id))
    conn.commit()
    conn.close()

# <-----------------------------  ATTENDANCE FUNCTIONS  --------------------------------------->

def count_attendance(student_id, class_id):
    """
    تعداد جلسات ثبت‌شده برای هنرجو در ترم فعال (end_date IS NULL).
    """
    term_id = get_term_id_by_student_and_class(student_id, class_id)
    if not term_id:
        return 0

    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*) FROM attendance
            WHERE student_id=? AND class_id=? AND date >= (
                SELECT start_date FROM student_terms WHERE id=?
            )
        """, (student_id, class_id, term_id))
        return c.fetchone()[0]


def fetch_classes_on_weekday(day_name):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT c.id, c.name, t.name, c.instrument, c.day, c.start_time, c.end_time, c.room
            FROM classes c
            JOIN teachers t ON c.teacher_id = t.id
            WHERE c.day = ?
            ORDER BY c.start_time
        """, (day_name,))
        return c.fetchall()

def insert_attendance_with_date(student_id, class_id, term_id, date, is_present):
    term_id = get_term_id_by_student_class_and_date(student_id, class_id, date)
    if not term_id:
        return  # ترمی پیدا نشد، ثبت نکن
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO attendance (student_id, class_id, term_id, date, is_present)
            VALUES (?, ?, ?, ?, ?)
            """,
            (student_id, class_id, term_id, date, is_present)
        )
        conn.commit()
    check_and_set_term_end(student_id, class_id, date)

def fetch_attendance_by_date(student_id, class_id, date_str, term_id=None):
    """
    وضعیت حضور هنرجو در یک کلاس، تاریخ و ترم خاص را برمی‌گرداند.
    اگر term_id داده نشود، از آخرین ترم فعال استفاده می‌کند.
    """
    if term_id is None:
        term_id = get_term_id_by_student_and_class(student_id, class_id)
    if not term_id:
        return None

    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT is_present FROM attendance
            WHERE student_id = ? AND class_id = ? AND term_id = ? AND date = ?
        """, (student_id, class_id, term_id, date_str))
        row = c.fetchone()
        if row is None:
            return None
        return bool(row[0])


def get_term_id_by_student_class_and_date(student_id, class_id, selected_date):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, start_date, end_date
            FROM student_terms
            WHERE student_id = ? AND class_id = ?
        """, (student_id, class_id))
        terms = c.fetchall()

        for term_id, start, end in terms:
            if selected_date >= start and (end is None or selected_date <= end):
                return term_id  # فقط ترمی که بازه‌اش معتبر است
    return None

def get_term_dates(term_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT start_date, end_date FROM student_terms
            WHERE id = ?
        """, (term_id,))
        return c.fetchone()

def get_student_contact(student_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT name, phone FROM students WHERE id = ?", (student_id,))
        row = c.fetchone()
        return row if row else (None, None)

# todo: get class and teacher name for sms
def get_class_and_teacher_name(class_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT c.name, t.name
            FROM classes c
            JOIN teachers t ON c.teacher_id = t.id
            WHERE c.id = ?
        """, (class_id,))
        return c.fetchone() or ("—", "—")

# <-----------------------------  گزارش گیری  --------------------------------------->

def count_attendance_for_term(term_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*) FROM attendance
            WHERE term_id = ?
        """, (term_id,))
        return c.fetchone()[0]

#todo: FinancialReport Functions

def get_all_student_terms_with_financials():
    """
    بازگرداندن لیست تمام ترم‌ها با اطلاعات مالی کامل برای گزارش‌گیری.
    """
    with get_connection() as conn:
        c = conn.cursor()

        # گرفتن مبلغ هر ترم از تنظیمات
        session_count = int(get_setting("term_session_count", 12))
        term_tuition = int(get_setting("term_tuition", 6000000))

        # گرفتن همه ترم‌ها همراه با اطلاعات مرتبط
        c.execute("""
            SELECT
                t.id as term_id,
                s.name as student_name,
                s.national_code,
                c.name as class_name,
                c.instrument,
                c.id as class_id,
                t.start_date,
                t.end_date,
                tr.name as teacher_name
            FROM student_terms t
            JOIN students s ON s.id = t.student_id
            JOIN classes c ON c.id = t.class_id
            JOIN teachers tr ON c.teacher_id = tr.id
            ORDER BY t.start_date DESC
        """)
        terms = c.fetchall()

        result = []

        for term in terms:
            (
                term_id, student_name, national_code, class_name,
                instrument, class_id, start_date, end_date, teacher_name
            ) = term

            paid_tuition = get_total_paid_for_term(term_id, 'tuition')
            paid_extra = get_total_paid_for_term(term_id, 'extra')
            total_paid = paid_tuition + paid_extra
            debt = term_tuition - paid_tuition
            if debt == 0:
                status = "تسویه"
            elif debt > 0:
                status = "بدهکار"
            else:
                status = "خطا در داده‌ها"  # چون نباید منفی باشه!

            # آخرین تاریخ پرداخت
            c.execute("""
                SELECT MAX(payment_date)
                FROM payments
                WHERE term_id = ?
            """, (term_id,))
            last_payment_date = c.fetchone()[0]

            result.append({
                "term_id": term_id,
                "student_name": student_name,
                "national_code": national_code,
                "class_name": class_name,
                "instrument": instrument,
                "teacher_name": teacher_name,
                "start_date": start_date,
                "end_date": end_date,
                "tuition": term_tuition,
                "paid_tuition": paid_tuition,
                "paid_extra": paid_extra,
                "total_paid": total_paid,
                "debt": debt,
                "status": status,
                "last_payment_date": last_payment_date
            })

        return result

#todo AttendanceReport Functions
def get_attendance_report_rows():
    """
    بازگرداندن لیست ترم‌ها با اطلاعات کلاس و حضور و غیاب برای گزارش‌گیری.
    """
    with get_connection() as conn:
        c = conn.cursor()

        # مرحله ۱: گرفتن لیست ترم‌ها همراه با اطلاعات مرتبط
        c.execute("""
            SELECT 
                t.id as term_id,
                s.name as student_name,
                t.start_date,
                t.end_date,
                cls.name as class_name,
                cls.instrument,
                tr.name as teacher_name
            FROM student_terms t
            JOIN students s ON s.id = t.student_id
            JOIN classes cls ON cls.id = t.class_id
            JOIN teachers tr ON cls.teacher_id = tr.id
            ORDER BY t.start_date ASC
        """)
        terms = c.fetchall()

        result = []

        # مرحله ۲: گرفتن حضور و غیاب هر ترم
        for (term_id, student_name, start_date, end_date,
             class_name, instrument, teacher_name) in terms:

            c.execute("""
                SELECT date, is_present
                FROM attendance
                WHERE term_id = ?
                ORDER BY date ASC
            """, (term_id,))
            attendance_rows = c.fetchall()

            attendance_dict = {
                row[0]: "حاضر" if row[1] == 1 else "غایب"
                for row in attendance_rows
            }

            result.append({
                "student_name": student_name,
                "teacher_name": teacher_name,
                "class_name": class_name,
                "instrument": instrument,
                "start_date": start_date,
                "end_date": end_date,
                "attendance": attendance_dict
            })

        return result

# todo: student term summary function

def get_student_term_summary_rows(student_name='', teacher_name='', class_name='',
                                   instrument_name='', day='', date_from='', date_to='',
                                   term_status=''):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            st.id AS term_id,
            s.id AS student_id,
            s.name AS student_name,
            s.national_code,
            c.name AS class_name,
            t.name AS teacher_name,
            c.instrument,
            c.day,
            c.start_time,
            st.start_date,
            st.end_date
        FROM student_terms st
        JOIN students s ON s.id = st.student_id
        JOIN classes c ON c.id = st.class_id
        JOIN teachers t ON t.id = c.teacher_id
        WHERE 1=1
    """

    params = []

    if student_name:
        query += " AND s.name LIKE ?"
        params.append(f"%{student_name}%")
    if teacher_name:
        query += " AND t.name LIKE ?"
        params.append(f"%{teacher_name}%")
    if class_name:
        query += " AND c.name LIKE ?"
        params.append(f"%{class_name}%")
    if instrument_name:
        query += " AND c.instrument LIKE ?"
        params.append(f"%{instrument_name}%")
    if day:
        query += " AND c.day = ?"
        params.append(day)
    if date_from:
        query += " AND st.start_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND st.start_date <= ?"
        params.append(date_to)
    if term_status == "active":
        query += " AND st.end_date IS NULL"
    elif term_status == "finished":
        query += " AND st.end_date IS NOT NULL"

    query += " ORDER BY st.start_date DESC"
    cursor.execute(query, params)
    terms = cursor.fetchall()

    # گرفتن تنظیم سقف جلسات ترم
    cursor.execute("SELECT value FROM settings WHERE key = 'term_session_count'")
    row = cursor.fetchone()
    session_limit = int(row[0]) if row else 12

    result = []
    for term in terms:
        (
            term_id, student_id, student_name, national_code,
            class_name, teacher_name, instrument, day, start_time,
            start_date, end_date
        ) = term

        # شمارش جلسات
        cursor.execute("""
            SELECT COUNT(*),
                   SUM(CASE WHEN is_present = 1 THEN 1 ELSE 0 END)
            FROM attendance
            WHERE term_id = ?
        """, (term_id,))
        session_row = cursor.fetchone()
        total_sessions = session_row[0] or 0
        present_sessions = session_row[1] or 0
        absent_sessions = total_sessions - present_sessions

        result.append([
            student_name,
            national_code,
            class_name,
            teacher_name,
            instrument,
            day,
            start_time,
            start_date,
            end_date,
            total_sessions,
            present_sessions,
            absent_sessions,
            round((present_sessions / total_sessions) * 100, 1) if total_sessions else 0
        ])

    conn.close()
    return result

# todo contacts list function
def fetch_all_contacts():
    with get_connection() as conn:
        c = conn.cursor()
        # هنرجویان
        c.execute("""
            SELECT name, national_code, phone, 'هنرجو' as role
            FROM students
        """)
        students = c.fetchall()

        # اساتید
        c.execute("""
            SELECT name, national_code, phone, 'استاد' as role
            FROM teachers
        """)
        teachers = c.fetchall()

        # ترکیب دو لیست
        return students + teachers

# todo: teachers summary function
def get_teacher_summary_rows():
    """
    بازگرداندن اطلاعات کامل اساتید برای گزارش‌گیری شامل مشخصات، سازهای تدریسی و روزهای کلاس.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT 
                t.name,
                t.national_code,
                t.teaching_card_number,
                t.phone,
                t.birth_date,
                t.card_number,
                t.iban,
                COALESCE(instrs.instruments, '—') AS instruments,
                COALESCE(days.days, '—') AS class_days
            FROM teachers t
            LEFT JOIN (
                SELECT teacher_id, GROUP_CONCAT(instrument, '/') AS instruments
                FROM teacher_instruments
                GROUP BY teacher_id
            ) instrs ON t.id = instrs.teacher_id
            LEFT JOIN (
                SELECT teacher_id, GROUP_CONCAT(DISTINCT day) AS days
                FROM classes
                GROUP BY teacher_id
            ) days ON t.id = days.teacher_id
            ORDER BY t.name COLLATE NOCASE
        """)
        result = []
        for row in c.fetchall():
            row = list(row)

            row[7] = row[7].replace(",", "/") if row[7] and row[7] != "—" else "—"
            row[8] = row[8].replace(",", "/") if row[8] and row[8] != "—" else "—"
            result.append(row)
        return result
