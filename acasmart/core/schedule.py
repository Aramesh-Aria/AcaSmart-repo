"""Model-B occurrence engine (Phase 2, ADR-0002).

Pure scheduling logic over Shamsi/Jalali dates: a term's lessons fall on a weekly
base pattern (every 7 days from start_date, same weekday). Dates are the app's
canonical "YYYY-MM-DD" Shamsi strings. All arithmetic goes through jdatetime by
converting to Gregorian, adding a timedelta, and converting back (robust across
Jalali month lengths and leap years).
"""
import datetime
import jdatetime


def _to_greg(shamsi_date: str) -> datetime.date:
    return jdatetime.date.fromisoformat(str(shamsi_date).strip()).togregorian()


def _to_shamsi(greg: datetime.date) -> str:
    return jdatetime.date.fromgregorian(date=greg).isoformat()


def days_between(start_shamsi: str, end_shamsi: str) -> int:
    """Signed day count from start to end (end - start). Negative if end precedes start."""
    return (_to_greg(end_shamsi) - _to_greg(start_shamsi)).days


def is_weekly_occurrence(start_shamsi: str, date_shamsi: str) -> bool:
    """True if date_shamsi is start_shamsi or a later same-weekday (every-7-days) date."""
    d = days_between(start_shamsi, date_shamsi)
    return d >= 0 and d % 7 == 0


def occurrence_dates(start_shamsi: str, count: int):
    """The first `count` weekly occurrence dates (Shamsi strings) starting at start_shamsi."""
    if count <= 0:
        return []
    g = _to_greg(start_shamsi)
    return [_to_shamsi(g + datetime.timedelta(days=7 * i)) for i in range(count)]


def add_weeks(start_shamsi: str, weeks: int) -> str:
    """Shamsi date `weeks` weeks after start_shamsi."""
    return _to_shamsi(_to_greg(start_shamsi) + datetime.timedelta(days=7 * weeks))


# Persian weekday names keyed by Gregorian weekday() (Monday=0) — matches the
# attendance window's mapping so class.day strings line up.
_WEEKDAY_FA = {0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه", 3: "پنجشنبه", 4: "جمعه", 5: "شنبه", 6: "یکشنبه"}


def weekday_fa(shamsi_date: str) -> str:
    """Persian weekday name for a Shamsi date."""
    return _WEEKDAY_FA[_to_greg(shamsi_date).weekday()]


def first_on_or_after(shamsi_date: str, weekday_name: str) -> str:
    """First Shamsi date >= shamsi_date whose Persian weekday equals weekday_name.

    Used to snap an enrollment's start_date onto the class's weekly day, so weekly
    occurrences land on the class day. Returns shamsi_date unchanged if weekday_name
    is unknown.
    """
    if weekday_name not in _WEEKDAY_FA.values():
        return shamsi_date
    g = _to_greg(shamsi_date)
    for i in range(7):
        d = g + datetime.timedelta(days=i)
        if _WEEKDAY_FA[d.weekday()] == weekday_name:
            return _to_shamsi(d)
    return shamsi_date
