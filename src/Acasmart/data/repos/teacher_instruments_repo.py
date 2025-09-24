from Acasmart.data.db import get_connection


def add_instrument_to_teacher(teacher_id, instrument):
	with get_connection() as conn:
		conn.execute(
			"""
			INSERT OR IGNORE INTO teacher_instruments (teacher_id, instrument)
			VALUES (?, ?)
			""",
			(teacher_id, instrument),
		)
		conn.commit()


def remove_instrument_from_teacher(teacher_id, instrument):
	with get_connection() as conn:
		conn.execute(
			"""
			DELETE FROM teacher_instruments
			WHERE teacher_id = ? AND instrument = ?
			""",
			(teacher_id, instrument),
		)
		conn.commit()


def get_instruments_for_teacher(teacher_id):
	with get_connection() as conn:
		c = conn.cursor()
		c.execute(
			"""
			SELECT instrument FROM teacher_instruments
			WHERE teacher_id = ?
			""",
			(teacher_id,),
		)
		return [row[0] for row in c.fetchall()]

def fetch_teachers_with_instruments():
	with get_connection() as conn:
		c = conn.cursor()
		c.execute(
			"""
			SELECT t.id, t.name, GROUP_CONCAT(ti.instrument, '/') as instruments
			FROM teachers t
			LEFT JOIN teacher_instruments ti ON t.id = ti.teacher_id
			GROUP BY t.id
			"""
		)
		return c.fetchall()
