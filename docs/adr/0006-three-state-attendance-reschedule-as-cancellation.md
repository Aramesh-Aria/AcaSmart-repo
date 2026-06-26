# Attendance is a three-state outcome; rescheduling is modeled as cancellation

A scheduled lesson resolves to one of three outcomes: **Present**, **Absence**, or **Canceled**. Present and Absence are Attendance — the lesson happened — and each consumes one session from the Term. Canceled means the lesson did not happen: it consumes zero sessions, carries a reason, and stays in history. This replaces the previous `is_present` boolean with a status.

Rescheduling is **not** a separate concept. Moving a lesson to another date is recorded as a Canceled Session (reason "rescheduled to …") plus normal Attendance on the new date — net consumption is one session, exactly as if it had not moved. A first-class linked "moved-from → moved-to" record was rejected as unnecessary complexity for a solo admin; it would only earn its place if reschedules became frequent and needed reporting.

## Consequences

- Canceled lessons are the canonical "deviation from the schedule" that model B (ADR-0002) persists, while normal weeks stay computed.
- A canceled week never burns a paying student's session — the fairness bug in the boolean model is removed.
