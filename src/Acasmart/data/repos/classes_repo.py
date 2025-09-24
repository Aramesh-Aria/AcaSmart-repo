import logging
from Acasmart.data.db import get_connection

logger = logging.getLogger(__name__)


def create_class(name, teacher_id, day, start_time, end_time, room, instrument):
	with get_connection() as conn:
		conn.execute(
			"INSERT INTO classes (name, teacher_id, day, start_time, end_time, room, instrument) VALUES (?, ?, ?, ?, ?, ?, ?)",
			(name, teacher_id, day, start_time, end_time, room, instrument),
		)
		conn.commit()


def fetch_classes():
	with get_connection() as conn:
		c = conn.cursor()
		c.execute(
			"""
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
			"""
		)
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
		c.execute(
			"""
			SELECT COUNT(*) FROM classes
			WHERE teacher_id = ? AND day = ? AND start_time = ? AND end_time = ? AND room = ?
			""",
			(teacher_id, day, start_time, end_time, room),
		)
		return c.fetchone()[0] > 0


def get_class_by_id(class_id):
	with get_connection() as conn:
		c = conn.cursor()
		c.execute(
			"""
			SELECT name, teacher_id, instrument, day, start_time, end_time, room
			FROM classes WHERE id = ?
			""",
			(class_id,),
		)
		return c.fetchone()


def update_class_by_id(class_id, name, teacher_id, day, start_time, end_time, room, instrument):
	with get_connection() as conn:
		conn.execute(
			"""
			UPDATE classes
			SET name=?, teacher_id=?, instrument=?, day=?, start_time=?, end_time=?, room=?, updated_at=datetime('now','localtime')
			WHERE id=?
			""",
			(name, teacher_id, instrument, day, start_time, end_time, room, class_id),
		)
		conn.commit()


def fetch_classes_on_weekday(day_name):
	with get_connection() as conn:
		c = conn.cursor()
		c.execute(
			"""
			SELECT c.id, c.name, t.name, c.instrument, c.day, c.start_time, c.end_time, c.room
			FROM classes c
			JOIN teachers t ON c.teacher_id = t.id
			WHERE c.day = ?
			ORDER BY c.start_time
			""",
			(day_name,),
		)
		return c.fetchall()


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


def does_teacher_have_time_conflict(teacher_id, day, start_time, end_time, exclude_class_id=None):
	with get_connection() as conn:
		c = conn.cursor()
		query = (
			"""
			SELECT COUNT(*) FROM classes
			WHERE teacher_id = ?
			  AND day = ?
			  AND (
			      (start_time < ? AND end_time > ?)
			      OR (start_time >= ? AND start_time < ?)
			  )
			"""
		)
		params = [teacher_id, day, end_time, start_time, start_time, end_time]
		if exclude_class_id:
			query += " AND id != ?"
			params.append(exclude_class_id)
		c.execute(query, params)
		return c.fetchone()[0] > 0

def get_day_and_time_for_class(class_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT day, start_time FROM classes WHERE id = ?", (class_id,))
        return c.fetchone() or (None, None)
    