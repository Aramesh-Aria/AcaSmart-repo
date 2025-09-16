import logging
from data.db import get_connection

logger = logging.getLogger(__name__)


def migrate_attendance_unique_constraint():
	"""
	Ensure attendance has UNIQUE(student_id, class_id, term_id, date).
	If not, rebuild table with correct constraint and migrate data safely.
	"""
	with get_connection() as conn:
		c = conn.cursor()

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
			logger.info("ℹ️ ساختار UNIQUE صحیح است؛ مهاجرت لازم نیست.")
			return

		logger.info("🔄 اجرای مهاجرت UNIQUE برای جدول attendance...")

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
		# اگر قبلاً رکوردِ تکراری (بر اساس همان 4 ستون) وجود داشته،
		# با GROUP BY فقط یک رکورد نگه می‌داریم؛
		# is_present را MAX و created_at را MIN و updated_at را MAX می‌گیریم.
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
		logger.info("✅ مهاجرت جدول attendance با موفقیت انجام شد.")


def migrate_drop_student_terms_term_id():
	with get_connection() as conn:
		c = conn.cursor()

		c.execute("PRAGMA table_info(student_terms)")
		cols = [r[1] for r in c.fetchall()]
		if "term_id" not in cols:
			return  # قبلاً حذف شده؛ کاری نکن

		logger.info("🔄 حذف ستون student_terms.term_id ...")

		# 🔒 FKها را موقتاً خاموش کن تا sessions پاک نشوند
		c.execute("PRAGMA foreign_keys=OFF;")
		try:
			c.execute("""
				CREATE TABLE student_terms_new (
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
					FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE ON UPDATE CASCADE,
					FOREIGN KEY(class_id)   REFERENCES classes(id)  ON DELETE CASCADE ON UPDATE CASCADE,
					FOREIGN KEY(profile_id) REFERENCES pricing_profiles(id) ON DELETE SET NULL ON UPDATE CASCADE
				);
			""")

			c.execute("""
				INSERT INTO student_terms_new
					(id, student_id, class_id, start_date, end_date, start_time,
					 sessions_limit, tuition_fee, currency_unit, profile_id,
					 created_at, updated_at)
				SELECT
					id, student_id, class_id, start_date, end_date, start_time,
					sessions_limit, tuition_fee, currency_unit, profile_id,
					created_at, updated_at
				FROM student_terms;
			""")

			c.execute("DROP TABLE student_terms;")
			c.execute("ALTER TABLE student_terms_new RENAME TO student_terms;")

			conn.commit()
		finally:
			c.execute("PRAGMA foreign_keys=ON;")
