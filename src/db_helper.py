from data.db import get_connection  # expose the same connection behavior
from data.schema import create_tables
from data.migrations import (
    migrate_attendance_unique_constraint,
    migrate_drop_student_terms_term_id,
)

# <-------------------------------  profiles functions  ------------------------------------------------->
def create_pricing_profile(name: str, sessions: int, fee: int, currency_unit: str = None, is_default: bool = False):
    if currency_unit is None:
        currency_unit = get_setting("currency_unit", "toman")
    with get_connection() as conn:
        c = conn.cursor()
        if is_default:
            c.execute("UPDATE pricing_profiles SET is_default = 0")
        c.execute("""
            INSERT INTO pricing_profiles(name, sessions_limit, tuition_fee, currency_unit, is_default)
            VALUES (?, ?, ?, ?, ?)
        """, (name, sessions, fee, currency_unit, 1 if is_default else 0))
        conn.commit()
        return c.lastrowid

def list_pricing_profiles():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, name, sessions_limit, tuition_fee, currency_unit, is_default
            FROM pricing_profiles
            ORDER BY is_default DESC, name COLLATE NOCASE
        """)
        return c.fetchall()

def get_default_profile():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, name, sessions_limit, tuition_fee, currency_unit
            FROM pricing_profiles
            WHERE is_default=1 LIMIT 1
        """)
        return c.fetchone()

def set_term_config(term_id: int, sessions_limit: int, tuition_fee: int, currency_unit: str = None, profile_id: int = None):
    if currency_unit is None:
        currency_unit = get_setting("currency_unit", "toman")
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            UPDATE student_terms
               SET sessions_limit=?, tuition_fee=?, currency_unit=?, profile_id=?
             WHERE id=?
        """, (sessions_limit, tuition_fee, currency_unit, profile_id, term_id))
        conn.commit()

def get_term_config(term_id: int):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT sessions_limit, tuition_fee, currency_unit
            FROM student_terms
            WHERE id=?
        """, (term_id,))
        row = c.fetchone()
        if row:
            sl, fee, unit = row
            if sl is None:
                sl = int(get_setting("term_session_count", 12))
            if fee is None:
                fee = int(get_setting("term_fee", get_setting("term_tuition", 6000000)))
            if not unit:
                unit = get_setting("currency_unit", "toman")
            return {"sessions_limit": sl, "tuition_fee": fee, "currency_unit": unit}
        return {
            "sessions_limit": int(get_setting("term_session_count", 12)),
            "tuition_fee": int(get_setting("term_fee", get_setting("term_tuition", 6000000))),
            "currency_unit": get_setting("currency_unit", "toman"),
        }

# --- Pricing Profiles helpers ---

