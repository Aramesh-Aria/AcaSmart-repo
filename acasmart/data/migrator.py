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

# Ordered list of hardening migrations. Each: (target_version, name, fn(conn)).
# Versions must be contiguous and strictly greater than BASELINE_VERSION.
# Example (commented until implemented):
#
#   def _migrate_v2_payments_check(conn):
#       # table-rebuild migration: manage FK + transaction explicitly
#       conn.execute("PRAGMA foreign_keys=OFF")
#       with transactional(conn):
#           conn.execute("CREATE TABLE payments_new ( ... CHECK (amount > 0 ...) )")
#           conn.execute("INSERT INTO payments_new SELECT ... FROM payments")
#           conn.execute("DROP TABLE payments")
#           conn.execute("ALTER TABLE payments_new RENAME TO payments")
#       conn.execute("PRAGMA foreign_keys=ON")
#
#   MIGRATIONS = [(2, "payments_check", _migrate_v2_payments_check)]
MIGRATIONS: list = []


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
