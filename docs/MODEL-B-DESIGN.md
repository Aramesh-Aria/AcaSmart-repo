# Model-B Design (Phase 2) — schedule-as-truth, computed occurrences

**Status: ✅ COMPLETE** — all 6 slices shipped and verified against copies of the live database; the `sessions` table is dropped by migration v6. Lessons are computed from each term's weekly schedule.

Implements ADR-0002. Replaces eagerly hand-placed `sessions` rows with lessons **computed** from each enrollment's weekly schedule. Locked decisions (grilling, Phase 2):

- **Q1 — stable weekly slots.** A student keeps one weekday + time for the whole term; holidays/makeups are exceptions, not the norm. Model-B's weekly base pattern fits.
- **Q2 — drop the `sessions` table.** After Items 4 & 6 the **attendance** table already records every held/canceled lesson, so `sessions` is redundant. One source of truth.

## Data model

- **`student_terms`** = the enrollment (unchanged). PK is the `term_id`. Carries `student_id`, `class_id`, `start_date`, `start_time`, `lesson_duration`, `sessions_limit`, `tuition_fee`, `currency_unit`, `profile_id`, `end_date`. **Registering a student = inserting this row.** `term_id` always comes from here, never from a session.
- **`attendance`** = the record of what happened (present/absent/canceled per `term_id` + date). Unchanged.
- **`sessions`** = removed (migration v6). Upcoming lessons are computed, not stored.

## The schedule

A term's lessons fall on a **weekly base pattern**: starting `start_date`, every 7 days (same weekday as `class.day`), at `start_time` for `lesson_duration` minutes. A date `D` is a scheduled occurrence of term `T` when `D >= T.start_date` and `days_between(start_date, D)` is a non-negative multiple of 7.

**Completion interacts with the schedule.** The term needs `sessions_limit` *held* lessons (present+absent; canceled doesn't count — ADR-0006). A canceled week is still a scheduled occurrence (so the admin can mark it canceled) but doesn't advance the held count, so it pushes the term one week longer.

Attendance-page rule — show term `T`'s student on date `D` when:
`is_weekly_occurrence(T.start_date, D)` AND (`an attendance row already exists for (T, D)` OR `held_count(T) < T.sessions_limit`).

## Conflict detection (recomputed)

Student and teacher conflicts are computed from **term schedules** (same weekday + interval overlap on `start_time`/`lesson_duration`) instead of scanning `sessions` rows — strictly better, since it reflects the real weekly commitment. The old session-based `is_class_slot_taken` was removed: a class slot being "taken" is now subsumed by the teacher conflict (one teacher can't be double-booked) plus the student conflict. Room is a label only — not a conflict dimension (see the Enrollment Schedule entry in CONTEXT.md).

## Implementation slices (all shipped — each tested on a DB copy before the next)

1. ✅ **Occurrence engine** (`acasmart/core/schedule.py`) — pure Shamsi date logic: `days_between`, `is_weekly_occurrence`, `occurrence_dates`, `add_weeks`, plus `weekday_fa` / `first_on_or_after` (added during testing to snap a start date onto the class weekday).
2. ✅ **Computed attendance-page fetch** — `sessions_repo.fetch_scheduled_students_for_class_on_date` lists students for class+date from term schedules + held-count, replacing the session-based fetch; wired into `attendance_window`.
3. ✅ **Computed conflict detection** — `has_student_schedule_conflict` / `has_teacher_schedule_conflict` read `student_terms` (interval overlap on `start_time`/`lesson_duration`), used by term creation.
4. ✅ **Enrollment** — `enroll_student` creates only the term (no session row); `insert_student_term_if_not_exists` reordered (get-existing first) and uses schedule-based conflicts.
5. ✅ **Session-manager UI rework** — now an enrollment manager (student + class + start date + time + duration/limit/fee → term); lists active enrollments; double-click un-enrolls. Click-tested by the user.
6. ✅ **Migration v6** — `DROP TABLE sessions`; `sessions_repo` reduced to Model-B functions; `schema.py` no longer creates the table (and v5 guarded for its absence).

### Fixes that came out of click-testing

- **Start-date snap** — enrollment snaps `start_date` to the first class-weekday on/after the chosen date (`first_on_or_after`), so weekly occurrences land on the class day and the student appears on the attendance page.
- **Duplicate guard** — re-enrolling a student already active in a class is blocked up front (one active term per student/class).
- **Pickers** — student/class pickers now show the **teacher** (derived from `student_terms`, not `sessions`) and an **active-term count**, searchable by teacher name. The 8 remaining live `sessions`-table references (delete-guards in `classes_repo`/`teachers_repo`/`payments_repo`, the attendance cleanup calls, the per-class count) were all rewritten onto `student_terms`.

## Risks

- Shamsi (Jalali) date arithmetic — handled via `jdatetime` (convert to Gregorian, add `timedelta`, convert back) and unit-tested.
- The session-manager rewrite is GUI and untestable here — done last, behind the user's click-through, after all data-layer slices are proven.
- Dropping `sessions` is irreversible — migration v6 runs after a full backup (ADR-0008) and after slices 1–5 are stable.