def get_pricing_profile_by_id(profile_id: int):
    """برگرداندن پروفایل بر اساس id (None اگر نبود)."""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, name, sessions_limit, tuition_fee, currency_unit, is_default
            FROM pricing_profiles
            WHERE id = ?
        """, (profile_id,))
        row = c.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "name": row[1],
            "sessions_limit": row[2],
            "tuition_fee": row[3],
            "currency_unit": row[4],
            "is_default": bool(row[5]),
        }

def apply_profile_to_term(term_id: int, profile_id: int):
    """
    پروفایل شهریه را روی ترم اعمال می‌کند (sessions_limit/tuition_fee/currency_unit و profile_id).
    """
    prof = get_pricing_profile_by_id(profile_id)
    if not prof:
        return False
    set_term_config(
        term_id,
        sessions_limit=prof["sessions_limit"],
        tuition_fee=prof["tuition_fee"],
        currency_unit=prof["currency_unit"],
        profile_id=prof["id"],
    )
    return True

def get_term_config_full(term_id: int):
    """
    کانفیگ کامل ترم + اطلاعات پروفایل (اگر داشته باشد).
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT st.sessions_limit, st.tuition_fee, st.currency_unit, st.profile_id,
                   pp.name
            FROM student_terms st
            LEFT JOIN pricing_profiles pp ON pp.id = st.profile_id
            WHERE st.id = ?
        """, (term_id,))
        row = c.fetchone()
        if not row:
            return None
        sl, fee, unit, pid, pname = row
        if sl is None:
            sl = int(get_setting("term_session_count", 12))
        if fee is None:
            fee = int(get_setting("term_fee", get_setting("term_tuition", 6000000)))
        if not unit:
            unit = get_setting("currency_unit", "toman")
        return {
            "sessions_limit": sl,
            "tuition_fee": fee,
            "currency_unit": unit,
            "profile_id": pid,
            "profile_name": pname,
        }

def set_default_pricing_profile(profile_id: int):
    """تغییر پروفایل پیش‌فرض (اختیاری اما مفید برای UI تنظیمات)."""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE pricing_profiles SET is_default = 0")
        c.execute("UPDATE pricing_profiles SET is_default = 1 WHERE id = ?", (profile_id,))
        conn.commit()

def clear_term_profile(term_id: int):
    """حذف نسبتِ پروفایل از ترم (ترم سفارشی می‌شود)."""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            UPDATE student_terms
               SET profile_id = NULL, updated_at = datetime('now','localtime')
             WHERE id = ?
        """, (term_id,))
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
    
