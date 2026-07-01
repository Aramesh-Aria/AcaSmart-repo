# PRD — AcaSmart Operational Data-Model Modernization (Hardening + Model-B)

> Status: **implemented and verified** (migrations v2–v6). This PRD is the spec-of-record synthesised from the design conversation; it uses the `CONTEXT.md` glossary and respects ADRs `docs/adr/0001`–`0009`.

## Problem Statement

The academy admin's operational records get **buggy and messy**. In daily use:

- The same Student ends up with **two active Terms** for one Class, so Tuition Payments and Attendance scatter across a phantom Term and the totals stop adding up. This happens for one-hour lessons (recorded as two 30-minute slots) and on any re-entry.
- When a Term completes, it becomes **frozen and hidden**: the admin can't view or edit its past Sessions, and if the Renewal Reminder SMS failed to send (e.g. bad provider config), the Term is stuck — the reminder can never be resent.
- Lessons are entered as eager `sessions` rows that the admin must place by hand; future rows go stale after edits, and cleanup machinery causes more confusion than it removes.
- Money rules (no overpayment of Tuition, valid amounts/types) live only in the UI, so any other path can corrupt the financial record.

The admin needs the records to be **trustworthy and self-correcting**, and lesson scheduling to be **automatic** rather than hand-maintained.

## Solution

Two coordinated changes, applied as ordered, backed-up, reversible-on-failure database migrations:

1. **Hardening** — make the records correct and safe by construction: enforce one active Term per Student per Class in the database; make Term completion a *derived, two-way* status (so a completed Term re-opens for editing instead of freezing); record the Renewal Reminder as sent only on genuine provider success and give the admin a resend action; add Canceled as a third Attendance outcome that consumes no Session; push money rules into the database/repository; make scheduling-conflict detection interval-aware.

2. **Model-B (schedule-as-truth)** — stop storing individual lessons. A Student is **enrolled** once (a Term carrying weekday, time, Lesson Duration, Session limit, and snapshotted Tuition); the weekly lessons are **computed** from that schedule. The `sessions` table is removed entirely; Attendance (Present/Absence/Canceled per date) is the only record of what actually happened.

The admin enrolls a Student once and the lessons appear automatically on the Attendance page each week; corrections are always possible; duplicate enrollments are impossible; and the financial picture is settled and consistent.

## User Stories

1. As an academy admin, I want to enroll a Student into a Class once (Student, Class, start date, time, Lesson Duration, Session count, Tuition), so that their weekly lessons appear automatically without my entering each one.
2. As an admin, I want the enrollment start date to snap to the Class's weekday, so that the computed weekly lessons land on the day the Class actually meets.
3. As an admin, I want to be blocked with a clear message when I try to enroll a Student who already has an active Term in that Class, so that I never create duplicate enrollments.
4. As an admin, I want the system to reject an enrollment that overlaps the same Student's or the same Teacher's existing weekly slot (by lesson interval, not exact start time), so that a one-hour lesson at 16:00 conflicts with a 16:30 booking.
5. As an admin, I want a one-hour lesson to count as a single lesson toward the Term's Session limit, so that a 6-lesson Term completes after six one-hour lessons.
6. As an admin, I want the Attendance page to show exactly the Students whose weekly lesson falls on the selected date, so that I mark the right people.
7. As an admin, I want to mark each lesson Present or Absence, so that the Term progresses toward its Session limit.
8. As an admin, I want to mark a lesson Canceled with a reason (holiday, Teacher sick), so that a week that didn't happen does not burn one of the Student's paid Sessions.
9. As an admin, I want a canceled week to push the Term one week longer, so that the Student still receives the number of lessons they paid for.
10. As an admin, I want a Term to be marked complete automatically when its counted Attendance reaches the Session limit, so that I don't track completion by hand.
11. As an admin, I want a completed Term to re-open automatically if I delete or cancel one of its Attendance records, so that I can correct mistakes after the fact.
12. As an admin, I want to toggle "show completed terms" on the Attendance page, so that I can view and edit the past lessons of a finished Term.
13. As an admin, I want the Renewal Reminder SMS to be sent automatically when exactly one Session remains, so that the parent is reminded to renew.
14. As an admin, I want the reminder recorded as "sent" only when the provider genuinely accepts it, so that a disabled/failed/errored send stays eligible for resend.
15. As an admin, I want a **resend** button for a Term whose reminder is due but not yet successfully sent, so that I can recover from a transient SMS failure.
16. As an admin, I want a Term that was wrongly flagged sent (by the old bug) to be resendable, so that no Student is silently missed.
17. As an admin, I want to record Tuition Payments and Extra Payments against a Term, so that I track the Student's financial account.
18. As an admin, I want the system to reject a Tuition Payment that exceeds the remaining Tuition debt, on every path (not just the UI), so that a Term is never overpaid by accident.
19. As an admin, I want the database to reject a payment with a non-positive amount or an invalid type, so that the financial record can't be corrupted.
20. As an admin, I want the duplicate one-hour-lesson Terms in my existing data merged into one settled Term (limit kept, fees and payments summed) when I upgrade, so that my historical records are cleaned up without losing money.
21. As an admin, I want to delete an enrollment that was a setup mistake, so that I can remove it cleanly.
22. As an admin, I want deletion blocked once a Term has any Payment or Attendance, so that I never destroy real history by accident.
23. As an admin, I want to find a Student in the picker by their name **or** their Teacher's name, so that I can locate them quickly.
24. As an admin, I want each Student in the picker to show their Teacher and their number of active Terms, so that I can confirm I have the right person.
25. As an admin, I want my database automatically backed up before any schema upgrade and restored if the upgrade fails, so that an upgrade can never leave my data half-migrated or lost.
26. As an admin, I want all dates shown and entered in the Shamsi (Jalali) calendar, so that the app matches how I work.
27. As an admin, I want deleting a Class or Teacher to be blocked when they still have enrollments, so that I don't orphan records.

