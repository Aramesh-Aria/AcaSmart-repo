# Lightweight guardrails over history, not an audit ledger

AcaSmart protects recorded history with two cheap rules rather than a formal Adjustment/audit system: (1) a Term cannot be deleted once it has any Tuition Payment, Extra Payment, or Attendance — deletion is only for empty setup mistakes; (2) editing a Term that already has history (changing tuition or session limit) is permitted but requires a confirmation warning, since it retroactively changes figures a parent may already have seen.

We deliberately rejected a first-class "Adjustment" entity with a per-change audit trail. AcaSmart is operated by a single admin who knows why every change was made; an audit ledger answers "who changed this and why?", a question that only matters with multiple users or staff accountability. If the app later gains multiple operators, revisit this and introduce real adjustment records.

## Consequences

- The "Adjustment" term is removed from the glossary.
- `delete_term_if_no_payments` must also check attendance before deleting (today it checks payments only — a history-loss bug).