def insert_student_term_if_not_exists(
    student_id, class_id, start_date, start_time,
    sessions_limit=None, tuition_fee=None, currency_unit=None, profile_id=None
):
    with get_connection() as conn:
        c = conn.cursor()

        # جلوگیری از تداخل استاد در همین روز/ساعت
        if has_teacher_weekly_time_conflict(class_id, start_time):
            return None

        # اگر ترم فعالِ دقیقا با همین start_date/start_time هست، همان را برگردان
        c.execute("""
            SELECT id
            FROM student_terms
            WHERE student_id=? AND class_id=? AND start_date=? AND start_time=? AND end_date IS NULL
        """, (student_id, class_id, start_date, start_time))
        row = c.fetchone()
        if row:
            term_id = row[0]
            # اگر ترم موجود است ولی کاربر مقدار سفارشی داده، روی همان ترم ست کن
            if any(v is not None for v in (sessions_limit, tuition_fee, currency_unit, profile_id)):
                if currency_unit is None:
                    currency_unit = get_setting("currency_unit", "toman")
                c.execute("""
                    UPDATE student_terms
                       SET sessions_limit = COALESCE(?, sessions_limit),
                           tuition_fee    = COALESCE(?, tuition_fee),
                           currency_unit  = COALESCE(?, currency_unit),
                           profile_id     = COALESCE(?, profile_id),
                           updated_at     = datetime('now','localtime')
                     WHERE id=?
                """, (sessions_limit, tuition_fee, currency_unit, profile_id, term_id))
                conn.commit()
            return term_id

        # اگر همان روز/ساعت جلسه‌ای برای این کلاس ثبت شده، بلاک
        c.execute("SELECT COUNT(*) FROM sessions WHERE class_id=? AND date=? AND time=?",
                  (class_id, start_date, start_time))
        if c.fetchone()[0] > 0:
            return None

        # عدم شروع قبل از پایان ترم قبلی
        c.execute("""
            SELECT end_date FROM student_terms
            WHERE student_id=? AND class_id=? AND end_date IS NOT NULL
            ORDER BY end_date DESC LIMIT 1
        """, (student_id, class_id))
        last = c.fetchone()
        if last and start_date < last[0]:
            return None

        # مقادیر پیش‌فرض برای فیلدهای سفارشی
        if sessions_limit is None:
            sessions_limit = int(get_setting("term_session_count", 12))
        if tuition_fee is None:
            tuition_fee = int(get_setting("term_fee", get_setting("term_tuition", 6000000)))
        if currency_unit is None:
            currency_unit = get_setting("currency_unit", "toman")

        # درج ترم جدید با مقادیر سفارشی
        c.execute("""
            INSERT INTO student_terms
                (student_id, class_id, start_date, start_time, end_date,
                 sessions_limit, tuition_fee, currency_unit, profile_id)
            VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?)
        """, (student_id, class_id, start_date, start_time,
              sessions_limit, tuition_fee, currency_unit, profile_id))
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
    اگر مجموع ثبت‌های ترم (حاضر + غایب) به سقف برسد و end_date هنوز خالی باشد،
    end_date = session_date می‌شود. مقدار True/False برمی‌گرداند که آیا end_date ست شد یا نه.
    """
    with get_connection() as conn:
        c = conn.cursor()

        # سقف ترم + end_date فعلی
        c.execute("""
            SELECT sessions_limit, end_date
            FROM student_terms
            WHERE id = ?
        """, (term_id,))
        row = c.fetchone()
        if not row:
            return False

        term_limit, current_end = row[0], row[1]
        if term_limit is None:
            # fallback به تنظیم سراسری اگر snapshot ترم خالی باشد
            term_limit = int(get_setting("term_session_count", 12))
        else:
            try:
                term_limit = int(term_limit)
            except:
                term_limit = int(get_setting("term_session_count", 12))

        # شمارش کل ثبت‌ها (حاضر + غایب)
        c.execute("SELECT COUNT(*) FROM attendance WHERE term_id = ?", (term_id,))
        total = c.fetchone()[0] or 0

        if current_end is None and total >= term_limit:
            c.execute("""
                UPDATE student_terms
                SET end_date = ?, updated_at = datetime('now','localtime')
                WHERE id = ?
            """, (session_date, term_id))
            conn.commit()
            return True

        return False

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
def ensure_term_config(term_id: int):
    cfg = get_term_config(term_id)  # همیشه چیزی برمی‌گرداند
    # اگر از قبل مقدار داشتیم، دست نزنیم (ایدمپوتنت)
    if cfg["sessions_limit"] and cfg["tuition_fee"] and cfg["currency_unit"]:
        return

    prof = get_default_profile()
    if prof:
        pid, name, sessions, fee, unit = prof
        set_term_config(term_id, sessions, fee, unit or get_setting("currency_unit", "toman"), profile_id=pid)
    else:
        sessions = int(get_setting("term_session_count", 12))
        fee      = int(get_setting("term_fee", get_setting("term_tuition", 6000000)))
        unit     = get_setting("currency_unit", "toman")
        set_term_config(term_id, sessions, fee, unit, profile_id=None)
        
def add_session(class_id, student_id, date, time,
                term_sessions_limit=None, term_tuition_fee=None,
                term_currency_unit=None, term_profile_id=None):
    conn = get_connection()
    c = conn.cursor()

    term_id = insert_student_term_if_not_exists(
        student_id, class_id, date, time,
        sessions_limit=term_sessions_limit,
        tuition_fee=term_tuition_fee,
        currency_unit=term_currency_unit,
        profile_id=term_profile_id
    )
    if not term_id:
        print(f"⛔️ ایجاد ترم/جلسه ممکن نشد.")
        conn.close()
        return None
    
    # جلوگیری از ثبت ناسازگار با end_date
    c.execute("SELECT end_date FROM student_terms WHERE id=?", (term_id,))
    row = c.fetchone()
    if row and row[0] and date > row[0]:
        print("⛔️ ترم پایان یافته؛ ثبت جلسه بعد از end_date ممنوع است.")
        conn.close()
        return None

    try:
        c.execute("""
            INSERT INTO sessions (class_id, student_id, term_id, date, time)
            VALUES (?, ?, ?, ?, ?)
        """, (class_id, student_id, term_id, date, time))
        conn.commit()
        return term_id
    except sqlite3.IntegrityError:
        print("⛔️ جلسه تکراری یا خطا در درج.")
        return None


def fetch_sessions_by_class(class_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT s.id, st.name, s.date, s.time, s.duration
            FROM sessions AS s
            JOIN students AS st ON s.student_id = st.id
            WHERE s.class_id = ?
            ORDER BY
                CAST(substr(TRIM(s.time), 1, 2) AS INTEGER),
                CAST(substr(TRIM(s.time), 4, 2) AS INTEGER),
                CAST(substr(TRIM(s.date), 1, 4) AS INTEGER),
                CAST(substr(TRIM(s.date), 6, 2) AS INTEGER),
                CAST(substr(TRIM(s.date), 9, 2) AS INTEGER)

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
    فقط «جلسات آینده»ی ترم‌های پایان‌یافته را حذف می‌کند.
    خروجی: تعداد جلسات حذف‌شده (int)
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, student_id, class_id, end_date
            FROM student_terms
            WHERE end_date IS NOT NULL
        """)
        expired_terms = c.fetchall()

        total_deleted = 0
        for term_id, student_id, class_id, end_date in expired_terms:
            c.execute("""
                DELETE FROM sessions
                WHERE term_id = ?
                  AND student_id = ?
                  AND class_id = ?
                  AND date > ?
            """, (term_id, student_id, class_id, end_date))
            total_deleted += c.rowcount or 0

        conn.commit()
        return total_deleted


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

