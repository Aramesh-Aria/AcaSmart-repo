"""Data layer package: database connection, schema, and migrations.
This package is introduced to modularize the previous monolithic db_helper.
"""

from .settings_repo import (
	set_setting, get_setting,
	_normalize_bool_str, get_setting_bool, set_setting_bool, ensure_bool_setting
)
from .profiles_repo import (
	create_pricing_profile, list_pricing_profiles, get_default_profile,
	set_term_config, get_term_config, get_pricing_profile_by_id,
	apply_profile_to_term, get_term_config_full, set_default_pricing_profile, clear_term_profile
)
from .terms_repo import (
	insert_student_term_if_not_exists, delete_student_term_by_id, get_student_term,
	get_last_term_end_date, get_term_id_by_student_and_class, get_all_terms_for_student_class,
	recalc_term_end_by_id, get_term_dates, get_term_tuition_by_id, get_term_sessions_limit_by_id,
	check_and_set_term_end_by_id, get_all_expired_terms, get_finished_terms_with_future_sessions
)
from .sessions_repo import (
	ensure_term_config, add_session, fetch_sessions_by_class, delete_future_sessions,
	is_class_slot_taken, fetch_students_with_teachers_for_class,
	fetch_students_with_active_terms_for_class, fetch_students_sessions_for_class_on_date,
	has_weekly_time_conflict, has_teacher_weekly_time_conflict, get_session_by_id,
	get_session_count_per_class, get_student_count_per_class, get_session_count_per_student
)
from .attendance_repo import (
	count_attendance, count_attendance_by_term, insert_attendance_with_date,
	delete_attendance, fetch_attendance_by_date, get_term_id_by_student_class_and_date,
	count_present_attendance_for_term
)
from .payments_repo import (
	insert_payment, fetch_payments, get_total_paid_for_term, delete_payment,
	get_terms_for_payment_management, fetch_extra_payments_for_term, get_payment_by_id,
	delete_term_if_no_payments
)
from .reports_repo import (
	get_all_student_terms_with_financials, get_attendance_report_rows,
	get_student_term_summary_rows, fetch_all_contacts, get_teacher_summary_rows
)
from .notifications_repo import (
	get_unnotified_expired_terms, mark_terms_as_notified,
	has_renew_sms_been_sent, mark_renew_sms_sent
)
