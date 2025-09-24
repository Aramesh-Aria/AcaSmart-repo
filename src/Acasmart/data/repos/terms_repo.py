import logging
from Acasmart.data.db import get_connection

logger = logging.getLogger(__name__)


def insert_student_term_if_not_exists(
	student_id, class_id, start_date, start_time,
	sessions_limit=None, tuition_fee=None, currency_unit=None, profile_id=None
):
	from Acasmart.data.repos.settings_repo import get_setting  # local to avoid cycles
	from Acasmart.data.repos.sessions_repo import has_teacher_weekly_time_conflict  # avoid cycles
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


def delete_student_term_by_id(term_id):
	with get_connection() as conn:
		conn.execute("DELETE FROM student_terms WHERE id = ?", (term_id,))
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


def get_term_id_by_student_and_class(student_id, class_id):
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
	with get_connection() as conn:
		c = conn.cursor()
		c.execute("""
			SELECT id, start_date, end_date, created_at
			FROM student_terms
			WHERE student_id = ? AND class_id = ?
			ORDER BY start_date DESC
		""", (student_id, class_id))
		return c.fetchall()


def recalc_term_end_by_id(term_id: int):
	with get_connection() as conn:
		c = conn.cursor()
		c.execute("""
			SELECT MAX(date)
			FROM attendance
			WHERE term_id = ?
		""", (term_id,))
		row = c.fetchone()
		if not row or not row[0]:
			return None
		last_date = row[0]
		c.execute("""
			UPDATE student_terms
			SET end_date = ?, updated_at = datetime('now','localtime')
			WHERE id = ?
		""", (last_date, term_id))
		conn.commit()
		return last_date


def get_term_dates(term_id):
	with get_connection() as conn:
		c = conn.cursor()
		c.execute("""
			SELECT start_date, end_date FROM student_terms
			WHERE id = ?
		""", (term_id,))
		return c.fetchone()


def get_term_tuition_by_id(term_id: int):
	with get_connection() as conn:
		c = conn.cursor()
		c.execute("SELECT tuition_fee FROM student_terms WHERE id= ?", (term_id,))
		row = c.fetchone()
		return int(row[0]) if row and row[0] is not None else None


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


def check_and_set_term_end_by_id(term_id, student_id, class_id, session_date):
	from Acasmart.data.repos.settings_repo import get_setting  # local to avoid cycles
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


def get_all_expired_terms():
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


def get_finished_terms_with_future_sessions():
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

def count_attendance_for_term(term_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*) FROM attendance
            WHERE term_id = ?
        """, (term_id,))
        return c.fetchone()[0]