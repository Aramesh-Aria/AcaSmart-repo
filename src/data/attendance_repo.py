import logging
from data.db import get_connection

logger = logging.getLogger(__name__)


def count_attendance(student_id, class_id):
	"""
	تعداد جلسات ثبت‌شده برای هنرجو در ترم فعال (end_date IS NULL).
	"""
	from data.terms_repo import get_term_id_by_student_and_class
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


def insert_attendance_with_date(student_id, class_id, term_id, date, is_present):
	"""
	ثبت حضور/غیاب برای تاریخ مشخص. اگر با این ثبت سقف پر شود،
	check_and_set_term_end_by_id همان روز را end_date می‌گذارد.
	مقدار True/False برمی‌گرداند که آیا end_date ست شد یا نه.
	"""
	from data.terms_repo import check_and_set_term_end_by_id
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
	from data.terms_repo import get_term_id_by_student_and_class
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


def count_present_attendance_for_term(term_id: int) -> int:
	with get_connection() as conn:
		c = conn.cursor()
		c.execute("SELECT COUNT(*) FROM attendance WHERE term_id = ? AND is_present = 1", (term_id,))
		row = c.fetchone()
		return int(row[0]) if row else 0
