"""Versioned, backed-up schema migrations (see docs/adr/0008).

Migrations are tracked by SQLite's built-in ``PRAGMA user_version``. On startup
``run_migrations()``:

1. Ensures the baseline schema exists (idempotent ``create_tables()``), and stamps
   any pre-versioning database (``user_version == 0``) as the BASELINE_VERSION.
2. Applies every migration in ``MIGRATIONS`` whose target version is greater than
   the database's current version, in order.

Safety (ADR-0008):
- Before applying any pending migration, the database file is copied to a
  timestamped backup using SQLite's online-backup API (consistent even under WAL).
- Each migration runs on its own connection; on ANY exception the backup is
  restored over the live file and startup aborts. Never leave a half-migrated DB.

Migration contract — each entry is ``(target_version, name, fn)`` where ``fn(conn)``
receives an autocommit connection and MUST manage its own transaction (and any
``PRAGMA foreign_keys`` toggling) itself. Use the ``transactional(conn)`` helper for
simple, single-transaction migrations. Keep ``fn`` idempotent (guard with
``PRAGMA table_info`` / ``sqlite_master`` checks) so a re-run is harmless.
"""
from __future__ import annotations

import logging
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from acasmart.paths import DB_PATH
from acasmart.data.db import get_connection
from acasmart.data.schema import create_tables

logger = logging.getLogger(__name__)

# Baseline = the schema produced by create_tables() (which itself runs the legacy
# attendance-UNIQUE migration). Existing installs are stamped to this with no data change.
BASELINE_VERSION = 1

