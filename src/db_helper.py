import sqlite3
from datetime import datetime, timedelta
from paths import DB_PATH

# تابع اتصال به دیتابیس
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn
def create_tables():
    """Create all tables with FKs, UNIQUE constraints, indexes, and audit columns."""
    with get_connection() as conn:
        c = conn.cursor()

        # Users table
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              mobile TEXT UNIQUE NOT NULL,
              password TEXT NOT NULL
            );
        ''')
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

        # student_terms table
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

        # add term_id to student_terms
        c.execute("PRAGMA table_info(student_terms)")
        columns = [row[1] for row in c.fetchall()]
        if "term_id" not in columns:
            c.execute("ALTER TABLE student_terms ADD COLUMN term_id INTEGER")
            print("✅ ستون term_id به جدول student_terms اضافه شد و مقداردهی شد.")

        # add start_time to student_terms (for distinguishing same-day sessions)
        c.execute("PRAGMA table_info(student_terms)")
        columns = [row[1] for row in c.fetchall()]
        if "start_time" not in columns:
            c.execute("ALTER TABLE student_terms ADD COLUMN start_time TEXT")
            print("✅ ستون start_time به جدول student_terms اضافه شد.")

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


        # Attendance table (ساخت اولیه یا بعد از مهاجرت)
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
            UNIQUE(student_id, class_id, term_id, date)
        );
        """)
            # Table of registered terms for which the end-of-term message has already been displayed.
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
        # Table of recorded messages sent as reminders for term renewal 
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
        # بلافاصله بعد از ساخت جدول notified_terms
        c.execute("PRAGMA table_info(notified_terms)")
        columns = [row[1] for row in c.fetchall()]
        if "session_date" not in columns:
            c.execute("ALTER TABLE notified_terms ADD COLUMN session_date TEXT")
            print("✅ ستون session_date به جدول notified_terms اضافه شد.")

        if "session_time" not in columns:
            c.execute("ALTER TABLE notified_terms ADD COLUMN session_time TEXT")
            print("✅ ستون session_time به جدول notified_terms اضافه شد.")

        # Indexes for faster lookups
        # For faster connection between students and classes
        c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_student_id ON sessions(student_id);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_class_id ON sessions(class_id);")

        # For linking the class with the instructor
        c.execute("CREATE INDEX IF NOT EXISTS idx_classes_teacher_id ON classes(teacher_id);")

        # If you search frequently, use the class day as a filter
        c.execute("CREATE INDEX IF NOT EXISTS idx_classes_day ON classes(day);")

        # If you want to sort the payments by student, class, or date
        c.execute("CREATE INDEX IF NOT EXISTS idx_payments_student_id ON payments(student_id);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_payments_class_id ON payments(class_id);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(payment_date);")

        # فقط وقتی دیتابیس تازه ساخته شده و جدول خالیه، مقادیر پیش‌فرض رو وارد کن
        c.execute("SELECT COUNT(*) FROM settings")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("currency_unit", "toman"))
            c.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("sms_enabled", "فعال"))
            c.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("term_session_count", "12"))
            c.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("term_tuition", "6000000"))

        conn.commit()

    migrate_attendance_unique_constraint()  # اجرای مهاجرت بعد از ساخت جداول
    migrate_student_terms_fk_to_sessions()


def migrate_attendance_unique_constraint():
    """Upgrade attendance table to have UNIQUE(student_id, class_id, term_id, date) instead of old constraint."""
    with get_connection() as conn:
        c = conn.cursor()

        # بررسی وجود جدول
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='attendance';")
        if not c.fetchone():
            return

        # بررسی ساختار UNIQUE
        c.execute("PRAGMA index_list(attendance);")
        indexes = c.fetchall()
        if any("term_id" in idx[1] for idx in indexes):
            print("ℹ️ جدول attendance قبلاً term_id را در UNIQUE دارد. مهاجرت لازم نیست.")
            return

        print("🔄 اجرای مهاجرت UNIQUE برای جدول attendance...")

        # بکاپ جدول
        c.execute("ALTER TABLE attendance RENAME TO attendance_old;")

        # ساخت جدول جدید با کلید یکتا صحیح
        c.execute("""
            CREATE TABLE attendance (
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
                UNIQUE(student_id, class_id, term_id, date)
            );
        """)

        # انتقال داده‌ها
        c.execute("""
            INSERT OR IGNORE INTO attendance (student_id, class_id, term_id, date, is_present, created_at, updated_at)
            SELECT student_id, class_id, term_id, date, is_present, created_at, updated_at
            FROM attendance_old;
        """)

        # حذف بکاپ
        c.execute("DROP TABLE attendance_old;")

        conn.commit()
        print("✅ مهاجرت جدول attendance با موفقیت انجام شد.")

def migrate_student_terms_fk_to_sessions():
    with get_connection() as conn:
        c = conn.cursor()

        # اگر قبلاً FK موردنظر اضافه شده، کاری نکن
        c.execute("PRAGMA foreign_key_list('student_terms');")
        fk_list = c.fetchall()
        if any(row[2] == 'sessions' and row[3] == 'term_id' for row in fk_list):
            print("ℹ️ FK student_terms.term_id → sessions(id) قبلاً وجود دارد.")
            return

        print("🔄 شروع مهاجرت student_terms برای افزودن FK به sessions(id)...")

        # جدول جدید با قید FK
        c.execute("""
            CREATE TABLE IF NOT EXISTS student_terms_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                class_id INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT,
                term_id INTEGER,
                start_time TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                updated_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY(class_id)   REFERENCES classes(id)  ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY(term_id)    REFERENCES sessions(id) ON DELETE SET NULL ON UPDATE CASCADE
            );
        """)

        # انتقال ایمن داده‌ها:
        # اگر term_id معتبر نباشد (جلسه‌ای با آن id وجود نداشته باشد)، به NULL ست می‌شود.
        c.execute("""
            INSERT INTO student_terms_new (id, student_id, class_id, start_date, end_date, term_id, start_time, created_at, updated_at)
            SELECT st.id,
                   st.student_id,
                   st.class_id,
                   st.start_date,
                   st.end_date,
                   CASE WHEN EXISTS (SELECT 1 FROM sessions s WHERE s.id = st.term_id)
                        THEN st.term_id
                        ELSE NULL
                   END AS term_id,
                   st.start_time,
                   st.created_at,
                   st.updated_at
            FROM student_terms st;
        """)

        # جایگزینی جدول
        c.execute("DROP TABLE student_terms;")
        c.execute("ALTER TABLE student_terms_new RENAME TO student_terms;")

        conn.commit()
        print("✅ FK term_id → sessions(id) با ON DELETE SET NULL و ON UPDATE CASCADE اضافه شد.")

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

# --- Boolean settings helpers (store as "0"/"1") ---

def _normalize_bool_str(s: str) -> bool:
    if s is None:
        return False
    s = str(s).strip().lower()
    return s in {"1", "true", "yes", "on", "فعال", "faal", "enable", "enabled"}

def get_setting_bool(key: str, default: bool = False) -> bool:
    raw = get_setting(key, None)
    if raw is None:
        return default
    s = str(raw).strip().lower()
    if s in {"1", "true", "yes", "on", "فعال", "faal", "enable", "enabled"}:
        return True
    if s in {"0", "false", "no", "off", "غیرفعال", "gheyre faal", "disable", "disabled"}:
        return False
    # مقدار ناشناخته: به‌صورت محافظه‌کارانه default
    return default

def set_setting_bool(key: str, value: bool):
    set_setting(key, "1" if bool(value) else "0")

def ensure_bool_setting(key: str, default: bool = False):
    """
    مهاجرت نرم: اگر مقدار فعلی هنوز «رشته‌ی فارسی/لاتین» باشد،
    آن را به 0/1 تبدیل می‌کند. اگر مقدار وجود نداشت، default ست می‌شود.
    """
    raw = get_setting(key, None)
    if raw is None:
        set_setting_bool(key, default)
        return
    # اگر قبلاً 0/1 بوده، کاری نکن
    if str(raw).strip() in {"0", "1"}:
        return
    # تبدیلِ هر چیز دیگری به 0/1
    set_setting_bool(key, _normalize_bool_str(raw))

# <-------------------------------  Notifications  ------------------------------------------------->
def get_unnotified_expired_terms():
    """
    لیست ترم‌هایی که end_date آنها ست شده ولی هنوز نوتیف نداده‌ایم.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT 
                t.student_id,
                t.class_id,
                s.name,
                s.national_code,
                c.name,
                c.day,
                t.id      AS term_id,
                t.end_date   AS session_date,
                t.start_time AS session_time
            FROM student_terms t
            JOIN students s ON s.id = t.student_id
            JOIN classes c  ON c.id = t.class_id
            WHERE t.end_date IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 
                  FROM notified_terms n 
                  WHERE n.term_id = t.id
              )
        """)
        return c.fetchall()


def mark_terms_as_notified(term_info_list):
    """
    term_info_list = list of (term_id, student_id, class_id, session_date, session_time)
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.executemany("""
            INSERT OR IGNORE INTO notified_terms (term_id, student_id, class_id, session_date, session_time)
            VALUES (?, ?, ?, ?, ?)
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
    
def insert_student_term_if_not_exists(student_id, class_id, start_date, start_time):

    """
    ترم جدید فقط اگر در همان تاریخ، جلسه‌ای از هنرجوی دیگر در همان ساعت نداشته باشد،
    و همچنین از تاریخ پایان ترم قبلی زودتر نباشد، ثبت می‌شود.
    """
    with get_connection() as conn:
        c = conn.cursor()

        # بررسی اینکه آیا ترمی با همین start_date وجود دارد یا نه
        c.execute("""
            SELECT id
            FROM student_terms
            WHERE student_id = ?
            AND class_id   = ?
            AND start_date = ?
            AND start_time = ?
            AND end_date IS NULL
        """, (student_id, class_id, start_date, start_time))
        existing = c.fetchone()
        if existing:
            return existing[0]

         # بررسی اینکه آیا جلسه‌ای از هنرجوی دیگر در این روز و ساعت وجود دارد

        c.execute("""
            SELECT COUNT(*) FROM sessions
            WHERE class_id = ? AND date = ? AND time = ? AND student_id != ?
        """, (class_id, start_date, start_time, student_id))
        conflict_count = c.fetchone()[0]
        if conflict_count > 0:
            return None  # تداخل با هنرجوی دیگر

        # ⛳️ بررسی تاریخ پایان آخرین ترم هنرجو
        c.execute("""
            SELECT end_date FROM student_terms
            WHERE student_id = ? AND class_id = ? AND end_date IS NOT NULL
            ORDER BY end_date DESC LIMIT 1
        """, (student_id, class_id))
        row = c.fetchone()
        if row:
            last_end_date = row[0]
            # فقط اگر تاریخ شروع جدید **قبل** از پایان قبلی باشه، اجازه نمی‌ده
            if start_date < last_end_date:
                return None

        # ✅ درج ترم جدید
        c.execute("""
            INSERT INTO student_terms (student_id, class_id, start_date, start_time, end_date)
            VALUES (?, ?, ?, ?, NULL)
        """, (student_id, class_id, start_date, start_time))

        print(f"📌 Checking for term: sid={student_id}, cid={class_id}, date={start_date}, time={start_time}")

        conn.commit()   
        return c.lastrowid

def delete_future_sessions(student_id, class_id, session_date):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM sessions WHERE student_id=? AND class_id=? AND date>=?",
            (student_id, class_id, session_date)
        )
        conn.commit()

def check_and_set_term_end_by_id(term_id, student_id, class_id, session_date):
    """
    اگر تعداد حضور >= term_session_count شد،
    برای آن ترم end_date را برابر session_date بگذار.
    """
    with get_connection() as conn:
        c = conn.cursor()

        # شمارش جلسات با حضور برای این term_id
        c.execute("""
            SELECT COUNT(*) FROM attendance
            WHERE term_id = ? AND is_present = 1
        """, (term_id,))
        present_count = c.fetchone()[0]

        term_limit = int(get_setting("term_session_count", 12))
        if present_count >= term_limit:
            # ثبت تاریخ پایان ترم
            c.execute("""
                UPDATE student_terms
                SET end_date = ?, updated_at = datetime('now','localtime')
                WHERE id = ?
            """, (session_date, term_id))
            conn.commit()

def delete_sessions_for_term(term_id):
    """
    همه جلسات مربوط به term_id را (گذشته و آینده) حذف می‌کند.
    """
    with get_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE term_id = ?", (term_id,))
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

    # اطمینان از وجود ترم
    term_id = insert_student_term_if_not_exists(student_id, class_id, date, time)
    if not term_id:
        print(f"⛔️ جلسه افزوده نشد، زیرا امکان ایجاد ترم جدید برای {student_id=} در {date=} وجود ندارد.")
        conn.close()
        return None

    try:
        # ثبت جلسه
        c.execute("""
            INSERT INTO sessions (class_id, student_id, term_id, date, time)
            VALUES (?, ?, ?, ?, ?)
        """, (class_id, student_id, term_id, date, time))
        session_id = c.lastrowid

        # حالا session_id رو به عنوان term_id در student_terms ذخیره کن
        c.execute("UPDATE student_terms SET term_id = ? WHERE id = ?", (session_id, term_id))

        conn.commit()
        return term_id
    except sqlite3.IntegrityError:
        print("⛔️ جلسه تکراری یا خطا در درج.")
        return None


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
        # اطلاعات جلسه را ابتدا بگیر
        c = conn.cursor()
        c.execute("SELECT student_id, class_id, term_id FROM sessions WHERE id=?", (session_id,))
        row = c.fetchone()
        if not row:
            return
        student_id, class_id, term_id = row

        # حذف جلسه
        conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
        conn.commit()
        
    # اگر ترم هیچ پرداختی ندارد و هیچ جلسه‌ای دیگر ندارد، آن را حذف کن
    delete_term_if_no_payments(student_id, class_id, term_id)

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

def update_session(session_id, class_id, student_id, term_id, date, time, duration=30):

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
    """
    with get_connection() as conn:
        c = conn.cursor()

        # دریافت ترم‌هایی که end_date دارند
        c.execute("""
            SELECT id, student_id, class_id, end_date
            FROM student_terms
            WHERE end_date IS NOT NULL
        """)
        expired_terms = c.fetchall()

        for term_id, student_id, class_id, end_date in expired_terms:
            # حذف فقط سشن‌هایی که به این term_id تعلق دارن و تاریخشون بعد از end_date هست
            c.execute("""
                DELETE FROM sessions
                WHERE term_id = ?
                  AND student_id = ?
                  AND class_id = ?
                  AND date > ?
            """, (term_id, student_id, class_id, end_date))

        conn.commit()



def get_session_count_per_class():
    """
    تعداد جلسات ثبت‌شده برای هر کلاس (شامل جلسات متعدد یک هنرجو).
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT class_id, COUNT(*)
            FROM sessions
            GROUP BY class_id
        """)
        return dict(c.fetchall())

def get_student_count_per_class():
    """
    تعداد هنرجویان منحصر به فرد برای هر کلاس (بدون تکرار).
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
    تمام جلسات ثبت‌شده برای کلاس خاص، همراه با نام هنرجو و استاد.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT students.id, students.name, teachers.name, sessions.time
            FROM students
            JOIN sessions ON students.id = sessions.student_id
            JOIN classes ON sessions.class_id = classes.id
            JOIN teachers ON classes.teacher_id = teachers.id
            WHERE classes.id = ?
            ORDER BY sessions.time, students.name COLLATE NOCASE
        """, (class_id,))
        return c.fetchall()

def fetch_students_with_active_terms_for_class(class_id, selected_date):
    """
    هنرجویانی که برای کلاس خاص ترم فعال دارند، همراه با نام هنرجو و استاد.
    برای استفاده در پنجره حضور و غیاب.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT DISTINCT students.id, students.name, teachers.name
            FROM students
            JOIN student_terms ON students.id = student_terms.student_id
            JOIN classes ON student_terms.class_id = classes.id
            JOIN teachers ON classes.teacher_id = teachers.id
            WHERE classes.id = ? 
            AND student_terms.start_date <= ?
            AND (student_terms.end_date IS NULL OR student_terms.end_date >= ?)
            ORDER BY students.name COLLATE NOCASE
        """, (class_id, selected_date, selected_date))
        return c.fetchall()
    
def delete_student_term_by_id(term_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM student_terms WHERE id = ?", (term_id,))
        conn.commit()


def get_last_term_end_date(student_id, class_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT end_date
            FROM student_terms
            WHERE student_id = ? AND class_id = ?
            AND end_date IS NOT NULL
            ORDER BY end_date DESC
            LIMIT 1
        """, (student_id, class_id))
        row = c.fetchone()
        return row[0] if row else None
    
def get_session_by_id(session_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT student_id, class_id, term_id
            FROM sessions
            WHERE id = ?
        """, (session_id,))
        return c.fetchone()

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
               payments.amount, payments.payment_date, payments.description, payments.payment_type,
               classes.id AS class_id
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

def get_all_terms_for_student_class(student_id, class_id):
    """
    تمام ترم‌های هنرجو در یک کلاس خاص (فعال و غیرفعال) را برمی‌گرداند.
    برای مدیریت پرداخت‌ها استفاده می‌شود.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, start_date, end_date, created_at
            FROM student_terms
            WHERE student_id = ? AND class_id = ?
            ORDER BY start_date DESC
        """, (student_id, class_id))
        return c.fetchall()

def get_terms_for_payment_management(student_id, class_id):
    """
    تمام ترم‌های هنرجو در یک کلاس خاص را با اطلاعات مالی برمی‌گرداند.
    برای مدیریت پرداخت‌ها استفاده می‌شود.
    """
    with get_connection() as conn:
        c = conn.cursor()
        
        # گرفتن مبلغ هر ترم از تنظیمات
        term_tuition = int(get_setting("term_tuition", 6000000))
        
        c.execute("""
            SELECT 
                t.id as term_id,
                t.start_date,
                t.end_date,
                t.created_at,
                COALESCE(SUM(CASE WHEN p.payment_type = 'tuition' THEN p.amount ELSE 0 END), 0) as paid_tuition,
                COALESCE(SUM(CASE WHEN p.payment_type = 'extra' THEN p.amount ELSE 0 END), 0) as paid_extra,
                COUNT(p.id) as payment_count
            FROM student_terms t
            LEFT JOIN payments p ON t.id = p.term_id
            WHERE t.student_id = ? AND t.class_id = ?
            GROUP BY t.id, t.start_date, t.end_date, t.created_at
            ORDER BY t.start_date DESC
        """, (student_id, class_id))
        
        terms = c.fetchall()
        result = []
        
        for term in terms:
            term_id, start_date, end_date, created_at, paid_tuition, paid_extra, payment_count = term
            total_paid = paid_tuition + paid_extra
            debt = term_tuition - paid_tuition
            status = "تسویه" if debt == 0 else "بدهکار" if debt > 0 else "خطا"
            term_status = "فعال" if end_date is None else "تکمیل شده"
            
            result.append({
                "term_id": term_id,
                "start_date": start_date,
                "end_date": end_date,
                "created_at": created_at,
                "paid_tuition": paid_tuition,
                "paid_extra": paid_extra,
                "total_paid": total_paid,
                "debt": debt,
                "status": status,
                "term_status": term_status,
                "payment_count": payment_count
            })
        
        return result

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
    with get_connection() as conn:
        conn.execute("""
            UPDATE payments
            SET amount = ?, payment_date = ?, payment_type = ?, description = ?, updated_at = datetime('now','localtime')
            WHERE id = ?
        """, (amount, date, payment_type, description, payment_id))
        conn.commit()



def fetch_students_sessions_for_class_on_date(class_id, selected_date):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT s.id, s.name, t.name, sess.time, sess.term_id
            FROM sessions sess
            JOIN students s ON s.id = sess.student_id
            JOIN classes c2 ON sess.class_id = c2.id
            JOIN teachers t ON c2.teacher_id = t.id
            JOIN student_terms st ON st.id = sess.term_id
            WHERE sess.class_id = ?
              AND st.start_date <= ?
              AND (st.end_date IS NULL OR st.end_date >= ?)
            ORDER BY sess.time, s.name COLLATE NOCASE
        """, (class_id, selected_date, selected_date))
        return c.fetchall()


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

def count_attendance_by_term(student_id, class_id, term_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*) FROM attendance
            WHERE student_id = ? AND class_id = ? AND term_id = ?
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
    if not term_id:
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
    
    # پاس دادن term_id مستقیم به تابع
    check_and_set_term_end_by_id(term_id, student_id, class_id, date)

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

# <-----------------------------  functions for Reporting windows(reports_window.py)--------------------------------------->

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
    شامل ترم‌های فعال و غیرفعال.
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

            # تعیین وضعیت ترم
            term_status = "فعال" if end_date is None else "تکمیل شده"

            result.append({
                "term_id": term_id,
                "student_name": student_name,
                "national_code": national_code,
                "class_name": class_name,
                "class_id": class_id,
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
                "term_status": term_status,
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
                cls.id as class_id,          -- اضافه شد
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
             class_id, class_name, instrument, teacher_name) in terms:

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
                "class_id": class_id,         # اضافه شد
                "class_name": class_name,
                "instrument": instrument,
                "start_date": start_date,
                "end_date": end_date,
                "attendance": attendance_dict
            })

        return result

# todo: student term summary function

def get_student_term_summary_rows(student_name='', teacher_name='', class_name='',class_id='',instrument_name='', day='', date_from='', date_to='',term_status=''):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            st.id AS term_id,
            s.id AS student_id,
            s.name AS student_name,
            s.national_code,
            c.id AS class_id,
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
    if class_id:
        query += " AND c.id = ?"
        params.append(class_id)
    elif class_name:
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
            term_id, student_id, student_name, national_code,class_id,
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
            class_id,
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
