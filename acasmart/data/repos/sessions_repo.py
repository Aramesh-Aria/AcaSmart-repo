import sqlite3
import logging
from acasmart.data.db import get_connection

logger = logging.getLogger(__name__)


def ensure_term_config(term_id: int):
	from acasmart.data.repos.profiles_repo import get_default_profile
	from acasmart.data.repos.settings_repo import get_setting
	from acasmart.data.repos.profiles_repo import set_term_config
	from acasmart.data.repos.profiles_repo import get_term_config
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


def fetch_enrollments_for_class(class_id, include_completed=False):
	"""Model-B: students enrolled in a class with their weekly schedule and progress.

	Returns rows: (term_id, student_id, student_name, start_date, start_time,
	lesson_duration, sessions_limit, held_count, end_date). held_count excludes canceled.
	By default only active enrollments (end_date IS NULL).
	"""
	with get_connection() as conn:
		c = conn.cursor()
		query = """
			SELECT st.id, st.student_id, s.name, st.start_date, st.start_time,
			       COALESCE(st.lesson_duration, 30), COALESCE(st.sessions_limit, 0),
			       (SELECT COUNT(*) FROM attendance a WHERE a.term_id = st.id AND a.status != 'canceled'),
			       st.end_date
			FROM student_terms st
			JOIN students s ON s.id = st.student_id
			WHERE st.class_id = ?
		"""
		params = [class_id]
		if not include_completed:
			query += " AND st.end_date IS NULL"
		query += " ORDER BY st.start_time, s.name COLLATE NOCASE"
		c.execute(query, params)
		return c.fetchall()


def enroll_student(class_id, student_id, start_date, start_time,
				   sessions_limit=None, tuition_fee=None,
				   currency_unit=None, profile_id=None, lesson_duration=None):
	"""Model-B enrollment: create (or return) the student's term for this class — no session row.

	The weekly lessons are computed from the term's schedule; there is nothing else to persist.
	Returns the term_id, or None if blocked (schedule conflict, or an active term already exists).
	"""
	from acasmart.data.repos.terms_repo import insert_student_term_if_not_exists
	return insert_student_term_if_not_exists(
		student_id, class_id, start_date, start_time,
		sessions_limit=sessions_limit, tuition_fee=tuition_fee,
		currency_unit=currency_unit, profile_id=profile_id, lesson_duration=lesson_duration,
	)


def add_session(class_id, student_id, date, time,
				term_sessions_limit=None, term_tuition_fee=None,
				term_currency_unit=None, term_profile_id=None):
	from acasmart.data.repos.terms_repo import insert_student_term_if_not_exists
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


def fetch_scheduled_students_for_class_on_date(class_id, selected_date, include_completed=False):
	"""Model-B: students whose weekly schedule lands a lesson in this class on selected_date.

	Computed from student_terms (no sessions table). A term's student appears when the date is
	a weekly occurrence (start_date + 7·n) and the term still has room (held < limit), OR when an
	attendance record already exists for that date (so recorded/makeup dates stay editable).
	With include_completed=True, completed terms are included too (for editing past dates).
	Returns rows shaped like fetch_students_sessions_for_class_on_date: (sid, name, teacher, start_time, term_id).
	"""
	from acasmart.core.schedule import is_weekly_occurrence
	with get_connection() as conn:
		c = conn.cursor()
		c.execute("""
			SELECT st.id, st.student_id, s.name, t.name, st.start_time, st.start_date,
			       st.end_date, COALESCE(st.sessions_limit, 0)
			FROM student_terms st
			JOIN students s ON s.id = st.student_id
			JOIN classes c2 ON st.class_id = c2.id
			JOIN teachers t ON c2.teacher_id = t.id
			WHERE st.class_id = ? AND st.start_date <= ?
		""", (class_id, selected_date))
		rows = c.fetchall()

		result = []
		for term_id, sid, sname, tname, start_time, start_date, end_date, limit in rows:
			if end_date is not None and not include_completed:
				continue
			c.execute("""
				SELECT
					SUM(CASE WHEN status != 'canceled' THEN 1 ELSE 0 END),
					SUM(CASE WHEN date = ? THEN 1 ELSE 0 END)
				FROM attendance WHERE term_id = ?
			""", (selected_date, term_id))
			hrow = c.fetchone()
			held = hrow[0] or 0
			has_record = (hrow[1] or 0) > 0
			is_occ = is_weekly_occurrence(start_date, selected_date) and held < int(limit or 0)
			if has_record or is_occ:
				result.append((sid, sname, tname, start_time, term_id))

		result.sort(key=lambda r: (str(r[3]), str(r[1])))
		return result


