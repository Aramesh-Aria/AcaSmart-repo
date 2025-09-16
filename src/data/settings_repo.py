import logging
from data.db import get_connection

logger = logging.getLogger(__name__)


def set_setting(key, value):
	"""Insert or update a setting key/value pair."""
	with get_connection() as conn:
		conn.execute(
			"REPLACE INTO settings (key, value) VALUES (?, ?)",
			(key, str(value))
		)
		conn.commit()


def get_setting(key, default=None):
	"""Retrieve a setting value by key, or return default."""
	with get_connection() as conn:
		c = conn.cursor()
		c.execute("SELECT value FROM settings WHERE key = ?", (key,))
		row = c.fetchone()
		return row[0] if row else default

# --- Boolean settings helpers (store as "0"/"1") ---

def _normalize_bool_str(s: str) -> bool:
	if s is None:
		return False
	s = str(s).strip().lower()
	return s in {"1", "true", "yes", "on", "فعال", "faal", "enable", "enabled"}


def get_setting_bool(key: str, default: bool = False) -> bool:
	raw = get_setting(key, None)
	if raw is None:
		return default
	s = str(raw).strip().lower()
	if s in {"1", "true", "yes", "on", "فعال", "faal", "enable", "enabled"}:
		return True
	if s in {"0", "false", "no", "off", "غیرفعال", "gheyre faal", "disable", "disabled"}:
		return False
	# مقدار ناشناخته: به‌صورت محافظه‌کارانه default
	return default


def set_setting_bool(key: str, value: bool):
	set_setting(key, "1" if bool(value) else "0")


def ensure_bool_setting(key: str, default: bool = False):
	"""
	مهاجرت نرم: اگر مقدار فعلی هنوز «رشته‌ی فارسی/لاتین» باشد،
	آن را به 0/1 تبدیل می‌کند. اگر مقدار وجود نداشت، default ست می‌شود.
	"""
	raw = get_setting(key, None)
	if raw is None:
		set_setting_bool(key, default)
		return
	# اگر قبلاً 0/1 بوده، کاری نکن
	if str(raw).strip() in {"0", "1"}:
		return
	# تبدیلِ هر چیز دیگری به 0/1
	set_setting_bool(key, _normalize_bool_str(raw))
