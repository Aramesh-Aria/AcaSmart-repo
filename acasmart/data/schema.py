import logging
from acasmart.data.db import get_connection
from acasmart.data.migrations import (
	run_all_migrations,
)

logger = logging.getLogger(__name__)


def create_tables():
	"""Create all tables with FKs, UNIQUE constraints, indexes, and audit columns."""
	with get_connection() as conn:
		c = conn.cursor()

		# Users table
		c.execute('''
			CREATE TABLE IF NOT EXISTS users (
			  id INTEGER PRIMARY KEY AUTOINCREMENT,
			  mobile TEXT UNIQUE NOT NULL,
			  password TEXT NOT NULL
			);
		''')
		# Teachers table
		c.execute("""
			CREATE TABLE IF NOT EXISTS teachers (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				name TEXT NOT NULL,
				national_code TEXT UNIQUE NOT NULL,
				teaching_card_number TEXT,
				gender TEXT,
				phone TEXT,
				birth_date TEXT,
				card_number TEXT,
				iban TEXT,
				created_at TEXT DEFAULT (datetime('now','localtime')),
				updated_at TEXT DEFAULT (datetime('now','localtime'))
			);
		""")
		# teachers instruments table
		c.execute("""CREATE TABLE IF NOT EXISTS teacher_instruments (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				teacher_id INTEGER NOT NULL,
				instrument TEXT NOT NULL,
				FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
				UNIQUE(teacher_id, instrument)
				);  
		""")
		# Students table
		c.execute("""CREATE TABLE IF NOT EXISTS students (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				name TEXT NOT NULL,
				birth_date TEXT NOT NULL,
				gender TEXT NOT NULL,
				national_code TEXT UNIQUE NOT NULL,
				phone TEXT,
				father_name TEXT,
				created_at TEXT DEFAULT (datetime('now','localtime')),
				updated_at TEXT DEFAULT (datetime('now','localtime'))
			);

		""")

		# Classes table
		c.execute("""
			CREATE TABLE IF NOT EXISTS classes (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				name TEXT NOT NULL,
				teacher_id INTEGER NOT NULL,
				day TEXT NOT NULL,
				start_time TEXT NOT NULL,
				end_time TEXT NOT NULL,
				room TEXT,
				instrument TEXT,
				created_at TEXT DEFAULT (datetime('now','localtime')),
				updated_at TEXT DEFAULT (datetime('now','localtime')),
				FOREIGN KEY(teacher_id)
				  REFERENCES teachers(id)
				  ON DELETE CASCADE
				  ON UPDATE CASCADE,
				UNIQUE(teacher_id, day, start_time, end_time, room)
			);
		""")

		# Sessions table
		c.execute("""
			CREATE TABLE IF NOT EXISTS sessions (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				class_id INTEGER NOT NULL,
				student_id INTEGER NOT NULL,
				term_id INTEGER,
				date TEXT NOT NULL,
				time TEXT NOT NULL,
				duration INTEGER DEFAULT 30,
				created_at TEXT DEFAULT (datetime('now','localtime')),
				updated_at TEXT DEFAULT (datetime('now','localtime')),
				FOREIGN KEY(class_id)
					REFERENCES classes(id)
					ON DELETE CASCADE
					ON UPDATE CASCADE,
				FOREIGN KEY(student_id)
					REFERENCES students(id)
					ON DELETE CASCADE
					ON UPDATE CASCADE,
				FOREIGN KEY(term_id)
					REFERENCES student_terms(id)
					ON DELETE CASCADE
					ON UPDATE CASCADE,
				UNIQUE(class_id, student_id, date, time)
			);
		""")

		# تضمین وجود term_id در sessions (اگر از قبل وجود داشت)
		c.execute("PRAGMA table_info(sessions)")
		cols = [row[1] for row in c.fetchall()]
		if "term_id" not in cols:
			c.execute("ALTER TABLE sessions ADD COLUMN term_id INTEGER")

		# student_terms table (Phase 2 will rebuild this cleanly)
		c.execute("""
			CREATE TABLE IF NOT EXISTS student_terms (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				student_id INTEGER NOT NULL,
				class_id INTEGER NOT NULL,
				start_date TEXT NOT NULL,
				end_date TEXT,
				start_time TEXT,
				sessions_limit INTEGER,
				tuition_fee INTEGER,
				currency_unit TEXT,
				profile_id INTEGER,
				created_at TEXT DEFAULT (datetime('now','localtime')),
				updated_at TEXT DEFAULT (datetime('now','localtime')),
				FOREIGN KEY(student_id)
					REFERENCES students(id)
					ON DELETE CASCADE
					ON UPDATE CASCADE,
				FOREIGN KEY(class_id)
					REFERENCES classes(id)
					ON DELETE CASCADE
					ON UPDATE CASCADE,
				FOREIGN KEY(profile_id)
					REFERENCES pricing_profiles(id)
					ON DELETE SET NULL ON UPDATE CASCADE
			);
		""")

		# تضمین وجود ستون‌های جدید در student_terms (اگر از قبل وجود داشت)
		c.execute("PRAGMA table_info(student_terms)")
		cols = [row[1] for row in c.fetchall()]
		if "sessions_limit" not in cols:
			c.execute("ALTER TABLE student_terms ADD COLUMN sessions_limit INTEGER")
		if "tuition_fee" not in cols:
			c.execute("ALTER TABLE student_terms ADD COLUMN tuition_fee INTEGER")
		if "currency_unit" not in cols:
			c.execute("ALTER TABLE student_terms ADD COLUMN currency_unit TEXT")
		if "profile_id" not in cols:
			c.execute("ALTER TABLE student_terms ADD COLUMN profile_id INTEGER")
		if "start_time" not in cols:
			c.execute("ALTER TABLE student_terms ADD COLUMN start_time TEXT")

		# profiles table
		c.execute("""
			CREATE TABLE IF NOT EXISTS pricing_profiles (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				name TEXT UNIQUE NOT NULL,
				sessions_limit INTEGER NOT NULL,
				tuition_fee INTEGER NOT NULL,
				currency_unit TEXT DEFAULT 'toman',
				is_default INTEGER DEFAULT 0,
				created_at TEXT DEFAULT (datetime('now','localtime')),
				updated_at TEXT DEFAULT (datetime('now','localtime'))
			);
		""")

		# بک‌فیل مقادیر خالی
		from acasmart.data.repos.settings_repo import get_setting  # lazy import to avoid circular
		default_fee = int(get_setting("term_fee", get_setting("term_tuition", 6000000)))
		default_sessions = int(get_setting("term_session_count", 12))
		default_unit = get_setting("currency_unit", "toman")
		c.execute("""
			UPDATE student_terms
			SET sessions_limit = COALESCE(sessions_limit, ?),
				tuition_fee    = COALESCE(tuition_fee,    ?),
				currency_unit  = COALESCE(currency_unit,  ?)
			WHERE sessions_limit IS NULL OR tuition_fee IS NULL OR currency_unit IS NULL
		""", (default_sessions, default_fee, default_unit))

		# Payments table
		c.execute("""
			CREATE TABLE IF NOT EXISTS payments (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				student_id INTEGER NOT NULL,
				class_id INTEGER NOT NULL,
				term_id INTEGER,
				amount INTEGER NOT NULL,
				payment_date TEXT NOT NULL,
				payment_type TEXT DEFAULT 'tuition',  -- 'tuition' or 'extra'
				description TEXT,
				created_at TEXT DEFAULT (datetime('now','localtime')),
				updated_at TEXT DEFAULT (datetime('now','localtime')),
				FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE ON UPDATE CASCADE,
				FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE ON UPDATE CASCADE,
				FOREIGN KEY(term_id) REFERENCES student_terms(id) ON DELETE CASCADE ON UPDATE CASCADE
			);
		""")

		# تضمین وجود term_id در payments (اگر از قبل وجود داشت)
		c.execute("PRAGMA table_info(payments)")
		cols = [row[1] for row in c.fetchall()]
		if "term_id" not in cols:
			c.execute("ALTER TABLE payments ADD COLUMN term_id INTEGER")

		# Settings table
		c.execute("""
			CREATE TABLE IF NOT EXISTS settings (
				key TEXT PRIMARY KEY,
				value TEXT NOT NULL
			);
		""")

		# Attendance table
		c.execute("""
			CREATE TABLE IF NOT EXISTS attendance (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			student_id INTEGER NOT NULL,
			class_id INTEGER NOT NULL,
			term_id INTEGER NOT NULL,
			date TEXT NOT NULL,
			is_present INTEGER NOT NULL DEFAULT 1,
			created_at TEXT DEFAULT (datetime('now','localtime')),
			updated_at TEXT DEFAULT (datetime('now','localtime')),
			FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE ON UPDATE CASCADE,
			FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE ON UPDATE CASCADE,
			FOREIGN KEY(term_id) REFERENCES student_terms(id) ON DELETE CASCADE ON UPDATE CASCADE,
			UNIQUE(student_id, class_id, term_id, date)
		);
		""")

		# تضمین وجود term_id در attendance (اگر از قبل وجود داشت)
		c.execute("PRAGMA table_info(attendance)")
		cols = [row[1] for row in c.fetchall()]
		if "term_id" not in cols:
			c.execute("ALTER TABLE attendance ADD COLUMN term_id INTEGER")
		if "date" not in cols:
			c.execute("ALTER TABLE attendance ADD COLUMN date TEXT")

		# Table of registered terms for which the end-of-term message has already been displayed.
		c.execute("""
			CREATE TABLE IF NOT EXISTS notified_terms (
				term_id INTEGER PRIMARY KEY,
				student_id INTEGER NOT NULL,
				class_id INTEGER NOT NULL,
				FOREIGN KEY(term_id) REFERENCES student_terms(id) ON DELETE CASCADE,
				FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
				FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE
			);
		""")
		# Table of recorded messages sent as reminders for term renewal 
		c.execute("""
			CREATE TABLE IF NOT EXISTS sms_notifications (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				student_id INTEGER NOT NULL,
				term_id INTEGER NOT NULL,
				sent_at TEXT DEFAULT (datetime('now','localtime')),
				FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
				FOREIGN KEY(term_id) REFERENCES student_terms(id) ON DELETE CASCADE,
				UNIQUE(student_id, term_id)
			);
		""")
		
		# Ensure additional columns exist in notified_terms
		c.execute("PRAGMA table_info(notified_terms)")
		cols = [row[1] for row in c.fetchall()]
		if "session_date" not in cols:
			c.execute("ALTER TABLE notified_terms ADD COLUMN session_date TEXT")
		if "session_time" not in cols:
			c.execute("ALTER TABLE notified_terms ADD COLUMN session_time TEXT")

		# Indexes for faster lookups
		c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_student_id ON sessions(student_id);")
		c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_class_id ON sessions(class_id);")
		c.execute("CREATE INDEX IF NOT EXISTS idx_classes_teacher_id ON classes(teacher_id);")
		c.execute("CREATE INDEX IF NOT EXISTS idx_classes_day ON classes(day);")
		c.execute("CREATE INDEX IF NOT EXISTS idx_payments_student_id ON payments(student_id);")
		c.execute("CREATE INDEX IF NOT EXISTS idx_payments_class_id ON payments(class_id);")
		c.execute("CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(payment_date);")
		
		# Check if term_id and date columns exist before creating indexes
		c.execute("PRAGMA table_info(attendance)")
		att_cols = [row[1] for row in c.fetchall()]
		if "term_id" in att_cols:
			c.execute("CREATE INDEX IF NOT EXISTS idx_attendance_term_id ON attendance(term_id);")
		
		c.execute("PRAGMA table_info(payments)")
		pay_cols = [row[1] for row in c.fetchall()]
		if "term_id" in pay_cols:
			c.execute("CREATE INDEX IF NOT EXISTS idx_payments_term_id   ON payments(term_id);")
			
		c.execute("CREATE INDEX IF NOT EXISTS idx_terms_student_class ON student_terms(student_id, class_id);")
		
		# Composite indexes (idempotent)
		c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_class_date_time ON sessions(class_id, date, time);")
		
		if "term_id" in att_cols and "date" in att_cols:
			c.execute("CREATE INDEX IF NOT EXISTS idx_attendance_term_date     ON attendance(term_id, date);")
		
		if "term_id" in pay_cols:
			c.execute("CREATE INDEX IF NOT EXISTS idx_payments_term_date       ON payments(term_id, payment_date);")
		
		# Initial settings
		c.execute("SELECT COUNT(*) FROM settings")
		if c.fetchone()[0] == 0:
			c.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("currency_unit", "toman"))
			c.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("sms_enabled", "فعال"))
			c.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("term_session_count", "12"))
			c.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("term_tuition", "6000000"))

		conn.commit()

	run_all_migrations()  # اجرای مهاجرت‌ها بعد از ساخت جداول
