# AcaSmart Implementation Plan

Derived from the grilling session (2026-06). Decisions are recorded in `docs/adr/0002`–`0008` and `CONTEXT.md`. This plan is split into **Phase 1 — Hardening (now)** and **Phase 2 — Model-B (later)**, per ADR-0008.

## Grounding facts (verified)

- Live DB: `/Users/aria/Library/Application Support/AcaSmart/acasmart.db` (resolved via `acasmart/paths.py` → `get_app_data_dir()`). Current `PRAGMA user_version = 0`.
- Connection + transaction helpers already exist: `acasmart/data/db.py` → `get_connection()`, `tx()`.
- Schema bootstrap: `acasmart/data/schema.py::create_tables()`; at line ~288 it calls `migrate_attendance_unique_constraint()`.
- Existing migrations are ad-hoc (`acasmart/data/migrations.py`); **no version tracking**. `migrate_drop_student_terms_term_id()` is defined but never called (dead code — delete it).
- SMS bug branch: `acasmart/ui/windows/attendance_window.py:371-375` marks sent on anything that isn't `DISABLED` (so config-`FAILED` is wrongly marked sent). `sms_notifier.py` returns `{"status": SmsStatus.SENT|FAILED|DISABLED}` and `raise`s on non-200.
- Sent ledger: `notifications_repo.py::{has_renew_sms_been_sent, mark_renew_sms_sent}` over `sms_notifications` with `UNIQUE(student_id, term_id)`, `INSERT OR IGNORE`, **no delete path**.

---

## Phase 0 — Migration framework (foundation for everything below) — ADR-0008

**Goal:** ordered, idempotent, atomic, backed-up migrations keyed on `PRAGMA user_version`.

**New file `acasmart/data/migrator.py`:**

