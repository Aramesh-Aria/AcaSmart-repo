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