## Implementation Decisions

- **Enrollment is the Term.** `student_terms` is the single enrollment record (Student, Class, start_date, start_time, lesson_duration, sessions_limit, snapshotted tuition/currency, end_date). Its primary key is the `term_id` that Attendance and Payments reference. There is no separate enrollment entity and no per-lesson row.
- **Lessons are computed, not stored.** The `sessions` table is dropped (migration v6). Upcoming lessons are derived from the Term's weekly schedule (start_date + 7·n, same weekday, at start_time for lesson_duration). The Attendance listing and conflict checks read `student_terms` + `attendance` only. (ADR-0002.)
- **One active Term per Student per Class** is enforced by a partial unique index `UNIQUE(student_id, class_id) WHERE end_date IS NULL`. Enrollment catches the resulting integrity error and surfaces a friendly "already enrolled" message.
- **Term completion is a derived, two-way status.** A single routine sets `end_date` when counted Attendance reaches the Session limit and clears it back to NULL when Attendance drops below — guarded so it never produces two active Terms. (ADR-0005.)
- **Attendance is three-state** (Present / Absence / Canceled, plus a reason). Canceled consumes no Session; every "consumed sessions" count excludes it. The deletion guard still treats Canceled rows as history. (ADR-0006.)
- **One-hour lessons** are one lesson counted once (sell lessons, not 30-minute units). Lesson Duration is a Term property used for interval-aware conflict detection and pricing, not for counting. (ADR-0004.)
- **Conflict detection is interval-aware**, computed from active Terms on the same weekday (overlap of `[start, start+duration)`), for both Student and Teacher.
- **Renewal Reminder** is recorded as sent only on a genuine provider success; disabled/failed/errored sends stay resendable; an explicit resend action and a flag-reset are provided. (Matches the Renewal Reminder definition in `CONTEXT.md`.)
- **Financial invariants live below the UI**: a database `CHECK` (amount > 0 AND payment_type IN ('tuition','extra')) plus a repository-level Tuition-debt cap that rejects (never clamps) an overpayment. (ADR-0003.)
- **Dedup on upgrade**: existing duplicate active Terms (split one-hour lessons) are merged into a single survivor — Session limit kept, Tuition fees and Payments summed, Attendance consolidated (same-day collapses), Lesson Duration set to the full span — with money conserved. (ADR-0009.)
- **Migration framework**: ordered, idempotent steps tracked by SQLite `PRAGMA user_version`; a WAL-safe file backup is taken before any pending step; on failure the backup is restored and startup aborts. Migration steps to date: v2 payment integrity, v3 three-state Attendance, v4 Lesson Duration, v5 dedup + unique index, v6 drop `sessions`. (ADR-0008.)
- **Delete-guards** (Class, Teacher, Term) and the per-Class/per-Student counts are computed from `student_terms` rather than the removed `sessions` table.
- **Out of the session-manager UI**, a Session-manager screen becomes an enrollment manager (enroll once; list active enrollments; double-click to un-enroll); the start date snaps to the Class weekday.

## Testing Decisions

- **What a good test asserts**: external behavior at the repository/migration boundary — given a database state, calling a repo function (enroll, record Attendance, refresh completion, insert Payment) or running `run_migrations()` produces the expected rows and return values. Not internal call shapes.
- **Primary seam — repository + migration layer (highest, preferred, single).** Tests run against a `shutil.copyfile` copy of the real SQLite database with `data.db.DB_PATH`/`data.migrator.DB_PATH` redirected at the copy, then `run_migrations()`. This is how the entire effort was verified: dedup conservation of money, two-way completion, canceled-excluded counts, the computed Attendance listing across weekly occurrences/completion/reopen, interval conflicts, debt-cap rejection, and the full v2→v6 chain (including that the dropped table is not re-created on the next startup).
- **Secondary seam — offscreen widget construction.** With `QT_QPA_PLATFORM=offscreen`, instantiate the changed widgets/pickers against a migrated DB copy to catch import/construction errors and verify rendered row text. Does not cover click flows — those are the admin's interactive check.
- **Prior art**: the inline DB-copy integration scripts used throughout this initiative are the template for future tests; there is no formal test runner configured.

## Out of Scope

- Group Classes (multiple Students in one Session) — explicitly excluded (ADR-0001).
- Room as a scheduling-conflict dimension — Room is a descriptive label only.
- A first-class Rescheduled-Session entity — rescheduling is modeled as a Canceled Session plus Attendance on the new date.
- A full Adjustment/audit ledger — corrections are lightweight (warned edits + history-protecting delete guard), suitable for a single admin.
- Provider-body inspection for SMS acceptance (beyond HTTP 200) — deferred hardening.
- Calendar rendering of upcoming computed lessons beyond the Attendance page.

## Further Notes

- The grilled domain model is in `CONTEXT.md`; the design rationale is in `docs/adr/0001`–`0009`; the hardening roadmap and the Model-B refactor are in `docs/IMPLEMENTATION-PLAN.md` and `docs/MODEL-B-DESIGN.md`.
- Databases live in the OS app-data directory (not the repo); each upgrade self-backs-up to `<app-data>/backups/`.
- On an admin's machine that has been running the app, hardening migrations (v2–v5) already applied; the `sessions` drop (v6) applies on the next launch.
