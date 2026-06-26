# Attendance stays date-keyed; lesson duration is a Term property

AcaSmart keeps attendance keyed by `(student_id, class_id, term_id, date)` — one record per student per class per day — and a Term is sold and counted in **lessons**, not 30-minute units. A 60-minute lesson is one Session that counts once toward the Term's session limit; its duration affects only scheduling-conflict detection and tuition, never the count.

A prior attempt (reverted) re-keyed attendance to `session_id` to allow two attendance marks on the same day, motivated by 1-hour lessons (two back-to-back 30-minute slots). That cascade broke the app. We rejected it because the academy never marks the two halves of a 1-hour lesson independently — a 1-hour lesson is one human event — so the only thing duration must drive is interval-aware conflict detection and price, both of which are far cheaper than session-keyed attendance.

## Consequences

- Lesson duration is fixed when the Term is created (a Term cannot mix lesson lengths).
- Conflict detection must become interval-aware (a 16:00 60-minute lesson conflicts with a 16:30 lesson); exact-time-string matching is insufficient.