def has_teacher_weekly_time_conflict(class_id, session_time, exclude_session_id=None):
    """
    آیا استادِ این کلاس، در همین روزِ هفته و همین ساعت، جلسهٔ دیگری (برای هر هنرجویی) دارد؟
    - class_id: کلاس انتخابی
    - session_time: رشته "HH:MM"
    - exclude_session_id: در مود ویرایش، شناسه‌ی جلسه‌ای که داریم ادیتش می‌کنیم (برای جلوگیری از false positive)
    """
    with get_connection() as conn:
        c = conn.cursor()
        # روز هفته و استادِ کلاسِ جدید
        c.execute("SELECT teacher_id, day FROM classes WHERE id = ?", (class_id,))
        row = c.fetchone()
        if not row:
            return False
        teacher_id, weekday = row

        query = """
            SELECT s.id
            FROM sessions s
            JOIN classes c2 ON c2.id = s.class_id
            WHERE c2.teacher_id = ?
              AND c2.day = ?
              AND s.time = ?
        """
        params = [teacher_id, weekday, session_time]

        if exclude_session_id:
            query += " AND s.id != ?"
            params.append(exclude_session_id)

        c.execute(query, params)
        return c.fetchone() is not None

def get_session_count_per_student():
    conn = get_connection()  # همان روشی که در پروژه‌ات برای اتصال استفاده می‌کنی
    cur = conn.cursor()
    cur.execute("""
        SELECT student_id, COUNT(*) 
        FROM sessions
        GROUP BY student_id
    """)
    rows = cur.fetchall()
    conn.close()
    # خروجی: {student_id: count}
    return {sid: cnt for (sid, cnt) in rows}

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
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT 
                t.id as term_id,
                t.start_date,
                t.end_date,
                t.created_at,
                COALESCE(SUM(CASE WHEN p.payment_type='tuition' THEN p.amount ELSE 0 END), 0) as paid_tuition,
                COALESCE(SUM(CASE WHEN p.payment_type='extra' THEN p.amount ELSE 0 END), 0) as paid_extra,
                COUNT(p.id) as payment_count,
                COALESCE(t.tuition_fee, 0) as term_fee  -- 👈 از خودِ ترم
            FROM student_terms t
            LEFT JOIN payments p ON t.id = p.term_id
            WHERE t.student_id = ? AND t.class_id = ?
            GROUP BY t.id, t.start_date, t.end_date, t.created_at, t.tuition_fee
            ORDER BY t.start_date DESC
        """, (student_id, class_id))
        rows = c.fetchall()

    result = []
    for term_id, start_date, end_date, created_at, paid_tuition, paid_extra, payment_count, term_fee in rows:
        if not term_fee:
            term_fee = int(get_setting("term_fee", get_setting("term_tuition", 6000000)))  # fallback
        debt = term_fee - paid_tuition
        status = "تسویه" if debt == 0 else "بدهکار" if debt > 0 else "خطا"
        term_status = "فعال" if end_date is None else "تکمیل شده"
        result.append({
            "term_id": term_id,
            "start_date": start_date,
            "end_date": end_date,
            "created_at": created_at,
            "paid_tuition": paid_tuition,
            "paid_extra": paid_extra,
            "total_paid": paid_tuition + paid_extra,
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

def get_payment_by_id(payment_id):
    """
    دریافت جزئیات یک پرداخت بر اساس ID.
    خروجی: dict شامل id, student_id, class_id, term_id, amount, payment_date (شمسی "YYYY-MM-DD"),
            payment_type ('tuition'/'extra'), description
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, student_id, class_id, term_id, amount, payment_date, payment_type, description
            FROM payments
            WHERE id = ?
        """, (payment_id,))
        row = c.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "student_id": row[1],
            "class_id": row[2],
            "term_id": row[3],
            "amount": row[4],
            "payment_date": row[5],   # تاریخ شمسی به صورت "YYYY-MM-DD"
            "payment_type": row[6],   # 'tuition' یا 'extra'
            "description": row[7],
        }
    
def get_term_tuition_by_id(term_id: int):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT tuition_fee FROM student_terms WHERE id=?", (term_id,))
        row = c.fetchone()
        return int(row[0]) if row and row[0] is not None else None

# db_helper.py
def get_term_sessions_limit_by_id(term_id: int):
    """
    سقف جلسات ترم را برمی‌گرداند.
    اول از student_terms.sessions_limit، اگر تهی بود از pricing_profiles.sessions_limit
    و در نهایت از تنظیمات پیش‌فرض term_session_count.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT
              COALESCE(st.sessions_limit, pp.sessions_limit) AS lim
            FROM student_terms st
            LEFT JOIN pricing_profiles pp ON pp.id = st.profile_id
            WHERE st.id = ?
        """, (term_id,))
        row = c.fetchone()
        if row and row[0] is not None:
            return int(row[0])
    # fallback بیرون از DB (در خود PaymentManager هم دوباره fallback می‌کنیم)
    return None

def get_finished_terms_with_future_sessions():
    """
    ترم‌هایی که end_date دارند و هنوز جلساتی با تاریخ > end_date برایشان ثبت است.
    خروجی: [(term_id, student_id, student_name, class_id, class_name, end_date, future_count), ...]
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT
                t.id AS term_id,
                t.student_id,
                s.name AS student_name,
                t.class_id,
                c2.name AS class_name,
                t.end_date,
                SUM(CASE WHEN sess.date > t.end_date THEN 1 ELSE 0 END) AS future_count
            FROM student_terms t
            JOIN students s ON s.id = t.student_id
            JOIN classes  c2 ON c2.id = t.class_id
            LEFT JOIN sessions sess ON sess.term_id = t.id
            WHERE t.end_date IS NOT NULL
            GROUP BY t.id
            HAVING SUM(CASE WHEN sess.date > t.end_date THEN 1 ELSE 0 END) > 0
            ORDER BY t.end_date DESC
        """)
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
    """
    ثبت حضور/غیاب برای تاریخ مشخص. اگر با این ثبت سقف پر شود،
    check_and_set_term_end_by_id همان روز را end_date می‌گذارد.
    مقدار True/False برمی‌گرداند که آیا end_date ست شد یا نه.
    """
    if not term_id:
        term_id = get_term_id_by_student_class_and_date(student_id, class_id, date)
    if not term_id:
        return False  # ترمی پیدا نشد؛ چیزی ثبت نشد

    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO attendance (student_id, class_id, term_id, date, is_present)
            VALUES (?, ?, ?, ?, ?)
            """,
            (student_id, class_id, term_id, date, is_present)
        )
        conn.commit()

    # بعد از ثبت، بررسی و در صورت لزوم بستن ترم (end_date = همان date)
    ended = check_and_set_term_end_by_id(term_id, student_id, class_id, date)
    return ended