def fetch_term_students_for_class_on_date(class_id, selected_date, include_completed=False):
	"""هنرجویانِ یک کلاس در یک تاریخ، بر مبنای ترم (نه جلسه) — برای دیدن/ویرایشِ ترم‌های تکمیل‌شده.

	اگر include_completed=False فقط ترم‌های فعال (end_date IS NULL)؛ در غیر این صورت هر ترمی که
	بازه‌اش شاملِ این تاریخ است (شاملِ تکمیل‌شده‌ها). خروجی هم‌شکلِ
	fetch_students_sessions_for_class_on_date است: (sid, name, teacher, time, term_id).
	"""
	with get_connection() as conn:
		c = conn.cursor()
		query = """
			SELECT s.id, s.name, t.name, st.start_time, st.id
			FROM student_terms st
			JOIN students s ON s.id = st.student_id
			JOIN classes c2 ON st.class_id = c2.id
			JOIN teachers t ON c2.teacher_id = t.id
			WHERE st.class_id = ?
			  AND st.start_date <= ?
		"""
		params = [class_id, selected_date]
		if include_completed:
			query += " AND (st.end_date IS NULL OR st.end_date >= ?)"
			params.append(selected_date)
		else:
			query += " AND st.end_date IS NULL"
		query += " ORDER BY st.start_time, s.name COLLATE NOCASE"
		c.execute(query, params)
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


def _time_to_minutes(t):
	"""تبدیل "HH:mm" (با ارقام فارسی یا انگلیسی) به دقیقه از نیمه‌شب؛ None اگر نامعتبر."""
	if t is None:
		return None
	t = str(t).strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
	try:
		hh, mm = t.split(":")
		return int(hh) * 60 + int(mm)
	except (ValueError, AttributeError):
		return None


def _intervals_overlap(start1, dur1, start2, dur2):
	"""آیا دو بازهٔ [start, start+dur) هم‌پوشانی دارند؟"""
	if start1 is None or start2 is None:
		return False
	return start1 < (start2 + dur2) and start2 < (start1 + dur1)


def has_student_schedule_conflict(student_id, class_id, start_time, new_duration=30, exclude_term_id=None):
	"""Model-B: does the student already have an active term whose weekly slot overlaps this one?

	Computed from student_terms (no sessions): same weekday (class.day) AND interval overlap on
	start_time/lesson_duration. exclude_term_id skips a term being edited.
	"""
	new_start = _time_to_minutes(start_time)
	if new_start is None:
		return False
	with get_connection() as conn:
		c = conn.cursor()
		row = c.execute("SELECT day FROM classes WHERE id = ?", (class_id,)).fetchone()
		if not row:
			return False
		class_day = row[0]
		query = """
			SELECT cl.day, st.start_time, COALESCE(st.lesson_duration, 30)
			FROM student_terms st JOIN classes cl ON cl.id = st.class_id
			WHERE st.student_id = ? AND st.end_date IS NULL
		"""
		params = [student_id]
		if exclude_term_id:
			query += " AND st.id != ?"
			params.append(exclude_term_id)
		c.execute(query, params)
		for day, stime, dur in c.fetchall():
			if day == class_day and _intervals_overlap(new_start, new_duration, _time_to_minutes(stime), int(dur or 30)):
				return True
	return False


