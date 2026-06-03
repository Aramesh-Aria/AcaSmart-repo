import logging
from acasmart.data.db import get_connection

logger = logging.getLogger(__name__)


def ensure_schema_version_table():
	"""Ensure the schema_version table exists."""
	with get_connection() as conn:
		conn.execute("""
			CREATE TABLE IF NOT EXISTS schema_version (
				version INTEGER PRIMARY KEY,
				applied_at TEXT DEFAULT (datetime('now','localtime'))
			);
		""")
		conn.commit()


def get_current_version():
	"""Get the current schema version."""
	ensure_schema_version_table()
	with get_connection() as conn:
		c = conn.cursor()
		c.execute("SELECT MAX(version) FROM schema_version")
		row = c.fetchone()
		return row[0] if row and row[0] is not None else 0


def apply_migration(version, migration_func):
	"""Apply a specific migration function and record the version."""
	current = get_current_version()
	if current >= version:
		return

	logger.info(f"🚀 Applying migration v{version}...")
	try:
		migration_func()
		with get_connection() as conn:
			conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
			conn.commit()
		logger.info(f"✅ Migration v{version} applied successfully.")
	except Exception as e:
		logger.error(f"❌ Failed to apply migration v{version}: {e}")
		raise


def migrate_attendance_unique_constraint():
	"""
	(Legacy Migration v1)
	Ensure attendance has UNIQUE(student_id, class_id, term_id, date).
	If not, rebuild table with correct constraint and migrate data safely.
	"""
	with get_connection() as conn:
		c = conn.cursor()
		# Check if already modernized by v2 (v2 rebuilds the whole table)
		c.execute("PRAGMA table_info(attendance)")
		cols = [row[1] for row in c.fetchall()]
		if "session_id" in cols:
			return

		# 1) وجود جدول
		c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='attendance';")
		row = c.fetchone()
		if not row:
			return  # هنوز جدولی نیست

		# 2) آیا همین حالا UNIQUE درست را داریم؟
		ddl = (row[0] or "")
		ddl_norm = "".join(ddl.split()).lower()  # حذف فاصله‌ها + حروف کوچک
		wanted = "unique(student_id,class_id,term_id,date)"
		if wanted in ddl_norm:
			logger.info("ℹ️ ساختار UNIQUE صحیح است؛ مهاجرت v1 لازم نیست.")
			return

		logger.info("🔄 اجرای مهاجرت UNIQUE (v1) برای جدول attendance...")

		# 3) بکاپ جدول
		c.execute("ALTER TABLE attendance RENAME TO attendance_old;")

		# 4) ساخت جدول جدید با UNIQUE صحیح
		c.execute("""
			CREATE TABLE attendance (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				student_id INTEGER NOT NULL,
				class_id   INTEGER NOT NULL,
				term_id    INTEGER NOT NULL,
				date       TEXT    NOT NULL,
				is_present INTEGER NOT NULL DEFAULT 1,
				created_at TEXT DEFAULT (datetime('now','localtime')),
				updated_at TEXT DEFAULT (datetime('now','localtime')),
				FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE ON UPDATE CASCADE,
				FOREIGN KEY(class_id)   REFERENCES classes(id)  ON DELETE CASCADE ON UPDATE CASCADE,
				FOREIGN KEY(term_id)    REFERENCES student_terms(id) ON DELETE CASCADE ON UPDATE CASCADE,
				UNIQUE(student_id, class_id, term_id, date)
			);
		""")

		# 5) انتقال داده‌ها:
		c.execute("""
			INSERT OR IGNORE INTO attendance
				(student_id, class_id, term_id, date, is_present, created_at, updated_at)
			SELECT
				student_id,
				class_id,
				term_id,
				date,
				MAX(COALESCE(is_present, 0))           AS is_present,
				MIN(COALESCE(created_at, '1900-01-01')) AS created_at,
				MAX(COALESCE(updated_at, '1900-01-01')) AS updated_at
			FROM attendance_old
			GROUP BY student_id, class_id, term_id, date;
		""")

		# 6) حذف بکاپ
		c.execute("DROP TABLE attendance_old;")

		# 7) ایندکس‌های مفید (idempotent)
		c.execute("CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id);")
		c.execute("CREATE INDEX IF NOT EXISTS idx_attendance_class   ON attendance(class_id);")
		c.execute("CREATE INDEX IF NOT EXISTS idx_attendance_term    ON attendance(term_id);")
		c.execute("CREATE INDEX IF NOT EXISTS idx_attendance_date    ON attendance(date);")

		conn.commit()


