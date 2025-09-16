import sqlite3
import logging
from data.db import get_connection

logger = logging.getLogger(__name__)


def ensure_term_config(term_id: int):
	from data.profiles_repo import get_default_profile
	from data.settings_repo import get_setting
	from data.profiles_repo import set_term_config
	from data.profiles_repo import get_term_config
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
	from data.terms_repo import insert_student_term_if_not_exists
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
		logger.warning(f"⛔️ ایجاد ترم/جلسه ممکن نشد.")
		conn.close()
		return None
	
	# جلوگیری از ثبت ناسازگار با end_date
	c.execute("SELECT end_date FROM student_terms WHERE id= ?", (term_id,))
	row = c.fetchone()
	if row and row[0] and date > row[0]:
		logger.warning("⛔️ ترم پایان یافته؛ ثبت جلسه بعد از end_date ممنوع است.")
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
		logger.warning("⛔️ جلسه تکراری یا خطا در درج.")
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


def delete_future_sessions(student_id, class_id, session_date):
	with get_connection() as conn:
		conn.execute(
			"DELETE FROM sessions WHERE student_id=? AND class_id=? AND date>=?",
			(student_id, class_id, session_date)
		)
		conn.commit()


def is_class_slot_taken(class_id, date, time):
	with get_connection() as conn:
		c = conn.cursor()
		c.execute("""
			SELECT COUNT(*) FROM sessions
			WHERE class_id = ? AND date = ? AND time = ?
		""", (class_id, date, time))
		return c.fetchone()[0] > 0


def fetch_students_with_teachers_for_class(class_id):
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


def has_weekly_time_conflict(student_id, class_day, session_time, exclude_session_id=None):
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


def has_teacher_weekly_time_conflict(class_id, session_time, exclude_session_id=None):
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


def get_session_by_id(session_id):
	with get_connection() as conn:
		c = conn.cursor()
		c.execute("""
			SELECT student_id, class_id, term_id
			FROM sessions
			WHERE id = ?
		""", (session_id,))
		return c.fetchone()

def delete_session(session_id):
	from data.payments_repo import delete_term_if_no_payments
	with get_connection() as conn:
		# اطلاعات جلسه را ابتدا بگیر
		c = conn.cursor()
		c.execute("SELECT student_id, class_id, term_id FROM sessions WHERE id= ?", (session_id,))
		row = c.fetchone()
		if not row:
			return
		student_id, class_id, term_id = row

		# حذف جلسه
		conn.execute("DELETE FROM sessions WHERE id= ?", (session_id,))
		conn.commit()

	# اگر ترم هیچ پرداختی ندارد و هیچ جلسه‌ای دیگر ندارد، آن را حذف کن
	delete_term_if_no_payments(student_id, class_id, term_id)


def get_session_count_per_class():
	with get_connection() as conn:
		c = conn.cursor()
		c.execute("""
			SELECT class_id, COUNT(*)
			FROM sessions
			GROUP BY class_id
		""")
		return dict(c.fetchall())


def get_student_count_per_class():
	with get_connection() as conn:
		c = conn.cursor()
		c.execute("""
			SELECT class_id, COUNT(DISTINCT student_id)
			FROM sessions
			GROUP BY class_id
		""")
		return dict(c.fetchall())


def get_session_count_per_student():
	conn = get_connection()
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


def delete_sessions_for_term(term_id):
    """
    همه جلسات مربوط به term_id را (گذشته و آینده) حذف می‌کند.
    """
    with get_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE term_id = ?", (term_id,))
        conn.commit()


def update_session(session_id, class_id, student_id, term_id, date, time, duration=30):

    with get_connection() as conn:
        conn.execute("""
            UPDATE sessions
            SET class_id = ?, student_id = ?, term_id = ?, date = ?, time = ?, duration = ?, updated_at = datetime('now','localtime')
            WHERE id = ?
        """, (class_id, student_id, term_id, date, time, duration, session_id))
        conn.commit()
