import hashlib
from db_helper import get_setting

def hash_password(plain: str) -> str:
    """Return SHA256 hex digest of the input."""
    return hashlib.sha256(plain.encode()).hexdigest()


def format_currency_with_unit(amount: int) -> str:
    unit = get_setting("currency_unit", "تومان")
    if unit == "rial":
        return f"{amount * 10:,} ریال"
    return f"{amount:,} تومان"

def get_currency_unit():
    unit = get_setting("currency_unit", "toman")
    return "تومان" if unit == "toman" else "rial"


def format_currency(amount):
    try:
        formatted = f"{int(amount):,}"
        return f"{formatted} {get_currency_unit()}"
    except:
        return str(amount)
