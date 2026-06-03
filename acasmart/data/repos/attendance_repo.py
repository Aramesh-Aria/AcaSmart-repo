import logging
from acasmart.data.db import get_connection

logger = logging.getLogger(__name__)


def count_attendance_by_term(student_id, class_id, term_id):
	"""
	تعداد جلسات ثبت‌شده (حاضر یا غایب) برای یک ترم.
	حالا با جوین به جلسات حساب می‌شود.
	"""
	with get_connection() as conn:
		c = conn.cursor()
		c.execute("""
			SELECT COUNT(a.id) 
			FROM attendance a
			JOIN sessions s ON a.session_id = s.id
			WHERE s.student_id = ? AND s.class_id = ? AND s.term_id = ?
		""", (student_id, class_id, term_id))
		return c.fetchone()[0]


def insert_attendance_for_session(session_id, is_present):
	"""
	ثبت حضور/غیاب برای یک جلسه خاص.
	اگر با این ثبت سقف ترم پر شود، ترم بسته می‌شود.
	"""
	from acasmart.data.repos.terms_repo import check_and_set_term_end_by_id
	
	with get_connection() as conn:
		# اطلاعات جلسه را بگیر برای بستن ترم
		c = conn.cursor()
		c.execute("SELECT student_id, class_id, term_id, date FROM sessions WHERE id = ?", (session_id,))
		row = c.fetchone()
		if not row:
			return False
		sid, cid, tid, date = row

		conn.execute(
			"""
			INSERT OR REPLACE INTO attendance (session_id, is_present)
			VALUES (?, ?)
			""",
			(session_id, is_present)
		)
		conn.commit()

	# بعد از ثبت، بررسی و در صورت لزوم بستن ترم
	ended = check_and_set_term_end_by_id(tid, sid, cid, date)
	return ended


def delete_attendance_for_session(session_id):
	"""حذف حضور/غیاب یک جلسه."""
	with get_connection() as conn:
		c = conn.cursor()
		c.execute("DELETE FROM attendance WHERE session_id = ?", (session_id,))
		conn.commit()
		return c.rowcount


def fetch_attendance_by_session(session_id):
	"""وضعیت حضور یک جلسه را برمی‌گرداند (None اگر ثبت نشده باشد)."""
	with get_connection() as conn:
		c = conn.cursor()
		c.execute("SELECT is_present FROM attendance WHERE session_id = ?", (session_id,))
		row = c.fetchone()
		if row is None:
			return None
		return bool(row[0])


def fetch_attendance_by_date(student_id, class_id, date_str, term_id=None):
	"""
	(Legacy support) وضعیت حضور در یک تاریخ خاص.
	حالا با جوین به جلسات کار می‌کند.
	"""
	from acasmart.data.repos.terms_repo import get_term_id_by_student_and_class
	if term_id is None:
		term_id = get_term_id_by_student_and_class(student_id, class_id)
	if not term_id:
		return None

	with get_connection() as conn:
		c = conn.cursor()
		c.execute("""
			SELECT a.is_present 
			FROM attendance a
			JOIN sessions s ON a.session_id = s.id
			WHERE s.student_id = ? AND s.class_id = ? AND s.term_id = ? AND s.date = ?
		""", (student_id, class_id, term_id, date_str))
		row = c.fetchone()
		if row is None:
			return None
		return bool(row[0])


def count_present_attendance_for_term(term_id: int) -> int:
	with get_connection() as conn:
		c = conn.cursor()
		c.execute("""
			SELECT COUNT(a.id) 
			FROM attendance a
			JOIN sessions s ON a.session_id = s.id
			WHERE s.term_id = ? AND a.is_present = 1
		""", (term_id,))
		row = c.fetchone()
		return int(row[0]) if row else 0

def count_attendance(student_id, class_id):
	"""
	تعداد کل جلسات ثبت‌شده برای ترم فعال فعلی.
	"""
	from acasmart.data.repos.terms_repo import get_term_id_by_student_and_class
	term_id = get_term_id_by_student_and_class(student_id, class_id)
	if not term_id:
		return 0
	return count_attendance_by_term(student_id, class_id, term_id)
