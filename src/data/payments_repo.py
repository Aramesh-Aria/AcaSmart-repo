import logging
from data.db import get_connection

logger = logging.getLogger(__name__)


def insert_payment(student_id, class_id, term_id, amount, payment_date, payment_type='tuition', description=None):
	"""
	ثبت پرداخت با ترم و نوع پرداخت.
	"""
	if payment_type not in {"tuition", "extra"}:
		raise ValueError("invalid payment_type")
	if amount < 0:
		raise ValueError("amount must be non-negative")
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


def get_terms_for_payment_management(student_id, class_id):
	from data.settings_repo import get_setting
	with get_connection() as conn:
		c = conn.cursor()
		c.execute(
			"""
			SELECT 
				t.id as term_id,
				t.start_date,
				t.end_date,
				t.created_at,
				COALESCE(SUM(CASE WHEN p.payment_type='tuition' THEN p.amount ELSE 0 END), 0) as paid_tuition,
				COALESCE(SUM(CASE WHEN p.payment_type='extra' THEN p.amount ELSE 0 END), 0) as paid_extra,
				COUNT(p.id) as payment_count,
				COALESCE(t.tuition_fee, 0) as term_fee
			FROM student_terms t
			LEFT JOIN payments p ON t.id = p.term_id
			WHERE t.student_id = ? AND t.class_id = ?
			GROUP BY t.id, t.start_date, t.end_date, t.created_at, t.tuition_fee
			ORDER BY t.start_date DESC
			""",
			(student_id, class_id)
		)
		rows = c.fetchall()

	result = []
	for (term_id, start_date, end_date, created_at, paid_tuition, paid_extra, payment_count, term_fee) in rows:
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
		c.execute(
			"""
			SELECT amount, payment_date, description
			FROM payments
			WHERE term_id = ? AND payment_type = 'extra'
			ORDER BY payment_date
			""",
			(term_id,)
		)
		return c.fetchall()


def get_payment_by_id(payment_id):
	"""
	دریافت جزئیات یک پرداخت بر اساس ID.
	خروجی: dict شامل id, student_id, class_id, term_id, amount, payment_date (شمسی "YYYY-MM-DD"),
	        payment_type ('tuition'/'extra'), description
	"""
	with get_connection() as conn:
		c = conn.cursor()
		c.execute(
			"""
			SELECT id, student_id, class_id, term_id, amount, payment_date, payment_type, description
			FROM payments
			WHERE id = ?
			""",
			(payment_id,)
		)
		row = c.fetchone()
		if not row:
			return None
		return {
			"id": row[0],
			"student_id": row[1],
			"class_id": row[2],
			"term_id": row[3],
			"amount": row[4],
			"payment_date": row[5],
			"payment_type": row[6],
			"description": row[7],
		}


def update_payment_by_id(payment_id, amount, date, payment_type, description):
	# Soft validations
	if payment_type not in {"tuition", "extra"}:
		raise ValueError("invalid payment_type")
	if amount < 0:
		raise ValueError("amount must be non-negative")
	with get_connection() as conn:
		conn.execute(
			"""
			UPDATE payments
			SET amount = ?, payment_date = ?, payment_type = ?, description = ?, updated_at = datetime('now','localtime')
			WHERE id = ?
			""",
			(amount, date, payment_type, description, payment_id),
		)
		conn.commit()


def delete_term_if_no_payments(student_id, class_id, term_id):
	conn = get_connection()
	c = conn.cursor()
	c.execute(
		"""
		SELECT COUNT(*) FROM payments
		WHERE student_id = ? AND class_id = ? AND term_id = ?
		""",
		(student_id, class_id, term_id)
	)
	has_payments = c.fetchone()[0] > 0

	if has_payments:
		conn.close()
		return False

	# حذف ترم و تمام جلسات آن ترم
	c.execute(
		"""
		DELETE FROM sessions WHERE student_id = ? AND class_id = ? AND term_id = ?
		""",
		(student_id, class_id, term_id)
	)

	c.execute(
		"""
		DELETE FROM student_terms WHERE student_id = ? AND class_id = ? AND id = ?
		""",
		(student_id, class_id, term_id)
	)

	conn.commit()
	conn.close()
	return True
