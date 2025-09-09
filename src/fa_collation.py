# fa_collation.py
import re
from functools import lru_cache, cmp_to_key
from typing import List, Tuple, Optional

try:
    from PySide6.QtCore import QCollator, QLocale, Qt
except Exception:
    QCollator = None
    QLocale = None
    Qt = None

_FA_ORDER = "ابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی"
_FA_INDEX = {ch: i for i, ch in enumerate(_FA_ORDER)}

def _normalize_fa(s: str) -> str:
    if not s:
        return ""
    s = s.strip()
    trans = str.maketrans({
        "ي": "ی", "ك": "ک",
        "ة": "ه", "ۀ": "ه",
        "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
        "ؤ": "و", "ئ": "ی",
        "‌": "",   # ZWNJ
        "‎": "", "‏": "",  # LRM/RLM
    })
    s = s.translate(trans)
    s = re.sub(r"[\u064B-\u0652\u0670\u0640]", "", s)  # اعراب + کشیده
    return s

@lru_cache(maxsize=10000)
def _norm_cached(s: str) -> str:
    return _normalize_fa(s)

class PersianCollator:
    """مرتب‌ساز فارسی با QCollator (اگر موجود بود) و فالبک سفارشی."""
    def __init__(self) -> None:
        self._coll: Optional["QCollator"] = None
        if QCollator is not None and QLocale is not None:
            try:
                c = QCollator(QLocale("fa_IR"))
                try: c.setCaseSensitivity(Qt.CaseInsensitive)
                except Exception: pass
                try: c.setNumericMode(True)
                except Exception: pass
                self._coll = c
            except Exception:
                self._coll = None

    def compare(self, a: str, b: str) -> int:
        a_n, b_n = _norm_cached(a), _norm_cached(b)
        if self._coll:
            return self._coll.compare(a_n, b_n)
        # فالبک: مقایسه بر اساس نگاشت الفبایی
        ka = tuple(_FA_INDEX.get(ch, 1000 + ord(ch)) for ch in a_n)
        kb = tuple(_FA_INDEX.get(ch, 1000 + ord(ch)) for ch in b_n)
        return (ka > kb) - (ka < kb)

    def contains(self, text: str, pattern: str) -> bool:
        return _norm_cached(pattern) in _norm_cached(text)

    def sort_records(self, records: List[Tuple], name_index: int = 1, tiebreak_index: Optional[int] = None):
        def _cmp(x, y):
            c = self.compare(str(x[name_index]), str(y[name_index]))
            if c != 0:
                return c
            if tiebreak_index is not None:
                tx, ty = x[tiebreak_index], y[tiebreak_index]
                return (tx > ty) - (tx < ty)
            return 0
        return sorted(records, key=cmp_to_key(_cmp))

# singleton آماده برای استفاده ساده
fa_collator = PersianCollator()

# توابع سطح-ماژول (راحت برای import در فایل‌های مختلف)
def sort_records_fa(records, name_index: int = 1, tiebreak_index: Optional[int] = None):
    return fa_collator.sort_records(records, name_index, tiebreak_index)

def contains_fa(text: str, pattern: str) -> bool:
    return fa_collator.contains(text, pattern)

# --- Digit normalization (fa→en) --------------------------------------------
_DIGIT_TRANS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

def nd(s: str) -> str:
    """Normalize digits: Persian/Arabic numerals → ASCII 0-9."""
    return str(s or "").translate(_DIGIT_TRANS)
