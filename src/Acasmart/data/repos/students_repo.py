import logging
from Acasmart.data.db import get_connection

logger = logging.getLogger(__name__)


def insert_student(name, birth_date, gender, national_code, phone, father_name):
	conn = get_connection()
	c = conn.cursor()
	c.execute(
		"""
		INSERT INTO students (name, birth_date, gender, national_code, phone, father_name)
		VALUES (?, ?, ?, ?, ?, ?)
		""",
		(name, birth_date, gender, national_code, phone, father_name),
	)
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
			(student_id,),
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
			(name, birth_date, gender, national_code, phone, father_name, student_id),
		)
		conn.commit()


def delete_student_by_id(student_id):
	with get_connection() as conn:
		conn.execute("DELETE FROM students WHERE id=?", (student_id,))
		conn.commit()


def fetch_students():
	with get_connection() as conn:
		c = conn.cursor()
		c.execute(
			"""
			SELECT id, name, gender, birth_date, national_code 
			FROM students
			ORDER BY name COLLATE NOCASE
			"""
		)
		return c.fetchall()


def is_national_code_exists_for_other(table, national_code, current_id):
	with get_connection() as conn:
		c = conn.cursor()
		c.execute(
			f"""
			SELECT COUNT(*) FROM {table}
			WHERE national_code = ? AND id != ?
			""",
			(national_code, current_id),
		)
		return c.fetchone()[0] > 0


def get_student_contact(student_id):
	with get_connection() as conn:
		c = conn.cursor()
		c.execute("SELECT name, phone FROM students WHERE id = ?", (student_id,))
		row = c.fetchone()
		return row if row else (None, None)


def fetch_registered_classes_for_student(student_id):
	conn = get_connection()
	c = conn.cursor()
	c.execute(
		"""
		SELECT DISTINCT classes.id, classes.name, teachers.name, classes.instrument,
		       classes.day, classes.start_time, classes.end_time, classes.room
		FROM classes
		JOIN teachers ON classes.teacher_id = teachers.id
		JOIN student_terms ON classes.id = student_terms.class_id
		WHERE student_terms.student_id = ?
		ORDER BY classes.day
		""",
		(student_id,),
	)
	result = c.fetchall()
	conn.close()
	return result

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