def delete_attendance(student_id, class_id, term_id, date_str):
    """حذف یک رکورد حضور بر اساس هنرجو/کلاس/ترم/تاریخ (رشته شمسی)."""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            DELETE FROM attendance
            WHERE student_id = ? AND class_id = ? AND term_id = ? AND date = ?
        """, (student_id, class_id, term_id, date_str))
        conn.commit()
        return c.rowcount  # برای اطلاع از تعداد رکوردهای حذف‌شده

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

def count_present_attendance_for_term(term_id: int) -> int:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*) FROM attendance
            WHERE term_id = ? AND is_present = 1
        """, (term_id,))
        row = c.fetchone()
        return row[0] or 0
    
def recalc_term_end_by_id(term_id: int):
    """اگر مجموع ثبت‌ها از limit کمتر باشد، end_date را NULL می‌کند؛
       اگر به حد رسیده باشد و end_date خالی است، همان امروز را نمی‌زند (این کار با insert انجام می‌شود).
    """
    with get_connection() as conn:
        c = conn.cursor()
        # limit و end_date فعلی
        c.execute("SELECT sessions_limit, end_date FROM student_terms WHERE id=?", (term_id,))
        row = c.fetchone()
        if not row:
            return
        limit, end_date = row[0], row[1]
        if limit is None:
            try:
                limit = int(get_setting("term_session_count", 12))
            except:
                limit = 12
        else:
            try:
                limit = int(limit)
            except:
                limit = 12

        # شمارش کل ثبت‌ها (حاضر + غایب)
        c.execute("SELECT COUNT(*) FROM attendance WHERE term_id=?", (term_id,))
        total = c.fetchone()[0] or 0

        # اگر قبلاً بسته شده ولی حالا کمتر از limit شد → بازش کن
        if end_date is not None and total < limit:
            c.execute("""
                UPDATE student_terms
                SET end_date = NULL, updated_at = datetime('now','localtime')
                WHERE id = ?
            """, (term_id,))
            conn.commit()

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
    with get_connection() as conn:
        c = conn.cursor()
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
                tr.name as teacher_name,
                COALESCE(t.tuition_fee, 0) as term_fee
            FROM student_terms t
            JOIN students s ON s.id = t.student_id
            JOIN classes c   ON c.id = t.class_id
            JOIN teachers tr ON c.teacher_id = tr.id
            ORDER BY t.start_date DESC
        """)
        terms = c.fetchall()

        result = []
        for (term_id, student_name, national_code, class_name, instrument,
             class_id, start_date, end_date, teacher_name, term_fee) in terms:

            if not term_fee:
                term_fee = int(get_setting("term_fee", get_setting("term_tuition", 6000000)))  # fallback

            paid_tuition = get_total_paid_for_term(term_id, 'tuition')
            paid_extra   = get_total_paid_for_term(term_id, 'extra')
            debt = term_fee - paid_tuition
            status = "تسویه" if debt == 0 else "بدهکار" if debt > 0 else "خطا در داده‌ها"
            term_status = "فعال" if end_date is None else "تکمیل شده"

            # آخرین تاریخ پرداخت
            c.execute("SELECT MAX(payment_date) FROM payments WHERE term_id = ?", (term_id,))
            last_payment_date = c.fetchone()[0]

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
                "tuition": term_fee,
                "paid_tuition": paid_tuition,
                "paid_extra": paid_extra,
                "total_paid": paid_tuition + paid_extra,
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
