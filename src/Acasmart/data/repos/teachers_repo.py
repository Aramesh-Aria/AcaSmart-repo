import logging
from Acasmart.data.db import get_connection

logger = logging.getLogger(__name__)


def fetch_teachers():
	with get_connection() as conn:
		c = conn.cursor()
		c.execute("SELECT id, name FROM teachers")
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
			(name, national_code, teaching_card_number, gender, phone, birth_date, card_number, iban),
		)
		conn.commit()


def delete_teacher_by_id(teacher_id):
	with get_connection() as conn:
		conn.execute("DELETE FROM teachers WHERE id=?", (teacher_id,))
		conn.commit()


def is_teacher_assigned_to_students(teacher_id):
	conn = get_connection()
	c = conn.cursor()
	c.execute("SELECT id FROM classes WHERE teacher_id = ?", (teacher_id,))
	class_ids = [row[0] for row in c.fetchall()]
	if not class_ids:
		conn.close()
		return False
	placeholders = ",".join("?" * len(class_ids))
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
			(name, national_code, teaching_card_number, gender, phone, birth_date, card_number, iban, teacher_id),
		)
		conn.commit()


def get_teacher_by_id(teacher_id):
	with get_connection() as conn:
		c = conn.cursor()
		c.execute(
			"""
			SELECT name, national_code, teaching_card_number, gender, phone, birth_date, card_number, iban
			FROM teachers
			WHERE id=?
			""",
			(teacher_id,),
		)
		return c.fetchone()


def get_teacher_id_by_national_code(national_code):
	with get_connection() as conn:
		c = conn.cursor()
		c.execute("SELECT id FROM teachers WHERE national_code = ?", (national_code,))
		row = c.fetchone()
		return row[0] if row else None
