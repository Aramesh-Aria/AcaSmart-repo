# Term completion is a derived status, not a frozen lock

A Term is "complete" when its recorded attendance count reaches its session limit — a derived, reversible status, not a one-way lock. Completed Terms stay visible and editable through a history view; editing past attendance simply recomputes completion. A completion date is kept for reporting, but it is maintained automatically, not a trapdoor.

The prior design set a permanent `end_date` on completion with no code path back to active, then hid the Term from the attendance page and wrote a one-shot "renewal SMS sent" flag even when the send failed. A single transient failure (e.g. missing SMS credentials) therefore froze and hid a Term forever, with no way to correct past sessions or resend the reminder. Treating completion as derived removes the locked state — and the entire class of bugs around escaping it.

## Consequences

- Renewal reminders are recorded as sent only on genuine provider success and remain resendable via an explicit action until then (see the Renewal Reminder definition in CONTEXT.md — the code must be brought to match it).
- "Active" must still be representable for the one-active-term rule and schedule computation; a maintained completion marker is acceptable as long as it can return to active when records change.