- `BACKUP`: before running any pending step, copy the DB file to `<db>.backup-<user_version>-<timestamp>` (timestamp passed in / from a non-frozen source). Keep last N backups.
- `MIGRATIONS = [(2, "payments_check", fn), (3, "attendance_status", fn), ...]` — list of `(target_version, name, callable(conn))`.
- `run_migrations()`:
  1. Read `PRAGMA user_version`.
  2. If `0`: run `create_tables()` + `migrate_attendance_unique_constraint()` (idempotent), then stamp `user_version = 1` (**baseline** = today's shipped schema). Existing installs match this with no data change.
  3. For each `(v, name, fn)` with `v > user_version`: **back up once**, then in a single transaction run `fn(conn)` and `PRAGMA user_version = v`. On exception: `rollback`, restore backup, abort startup with a clear message (never leave a half-migrated DB).
- Each `fn` must be idempotent (guard with `PRAGMA table_info` / `sqlite_master` checks) so a re-run is safe.

**Wire-in:** replace the single `migrate_attendance_unique_constraint()` call at `schema.py:288` with `run_migrations()` (or call it from app startup right after `create_tables()`).

**Test:** copy live DB to a scratch path, point `DB_PATH` at the copy, run `run_migrations()` twice — second run is a no-op; `user_version` advances correctly; a deliberately-thrown step restores the backup.

---

## Phase 1 — Hardening (now)

Ordered by risk and dependency. Items 1–3 are **code-only** (no schema change) and can ship immediately and independently. Items 4–7 are versioned migrations.

### 1. SMS success semantics + resend button — ADR-0005, CONTEXT.md "Renewal Reminder" *(highest daily value)*

- **`attendance_window.py:367-379`** — change the branch so the sent flag is written **only on genuine success**:
  ```python
  if result.get("status") == SmsStatus.SENT:
      mark_renew_sms_sent(sid, term_id)
  elif result.get("status") == SmsStatus.DISABLED:
      pass  # intentional, stays resendable
  else:  # FAILED
      failed_sms.append(name)
  # non-200 still raises → caught → failed_sms (already correct)
  ```
- **`notifications_repo.py`** — add `clear_renew_sms_sent(student_id, term_id)` (`DELETE FROM sms_notifications WHERE ...`). Needed to unstick terms wrongly marked sent by the old bug, and to support force-resend.
- **Resend action** — in the attendance window (and the completed-term history view from item 5), add a "ارسال مجدد یادآوری" button per student/term, enabled when the reminder is **due** (count == limit−1, or term complete) and `not has_renew_sms_been_sent`. It calls `send_renew_term_notification` and marks sent only on `SENT`.
- Because the row is now written only on success, resend stays available until it actually goes through — no UNIQUE-constraint trap.
- **Deferred (Q8 "B" later):** inspect the IPPanel response body, not just HTTP 200.

### 2. Deletion guard checks attendance — ADR-0007, CONTEXT.md "Deletion"

- **`payments_repo.py::delete_term_if_no_payments`** (line ~206) — also count attendance; block deletion if **payments OR attendance** exist. Rename to `delete_term_if_no_history`; update callers in `sessions_repo.py:231` and `session_manager.py:468,517`.

### 3. Derived completion / two-way `end_date` — ADR-0005

- Add **`terms_repo.py::refresh_term_completion(term_id)`** to replace both `check_and_set_term_end_by_id` and `recalc_term_end_by_id`:
  - count = attendance rows for the term **with status in ('present','absent')** (canceled excluded — depends on item 4; until then, all rows).
  - if `count >= limit` → `end_date = max(counting date)`; else → `end_date = NULL` (the missing half today).
  - **Edge (flag):** setting `end_date = NULL` can collide with the active-term unique index (item 6) if a *newer* active term exists for the same student+class. Guard: only NULL it when no other active term exists; otherwise leave the marker but still allow editing via the history view. Editability is a UI concern, not gated on `end_date`.
- Call `refresh_term_completion` after every attendance insert / delete / status change.
- **History view:** add a screen (or unlock the attendance window) to open **any** term — active or complete — and edit its attendance. This removes the `selected_date > end_date` save block (`attendance_window.py:340`) for the explicit history path.

### 4. Three-state attendance — ADR-0006, CONTEXT.md "Attendance"  *(migration v3)*

- Migration: `ALTER TABLE attendance ADD COLUMN status TEXT NOT NULL DEFAULT 'present'`; `ADD COLUMN cancel_reason TEXT`; backfill `status = CASE is_present WHEN 1 THEN 'present' ELSE 'absent' END`. (Additive ALTERs — safe. Keep `is_present` for now; drop in a later rebuild.)
- **`attendance_repo.py`** — `insert_attendance_with_date(...)` takes a `status` (present/absent/canceled) instead of/alongside `is_present`; validate `status IN {...}` in Python (DB `CHECK` deferred to the model-B rebuild, since SQLite can't add a CHECK via ALTER).
- **Counting** — `count_attendance_by_term` and `refresh_term_completion` count only `status IN ('present','absent')`; canceled consumes nothing.
- **UI** — attendance window gains a "لغو جلسه" (cancel) option with a reason; canceled rows render distinctly and don't tick toward the limit. Reschedule = cancel-with-reason + record on the new date (no new entity).

### 5. Payment integrity — ADR-0003, CONTEXT.md "Tuition Payment"  *(migration v2)*

- Migration (table rebuild, since SQLite can't `ALTER ADD CONSTRAINT`): pre-scan `payments` for `amount <= 0` or `payment_type NOT IN ('tuition','extra')`; if any exist, **abort with a report** (don't silently change money). Then rebuild `payments` with `CHECK (amount > 0 AND payment_type IN ('tuition','extra'))` and `payment_type TEXT NOT NULL DEFAULT 'tuition'`; copy data; recreate indexes (`idx_payments_*`).
- **`payments_repo.py::insert_payment`** — fix `amount < 0` → `amount <= 0`; add repo-level debt cap: for `payment_type == 'tuition'`, reject (raise) if `amount > remaining_debt` where `remaining = tuition_fee − get_total_paid_for_term(term_id,'tuition')`. **Reject, never clamp.** Same guard in `update_payment_by_id`.
- UI keeps its friendly messages but is no longer the only guard.

### 6. One active term — DB partial unique index + dedup — ADR-0005/CONTEXT "Term"  *(migration v4 — riskiest, ship last)*

- **Step A (data, explicit + reported):** find groups of `student_terms` with same `(student_id, class_id)` and `end_date IS NULL` having `count > 1`. For each, pick a survivor (oldest `start_date`, or the one with most history), repoint `sessions.term_id`, `payments.term_id`, `attendance.term_id` to the survivor, then delete the extras. **Caution:** attendance has `UNIQUE(student_id,class_id,term_id,date)` — when repointing, a same-date collision can occur; merge per-date (`UPDATE OR IGNORE` then delete leftovers) so the copy can't fail. **Log every merge** (which terms merged into which) — no silent merges.
- **Step B:** `CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_term ON student_terms(student_id, class_id) WHERE end_date IS NULL;` (fails if Step A missed a duplicate → transaction aborts → backup restored).
- **`terms_repo.py::insert_student_term_if_not_exists`** — on the resulting `IntegrityError`, surface a friendly "این هنرجو از قبل یک ترم فعال در این کلاس دارد" with an option to open the existing term, instead of a raw DB error.

### 7. Interval-aware conflict detection — ADR-0004, CONTEXT.md "Enrollment Schedule"  *(migration v5, additive)*

- Migration: `ALTER TABLE student_terms ADD COLUMN lesson_duration INTEGER NOT NULL DEFAULT 30;` (per ADR-0004 duration is a Term property; 60 for 1-hour lessons).
- **`sessions_repo.py`** — rewrite `has_weekly_time_conflict` (line ~156) and `has_teacher_weekly_time_conflict` (line ~177) to test **interval overlap**: two lessons on the same weekday conflict when `[start, start+duration)` intervals intersect — not exact `time ==` string match. Pull duration from the term / class.
- Enrollment/scheduling UI surfaces the conflicting lesson on rejection.

---

## Phase 2 — Model-B (later, its own migration, after Phase 1 is stable) — ADR-0002

Structural rewrite to **lazy, schedule-as-truth** sessions. Out of scope for the hardening pass; gets its own backup, its own migration, and a full test pass against a **copy** of the live DB before it runs for real.

- Term carries its recurring commitment `(day, time, lesson_duration)` (day/time today live on `classes`; decide whether the schedule belongs on the term or stays on the class).
- Upcoming lessons are **computed** from the schedule, not stored.
- A `sessions` row is persisted **only** for a deviation (a Canceled Session from item 4) or once attendance is recorded.
- Retire eager pre-creation and the bulk-delete machinery: `add_session` (eager insert), `delete_future_sessions`, `delete_sessions_for_expired_terms`.
- Rework the attendance window to render computed occurrences for a date and materialize on action.

---

## Sequencing summary

| Order | Item | Type | Risk | Depends on |
|------|------|------|------|-----------|
| 0 | Migration framework | new code | low | — |
| 1 | SMS fix + resend | code-only | low | — |
| 2 | Deletion guard | code-only | low | — |
| 3 | Derived completion | code-only | medium | item 6 (uniqueness edge) |
| 4 | Three-state attendance | migration v3 | low | framework |
| 5 | Payment integrity | migration v2 | medium (rebuild) | framework |
| 6 | One active term + dedup | migration v4 | **high** (data) | framework |
| 7 | Interval-aware conflict | migration v5 | low | framework |
| — | Model-B | separate effort | high | Phase 1 stable |

Ship 1 and 2 first (sharpest daily pain, zero schema risk). Then the framework and the additive migrations (3/4/5/7). Do item 6 (dedup + unique index) **last** in Phase 1, on its own, with the backup verified.

## Backup & rollback discipline (ADR-0008)

- Mandatory file copy before any pending migration; abort-and-restore on failure.
- Each migration in a transaction; idempotent guards so re-runs are safe.
- Before item 6 and before Phase 2: dry-run against a **copy** of the live `acasmart.db`, inspect with `sqlite3`/DB browser, confirm counts and merges, then run for real.

## Open operational items

- Confirm a **routine backup** of `~/Library/Application Support/AcaSmart/acasmart.db` independent of the migration backups (e.g. before each app update).
- Deferred by choice: SMS response-body inspection; first-class reschedule; room enforcement; audit ledger (all revisitable if the academy adds staff/users).