def migrate_v2_modernize_schema():
	"""
	Phase 2 Migration:
	1. Merge duplicate active terms (student_id, class_id).
	2. Ensure every attendance record has a session_id.
	3. Rebuild sessions, attendance, and payments with NOT NULL term_id and other constraints.
	4. Add partial unique index on student_terms.
	"""
	with get_connection() as conn:
		c = conn.cursor()
		c.execute("PRAGMA foreign_keys=OFF;")

		try:
			# --- 1) Merge duplicate active terms ---
			# We keep the one with the smallest ID (usually the first one created)
			c.execute("""
				SELECT student_id, class_id, MIN(id) as keep_id
				FROM student_terms
				WHERE end_date IS NULL
				GROUP BY student_id, class_id
				HAVING COUNT(*) > 1
			""")
			duplicates = c.fetchall()
			for sid, cid, keep_id in duplicates:
				logger.info(f"Merging duplicate terms for student={sid}, class={cid} -> keeping term={keep_id}")
				# Find all other active terms for this student/class
				c.execute("""
					SELECT id FROM student_terms 
					WHERE student_id=? AND class_id=? AND end_date IS NULL AND id != ?
				""", (sid, cid, keep_id))
				other_ids = [r[0] for r in c.fetchall()]
				
				for old_id in other_ids:
					# Move sessions, payments, attendance to the kept term
					c.execute("UPDATE sessions SET term_id = ? WHERE term_id = ?", (keep_id, old_id))
					c.execute("UPDATE payments SET term_id = ? WHERE term_id = ?", (keep_id, old_id))
					c.execute("UPDATE attendance SET term_id = ? WHERE term_id = ?", (keep_id, old_id))
					c.execute("UPDATE notified_terms SET term_id = ? WHERE term_id = ?", (keep_id, old_id))
					c.execute("UPDATE sms_notifications SET term_id = ? WHERE term_id = ?", (keep_id, old_id))
					# Delete the old term
					c.execute("DELETE FROM student_terms WHERE id = ?", (old_id,))

			# --- 2) Ensure every attendance has a session ---
			# In the old model, attendance was date-based. In the new model, it's session-based.
			# We find (student, class, term, date) in attendance that don't have a matching session.
			c.execute("""
				SELECT a.student_id, a.class_id, a.term_id, a.date, a.is_present, a.created_at
				FROM attendance a
				LEFT JOIN sessions s ON a.student_id = s.student_id 
				                    AND a.class_id = s.class_id 
				                    AND a.term_id = s.term_id 
				                    AND a.date = s.date
				WHERE s.id IS NULL
			""")
			orphans = c.fetchall()
			for sid, cid, tid, date, is_present, created_at in orphans:
				# Create a placeholder session. We'll use a dummy time if we don't know it.
				# Try to get time from other sessions in that class? Or just 00:00.
				c.execute("SELECT time FROM sessions WHERE class_id=? LIMIT 1", (cid,))
				row = c.fetchone()
				session_time = row[0] if row else "00:00"
				
				c.execute("""
					INSERT INTO sessions (class_id, student_id, term_id, date, time, created_at)
					VALUES (?, ?, ?, ?, ?, ?)
				""", (cid, sid, tid, date, session_time, created_at))
				logger.info(f"Created placeholder session for orphaned attendance: student={sid}, date={date}")

			# --- 3) Rebuild Tables ---

			# A) SESSIONS (Make term_id NOT NULL)
			c.execute("ALTER TABLE sessions RENAME TO sessions_old;")
			c.execute("""
				CREATE TABLE sessions (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					class_id INTEGER NOT NULL,
					student_id INTEGER NOT NULL,
					term_id INTEGER NOT NULL,
					date TEXT NOT NULL,
					time TEXT NOT NULL,
					duration INTEGER DEFAULT 30,
					created_at TEXT DEFAULT (datetime('now','localtime')),
					updated_at TEXT DEFAULT (datetime('now','localtime')),
					FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE ON UPDATE CASCADE,
					FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE ON UPDATE CASCADE,
					FOREIGN KEY(term_id) REFERENCES student_terms(id) ON DELETE CASCADE ON UPDATE CASCADE,
					UNIQUE(class_id, student_id, date, time)
				);
			""")
			c.execute("""
				INSERT INTO sessions (id, class_id, student_id, term_id, date, time, duration, created_at, updated_at)
				SELECT id, class_id, student_id, COALESCE(term_id, 0), date, time, duration, created_at, updated_at
				FROM sessions_old WHERE term_id IS NOT NULL;
			""")
			c.execute("DROP TABLE sessions_old;")

			# B) ATTENDANCE (Linked to session_id)
			c.execute("ALTER TABLE attendance RENAME TO attendance_old;")
			c.execute("""
				CREATE TABLE attendance (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					session_id INTEGER UNIQUE NOT NULL,
					is_present INTEGER NOT NULL DEFAULT 1,
					created_at TEXT DEFAULT (datetime('now','localtime')),
					updated_at TEXT DEFAULT (datetime('now','localtime')),
					FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE ON UPDATE CASCADE
				);
			""")
			# Link old attendance to sessions
			c.execute("""
				INSERT OR IGNORE INTO attendance (session_id, is_present, created_at, updated_at)
				SELECT s.id, a.is_present, a.created_at, a.updated_at
				FROM attendance_old a
				JOIN sessions s ON a.student_id = s.student_id 
				               AND a.class_id = s.class_id 
				               AND a.term_id = s.term_id 
				               AND a.date = s.date;
			""")
			c.execute("DROP TABLE attendance_old;")

			# C) PAYMENTS (Make term_id NOT NULL, add CHECKs)
			c.execute("ALTER TABLE payments RENAME TO payments_old;")
			c.execute("""
				CREATE TABLE payments (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					student_id INTEGER NOT NULL,
					class_id INTEGER NOT NULL,
					term_id INTEGER NOT NULL,
					amount INTEGER NOT NULL CHECK(amount >= 0),
					payment_date TEXT NOT NULL,
					payment_type TEXT DEFAULT 'tuition' CHECK(payment_type IN ('tuition', 'extra')),
					description TEXT,
					created_at TEXT DEFAULT (datetime('now','localtime')),
					updated_at TEXT DEFAULT (datetime('now','localtime')),
					FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE ON UPDATE CASCADE,
					FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE ON UPDATE CASCADE,
					FOREIGN KEY(term_id) REFERENCES student_terms(id) ON DELETE CASCADE ON UPDATE CASCADE
				);
			""")
			c.execute("""
				INSERT INTO payments (id, student_id, class_id, term_id, amount, payment_date, payment_type, description, created_at, updated_at)
				SELECT id, student_id, class_id, term_id, amount, payment_date, payment_type, description, created_at, updated_at
				FROM payments_old WHERE term_id IS NOT NULL;
			""")
			c.execute("DROP TABLE payments_old;")

			# --- 4) Partial Unique Index on student_terms ---
			c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_active_term ON student_terms(student_id, class_id) WHERE end_date IS NULL;")

			# Re-create other indexes for rebuilt tables
			c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_student_id ON sessions(student_id);")
			c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_class_id ON sessions(class_id);")
			c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_class_date_time ON sessions(class_id, date, time);")
			c.execute("CREATE INDEX IF NOT EXISTS idx_payments_student_id ON payments(student_id);")
			c.execute("CREATE INDEX IF NOT EXISTS idx_payments_class_id ON payments(class_id);")
			c.execute("CREATE INDEX IF NOT EXISTS idx_payments_term_id ON payments(term_id);")
			c.execute("CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(payment_date);")

			conn.commit()
		finally:
			c.execute("PRAGMA foreign_keys=ON;")


def run_all_migrations():
	"""Runner for all versioned migrations."""
	apply_migration(1, migrate_attendance_unique_constraint)
	apply_migration(2, migrate_v2_modernize_schema)