def _migrate_v2_payments_integrity(conn):
    """v2: add CHECK(amount > 0 AND payment_type IN ('tuition','extra')) to payments.

    SQLite can't ALTER-ADD a constraint, so the table is rebuilt. Money is never
    changed silently: rows with amount <= 0 or an invalid (non-null) payment_type
    abort the migration (the framework then restores the backup). A NULL
    payment_type is coerced to the schema default 'tuition'.
    """
    # Pre-scan: refuse to touch money silently.
    bad = conn.execute(
        "SELECT COUNT(*) FROM payments "
        "WHERE amount <= 0 "
        "   OR (payment_type IS NOT NULL AND payment_type NOT IN ('tuition','extra'))"
    ).fetchone()[0]
    if bad:
        sample = conn.execute(
            "SELECT id, term_id, amount, payment_type FROM payments "
            "WHERE amount <= 0 "
            "   OR (payment_type IS NOT NULL AND payment_type NOT IN ('tuition','extra')) "
            "LIMIT 10"
        ).fetchall()
        raise RuntimeError(
            f"payments integrity migration aborted: {bad} row(s) violate "
            f"amount>0 / valid payment_type. Fix these manually first. "
            f"Sample (id, term_id, amount, type): {[tuple(r) for r in sample]}"
        )

    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        with transactional(conn):
            conn.execute("""
                CREATE TABLE payments_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    class_id INTEGER NOT NULL,
                    term_id INTEGER,
                    amount INTEGER NOT NULL,
                    payment_date TEXT NOT NULL,
                    payment_type TEXT NOT NULL DEFAULT 'tuition',
                    description TEXT,
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    updated_at TEXT DEFAULT (datetime('now','localtime')),
                    CHECK (amount > 0 AND payment_type IN ('tuition','extra')),
                    FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE ON UPDATE CASCADE,
                    FOREIGN KEY(class_id)   REFERENCES classes(id)  ON DELETE CASCADE ON UPDATE CASCADE,
                    FOREIGN KEY(term_id)    REFERENCES student_terms(id) ON DELETE CASCADE ON UPDATE CASCADE
                )
            """)
            conn.execute("""
                INSERT INTO payments_new
                    (id, student_id, class_id, term_id, amount, payment_date,
                     payment_type, description, created_at, updated_at)
                SELECT
                    id, student_id, class_id, term_id, amount, payment_date,
                    COALESCE(payment_type, 'tuition'), description, created_at, updated_at
                FROM payments
            """)
            conn.execute("DROP TABLE payments")
            conn.execute("ALTER TABLE payments_new RENAME TO payments")
            # Recreate indexes (dropped together with the old table).
            conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_student_id ON payments(student_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_class_id   ON payments(class_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_date       ON payments(payment_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_term_id    ON payments(term_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_term_date  ON payments(term_id, payment_date)")
            violations = conn.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RuntimeError(f"payments FK check failed after rebuild: {violations[:5]}")
    finally:
        conn.execute("PRAGMA foreign_keys=ON")


def _migrate_v3_attendance_status(conn):
    """v3: three-state attendance — add status + cancel_reason (additive), backfill from is_present.

    A scheduled lesson resolves to 'present', 'absent', or 'canceled' (ADR-0006).
    Canceled consumes no session. Columns are added with ALTER (additive, low-risk);
    is_present is kept for now. The status CHECK is deferred to the model-B rebuild,
    so validity is enforced in the repository layer.
    """
    cols = [r[1] for r in conn.execute("PRAGMA table_info(attendance)").fetchall()]
    added_status = "status" not in cols
    with transactional(conn):
        if added_status:
            conn.execute("ALTER TABLE attendance ADD COLUMN status TEXT NOT NULL DEFAULT 'present'")
        if "cancel_reason" not in cols:
            conn.execute("ALTER TABLE attendance ADD COLUMN cancel_reason TEXT")
        if added_status:
            # Backfill once, only when the column was just created (avoids clobbering
            # any 'canceled' rows on a re-run).
            conn.execute(
                "UPDATE attendance SET status = CASE WHEN is_present = 1 THEN 'present' ELSE 'absent' END"
            )


def _migrate_v4_term_lesson_duration(conn):
    """v4: lesson duration is a Term property (ADR-0004).

    Additive column (default 30 minutes). Drives interval-aware conflict detection
    and pricing; a 60 marks a one-hour lesson. Existing terms default to 30.
    """
    cols = [r[1] for r in conn.execute("PRAGMA table_info(student_terms)").fetchall()]
    if "lesson_duration" in cols:
        return
    with transactional(conn):
        conn.execute(
            "ALTER TABLE student_terms ADD COLUMN lesson_duration INTEGER NOT NULL DEFAULT 30"
        )


def _time_mins(t):
    """تبدیل "HH:mm" (ارقام فارسی/انگلیسی) به دقیقه؛ None اگر نامعتبر."""
    try:
        t = str(t).strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
        hh, mm = t.split(":")
        return int(hh) * 60 + int(mm)
    except Exception:
        return None


def _migrate_v5_dedup_active_terms(conn):
    """v5: merge duplicate active terms (one-hour-lesson splits), then enforce one-active-term.

    Each (student_id, class_id) with more than one active term is a one-hour lesson that was
    split into two 30-minute-slot terms. They are merged into a single survivor term (the
    earliest start_time): session-limits and tuition fees are SUMMED (two halves → the full
    enrollment, e.g. 6+6 sessions / 4.2M+4.2M → 12 / 8.4M), payments are repointed (summed),
    attendance and sessions are repointed (same-day attendance collapses via the UNIQUE
    constraint), the merged term's lesson_duration is set to the full span (e.g. 60), and the
    emptied duplicate term is deleted. Then a partial unique index makes a second active term
    for the same student+class physically impossible. Every merge is logged.
    """
    groups = conn.execute("""
        SELECT student_id, class_id FROM student_terms
        WHERE end_date IS NULL
        GROUP BY student_id, class_id HAVING COUNT(*) > 1
    """).fetchall()

    with transactional(conn):
        sessions_present = _table_exists(conn, "sessions")
        for sid, cid in groups:
            terms = conn.execute("""
                SELECT id, start_time, COALESCE(sessions_limit, 0), COALESCE(tuition_fee, 0)
                FROM student_terms
                WHERE student_id = ? AND class_id = ? AND end_date IS NULL
                ORDER BY start_time ASC, id ASC
            """, (sid, cid)).fetchall()

            survivor = terms[0][0]
            others = [t[0] for t in terms[1:]]
            # Session limit is KEPT at the survivor's value (a one-hour lesson is one lesson,
            # counted once — not doubled). Fees still SUM (two 4.2M halves → the full 8.4M).
            kept_limit = terms[0][2]
            total_fee = sum(t[3] for t in terms)
            starts = [m for m in (_time_mins(t[1]) for t in terms) if m is not None]
            duration = (max(starts) + 30 - min(starts)) if starts else 30 * len(terms)

            for o in others:
                # attendance/sessions: repoint, then drop rows that collided on the UNIQUE key
                conn.execute("UPDATE OR IGNORE attendance SET term_id = ? WHERE term_id = ?", (survivor, o))
                conn.execute("DELETE FROM attendance WHERE term_id = ?", (o,))
                if sessions_present:  # legacy table may already be gone on fresh installs
                    conn.execute("UPDATE OR IGNORE sessions SET term_id = ? WHERE term_id = ?", (survivor, o))
                    conn.execute("DELETE FROM sessions WHERE term_id = ?", (o,))
                # payments: plain repoint (summed onto survivor — no UNIQUE on term_id)
                conn.execute("UPDATE payments SET term_id = ? WHERE term_id = ?", (survivor, o))
                conn.execute("DELETE FROM student_terms WHERE id = ?", (o,))

            conn.execute("""
                UPDATE student_terms
                SET sessions_limit = ?, tuition_fee = ?, lesson_duration = ?,
                    updated_at = datetime('now','localtime')
                WHERE id = ?
            """, (kept_limit, total_fee, duration, survivor))
            logger.info(
                "🔗 merged active terms %s into %s (student=%s class=%s): limit=%s fee=%s duration=%smin",
                others, survivor, sid, cid, kept_limit, total_fee, duration,
            )

        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_term
            ON student_terms(student_id, class_id) WHERE end_date IS NULL
        """)
        remaining = conn.execute("""
            SELECT COUNT(*) FROM (
                SELECT 1 FROM student_terms WHERE end_date IS NULL
                GROUP BY student_id, class_id HAVING COUNT(*) > 1
            )
        """).fetchone()[0]
        if remaining:
            raise RuntimeError(f"{remaining} duplicate active-term group(s) remain; aborting migration")


def _migrate_v6_drop_sessions(conn):
    """v6 (Model-B, ADR-0002): drop the legacy `sessions` table.

    Lessons are now computed from each term's weekly schedule, so the eager session rows
    are obsolete. By this point all live code reads/writes student_terms + attendance only;
    the table is gone for good (this is the irreversible step — it runs after the automatic
    pre-migration backup).
    """
    with transactional(conn):
        conn.execute("DROP TABLE IF EXISTS sessions")


# Ordered list of hardening migrations. Each: (target_version, name, fn(conn)).
# Versions must be contiguous and strictly greater than BASELINE_VERSION.
MIGRATIONS = [
    (2, "payments_integrity", _migrate_v2_payments_integrity),
    (3, "attendance_status", _migrate_v3_attendance_status),
    (4, "term_lesson_duration", _migrate_v4_term_lesson_duration),
    (5, "dedup_active_terms", _migrate_v5_dedup_active_terms),
    (6, "drop_sessions", _migrate_v6_drop_sessions),
]


@contextmanager
def transactional(conn):
    """Run a block inside an explicit transaction on an autocommit connection."""
    conn.execute("BEGIN")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _user_version(conn) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def _set_user_version(conn, version: int) -> None:
    # PRAGMA does not accept bound parameters; version is an int we control.
    conn.execute(f"PRAGMA user_version = {int(version)}")


def _table_exists(conn, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?", (name,)
    ).fetchone() is not None


def _backup_db(from_version: int) -> "Path | None":
    """Snapshot the live DB via the online-backup API. Returns the backup path."""
    db_path = Path(DB_PATH)
    if not db_path.exists():
        return None  # fresh install — nothing to back up yet

    backups_dir = db_path.parent / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = backups_dir / f"{db_path.stem}.v{from_version}.{stamp}.db"

    src = sqlite3.connect(str(db_path))
    try:
        dst = sqlite3.connect(str(dest))
        try:
            src.backup(dst)  # consistent snapshot, WAL-safe
        finally:
            dst.close()
    finally:
        src.close()

    logger.info("📦 DB backup created before migration: %s", dest)
    return dest


def _restore_db(backup_path: "Path") -> None:
    """Overwrite the live DB with a backup and drop stale WAL/SHM sidecars."""
    db_path = Path(DB_PATH)
    for suffix in ("-wal", "-shm"):
        side = Path(str(db_path) + suffix)
        if side.exists():
            try:
                side.unlink()
            except OSError as e:
                logger.warning("could not remove %s: %s", side, e)
    shutil.copyfile(backup_path, db_path)
    logger.warning("♻️ DB restored from backup: %s", backup_path)


def run_migrations() -> None:
    """Apply all pending schema migrations atomically, with pre-backup + restore-on-fail."""
    # 1) Baseline bootstrap. create_tables() is idempotent and also runs the legacy
    #    attendance-UNIQUE migration. A brand-new/pre-versioning DB is stamped to baseline.
    create_tables()
    with get_connection() as conn:
        current = _user_version(conn)
        if current == 0:
            _set_user_version(conn, BASELINE_VERSION)
            conn.commit()
            current = BASELINE_VERSION
            logger.info("🔖 stamped baseline schema as v%d", BASELINE_VERSION)

    # 2) Compute pending migrations.
    pending = sorted((v, name, fn) for (v, name, fn) in MIGRATIONS if v > current)
    if not pending:
        return

    logger.info("⏳ %d migration(s) pending (current v%d → v%d)",
                len(pending), current, pending[-1][0])

    # 3) One backup before touching anything.
    backup_path = _backup_db(current)

    # 4) Apply each migration on its own connection; restore on any failure.
    for version, name, fn in pending:
        conn = get_connection()
        conn.isolation_level = None  # autocommit; fn manages its own transaction
        try:
            fn(conn)
            _set_user_version(conn, version)
            logger.info("✅ migration v%d (%s) applied", version, name)
        except Exception:
            logger.exception("❌ migration v%d (%s) failed", version, name)
            try:
                conn.close()
            except Exception:
                pass
            if backup_path is not None:
                _restore_db(backup_path)
            raise RuntimeError(
                f"Migration v{version} ({name}) failed; database restored from backup. "
                f"Startup aborted."
            )
        finally:
            try:
                conn.close()
            except Exception:
                pass
