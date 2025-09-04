import hashlib
from db_helper import get_setting
from typing import Union  

def hash_password(plain: str) -> str:
    """Return SHA256 hex digest of the input."""
    return hashlib.sha256(plain.encode()).hexdigest()

# -------------------- Currency helpers (backward compatible) --------------------
def _currency_is_rial() -> bool:
    """True if UI/display unit should be Rial.
    Accepts legacy values: 'rial', 'ریال', 'toman', 'تومان', as well as '0'/'1'.
    Convention: 1 => rial, 0 => toman.
    """
    u = str(get_setting("currency_unit", "toman") or "toman").strip().lower()
    return u in {"1", "rial", "ریال"}

def currency_label() -> str:
    return "ریال" if _currency_is_rial() else "تومان"

def format_currency_with_unit(amount_toman: Union[int, float]) -> str:  # ← فقط همین تغییر
    """Format an amount stored in *toman* for display in current UI unit."""
    try:
        if _currency_is_rial():
            disp = int(round(float(amount_toman) * 10))
            return f"{disp:,} ریال"
        else:
            disp = int(round(float(amount_toman)))
            return f"{disp:,} تومان"
    except Exception:
        return str(amount_toman)

def parse_user_amount_to_toman(text: str) -> int:
    """Parse user-entered amount (current UI unit) and return *toman* for DB."""
    if text is None:
        return 0
    s = str(text).replace(",", "").strip()
    if not s:
        return 0
    try:
        val = float(s)
    except ValueError:
        import re as _re
        digits = ''.join(_re.findall(r"\d+", s)) or "0"
        val = float(digits)
    if _currency_is_rial():
        val = val / 10.0
    return int(round(val))

def get_currency_unit():
    """Legacy compatibility: returns the *label* ('ریال' or 'تومان')."""
    return currency_label()

def format_currency(amount):
    """Legacy compatibility: `amount` is *toman*; append label by current UI."""
    try:
        if _currency_is_rial():
            disp = int(round(float(amount) * 10))
        else:
            disp = int(round(float(amount)))
        formatted = f"{disp:,}"
        return f"{formatted} {currency_label()}"
    except Exception:
        return str(amount)
