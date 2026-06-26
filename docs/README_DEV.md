Developer guide: Data layer refactor

Overview
- The monolithic db_helper.py has been modularized into domain-specific repos under src/data/.
- Connection and PRAGMAs are centralized in data/db.py.
- Schema and migrations live in data/schema.py and data/migrations.py.

Key modules
- data/db.py: get_connection (sqlite3.Row, WAL, foreign_keys=ON, synchronous=NORMAL)
- data/schema.py: create_tables()
- data/migrations.py: migration helpers (idempotent)
- data/settings_repo.py: settings getters/setters and boolean helpers
- data/profiles_repo.py: pricing profiles and term config helpers
- data/terms_repo.py: term creation/queries and end-date checks
- data/sessions_repo.py: session helpers (including delete_session)
- data/attendance_repo.py: attendance helpers
- data/payments_repo.py: payments helpers and delete_term_if_no_payments
- data/reports_repo.py: reporting helpers for UI windows
- data/notifications_repo.py: notification-related queries
- data/classes_repo.py, data/teachers_repo.py, data/teacher_instruments_repo.py, data/students_repo.py: CRUD/read helpers for UI

Migration guide (was → now)
- from db_helper import add_session → from data.sessions_repo import add_session
- from db_helper import delete_session → from data.sessions_repo import delete_session
- from db_helper import insert_payment → from data.payments_repo import insert_payment
- from db_helper import get_total_paid_for_term → from data.payments_repo import get_total_paid_for_term
- from db_helper import get_all_student_terms_with_financials → from data.reports_repo import get_all_student_terms_with_financials
- from db_helper import mark_terms_as_notified → from data.notifications_repo import mark_terms_as_notified
- from db_helper import get_setting / set_setting → from data.settings_repo import get_setting / set_setting
- from db_helper import create_tables → from data.schema import create_tables
- from db_helper import get_connection → from data.db import get_connection

Note: db_helper.py is retired and will raise a RuntimeError on import. Use data/* modules instead.

Usage mapping and modernization
- Generate function→module map: python3 tools/build_data_export_map.py (writes artifacts/data_export_map.json)
- Rewrite UI imports: python3 tools/modernize_ui_imports.py

Smoke checks
- Step 6: python3 tools/smoke_check_step6.py
- Step 7: python3 tools/smoke_check_step7.py

CI guard (optional)
- python3 tools/assert_no_db_helper_imports.py → exits non-zero if any db_helper import remains.
