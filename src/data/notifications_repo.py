import logging
from data.db import get_connection

logger = logging.getLogger(__name__)


def get_unnotified_expired_terms():
	"""
	لیست ترم‌هایی که end_date آنها ست شده ولی هنوز نوتیف نداده‌ایم.
	"""
	with get_connection() as conn:
		c = conn.cursor()
		c.execute("""
			SELECT 
				t.student_id,
				t.class_id,
				s.name,
				s.national_code,
				c.name,
				c.day,
				t.id      AS term_id,
				t.end_date   AS session_date,
				t.start_time AS session_time
			FROM student_terms t
			JOIN students s ON s.id = t.student_id
			JOIN classes c  ON c.id = t.class_id
			WHERE t.end_date IS NOT NULL
			  AND NOT EXISTS (
				  SELECT 1 
				  FROM notified_terms n 
				  WHERE n.term_id = t.id
			  )
		""")
		return c.fetchall()


def mark_terms_as_notified(term_info_list):
	"""
	term_info_list = list of (term_id, student_id, class_id, session_date, session_time)
	"""
	with get_connection() as conn:
		c = conn.cursor()
		c.executemany("""
			INSERT OR IGNORE INTO notified_terms (term_id, student_id, class_id, session_date, session_time)
			VALUES (?, ?, ?, ?, ?)
		""", term_info_list)
		conn.commit()


def has_renew_sms_been_sent(student_id, term_id):
	with get_connection() as conn:
		c = conn.cursor()
		c.execute("""
			SELECT COUNT(*) FROM sms_notifications
			WHERE student_id = ? AND term_id = ?
		""", (student_id, term_id))
		return c.fetchone()[0] > 0


def mark_renew_sms_sent(student_id, term_id):
	with get_connection() as conn:
		conn.execute("""
			INSERT OR IGNORE INTO sms_notifications (student_id, term_id)
			VALUES (?, ?)
		""", (student_id, term_id))
		conn.commit()