def has_teacher_schedule_conflict(class_id, start_time, new_duration=30, exclude_term_id=None):
	"""Model-B: does the class's teacher already have an active term whose weekly slot overlaps this one?"""
	new_start = _time_to_minutes(start_time)
	if new_start is None:
		return False
	with get_connection() as conn:
		c = conn.cursor()
		row = c.execute("SELECT teacher_id, day FROM classes WHERE id = ?", (class_id,)).fetchone()
		if not row:
			return False
		teacher_id, class_day = row
		query = """
			SELECT cl.day, st.start_time, COALESCE(st.lesson_duration, 30)
			FROM student_terms st JOIN classes cl ON cl.id = st.class_id
			WHERE cl.teacher_id = ? AND st.end_date IS NULL
		"""
		params = [teacher_id]
		if exclude_term_id:
			query += " AND st.id != ?"
			params.append(exclude_term_id)
		c.execute(query, params)
		for day, stime, dur in c.fetchall():
			if day == class_day and _intervals_overlap(new_start, new_duration, _time_to_minutes(stime), int(dur or 30)):
				return True
	return False


def has_weekly_time_conflict(student_id, class_day, session_time, exclude_session_id=None, new_duration=30):
	"""تداخل زمانی هنرجو در یک روز هفته، بر مبنای هم‌پوشانیِ بازه‌ای (با درنظرگرفتن مدت جلسه)،
	نه تطبیق دقیقِ رشتهٔ ساعت. مدت هر جلسهٔ موجود از lesson_duration ترم (یا duration جلسه) گرفته می‌شود."""
	new_start = _time_to_minutes(session_time)
	if new_start is None:
		return False
	with get_connection() as conn:
		c = conn.cursor()
		query = """
			SELECT s.time, COALESCE(st.lesson_duration, s.duration, 30) AS dur
			FROM sessions s
			JOIN classes c ON s.class_id = c.id
			LEFT JOIN student_terms st ON st.id = s.term_id
			WHERE s.student_id = ?
			  AND c.day = ?
		"""
		params = [student_id, class_day]
		if exclude_session_id:
			query += " AND s.id != ?"
			params.append(exclude_session_id)

		c.execute(query, params)
		for s_time, dur in c.fetchall():
			if _intervals_overlap(new_start, new_duration, _time_to_minutes(s_time), int(dur or 30)):
				return True
	return False


def has_teacher_weekly_time_conflict(class_id, session_time, exclude_session_id=None, new_duration=30):
	"""تداخل زمانی استاد در یک روز هفته، بر مبنای هم‌پوشانیِ بازه‌ای (با درنظرگرفتن مدت جلسه)."""
	new_start = _time_to_minutes(session_time)
	if new_start is None:
		return False
	with get_connection() as conn:
		c = conn.cursor()
		# روز هفته و استادِ کلاسِ جدید
		c.execute("SELECT teacher_id, day FROM classes WHERE id = ?", (class_id,))
		row = c.fetchone()
		if not row:
			return False
		teacher_id, weekday = row

		query = """
			SELECT s.time, COALESCE(st.lesson_duration, s.duration, 30) AS dur
			FROM sessions s
			JOIN classes c2 ON c2.id = s.class_id
			LEFT JOIN student_terms st ON st.id = s.term_id
			WHERE c2.teacher_id = ?
			  AND c2.day = ?
		"""
		params = [teacher_id, weekday]
		if exclude_session_id:
			query += " AND s.id != ?"
			params.append(exclude_session_id)

		c.execute(query, params)
		for s_time, dur in c.fetchall():
			if _intervals_overlap(new_start, new_duration, _time_to_minutes(s_time), int(dur or 30)):
				return True
	return False


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
	from acasmart.data.repos.payments_repo import delete_term_if_no_history
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

	# اگر ترم هیچ سابقه‌ای (پرداخت یا حضور و غیاب) ندارد، آن را حذف کن
	delete_term_if_no_history(student_id, class_id, term_id)


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
