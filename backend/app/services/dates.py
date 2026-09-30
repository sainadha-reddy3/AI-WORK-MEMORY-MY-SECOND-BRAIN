"""
Understanding time in questions.

"What did I do yesterday?" should look at yesterday's memories, not
search for the word "yesterday". This module finds a time expression,
turns it into a date range, and returns the rest of the question.

Deliberately rule-based: every range it produces is predictable, and
the answer always states which range was used.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import settings


@dataclass
class DateRange:
    since: date
    until: date
    label: str       # e.g. "yesterday (Sep 29, 2026)"
    remaining: str   # the question with the time phrase removed


def local_today() -> date:
    """Today in the user's timezone — not the server's UTC clock."""
    return datetime.now(ZoneInfo(settings.timezone)).date()


MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
MONTH = (
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|"
    r"aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
)


def _fmt(d: date) -> str:
    return f"{d:%b} {d.day}, {d.year}"


def _span(a: date, b: date) -> str:
    return _fmt(a) if a == b else f"{_fmt(a)} – {_fmt(b)}"


def _month_end(year: int, month: int) -> date:
    first_next = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return first_next - timedelta(days=1)


def _recent_year(month: int, day: int, today: date) -> int:
    """The most recent year in which month/day is not in the future."""
    try:
        candidate = date(today.year, month, day)
    except ValueError:
        return today.year - 1
    return today.year if candidate <= today else today.year - 1


def parse_date_range(text: str, today: date | None = None) -> DateRange | None:
    """Find the first time expression in `text` and return its date range."""
    today = today or local_today()
    lower = text.lower()

    def build(m: re.Match, since: date, until: date, name: str) -> DateRange:
        until = min(until, today)
        remaining = re.sub(r"\s{2,}", " ", (text[: m.start()] + " " + text[m.end():])).strip()
        return DateRange(since, until, f"{name} ({_span(since, until)})", remaining)

    if m := re.search(r"\bday before yesterday\b", lower):
        d = today - timedelta(days=2)
        return build(m, d, d, "the day before yesterday")

    # Telugu "ninna / నిన్న", Hindi "kal / कल". (Hindi "kal" can also mean
    # tomorrow, but questions about recorded work are about the past.)
    if m := re.search(r"\byesterday\b|\bninna\b|నిన్న|\bkal\b|कल", lower):
        d = today - timedelta(days=1)
        return build(m, d, d, "yesterday")

    if m := re.search(
        r"\btoday\b|\bthis (?:morning|afternoon|evening)\b|\btonight\b|"
        r"\beeroju\b|\bivvala\b|ఈ ?రోజు|\baaj\b|आज",
        lower,
    ):
        return build(m, today, today, "today")

    if m := re.search(r"\b(?:last|past) (\d{1,3}) days?\b", lower):
        n = max(1, int(m.group(1)))
        return build(m, today - timedelta(days=n - 1), today, f"the last {n} days")

    if m := re.search(r"\b(?:last|past) (\d{1,2}) weeks?\b", lower):
        n = max(1, int(m.group(1)))
        return build(m, today - timedelta(days=7 * n - 1), today, f"the last {n} weeks")

    monday = today - timedelta(days=today.weekday())

    if m := re.search(r"\bthis week\b", lower):
        return build(m, monday, today, "this week")

    if m := re.search(r"\b(?:last|previous) week\b", lower):
        return build(m, monday - timedelta(days=7), monday - timedelta(days=1), "last week")

    if m := re.search(r"\bthis month\b", lower):
        return build(m, today.replace(day=1), today, "this month")

    if m := re.search(r"\b(?:last|previous) month\b", lower):
        end = today.replace(day=1) - timedelta(days=1)
        return build(m, end.replace(day=1), end, "last month")

    if m := re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", lower):
        try:
            d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return build(m, d, d, "that day")
        except ValueError:
            pass

    # "Sep 20", "on September 20th, 2026"
    if m := re.search(rf"\b(?:on )?({MONTH})\.? (\d{{1,2}})(?:st|nd|rd|th)?\b(?:,? (\d{{4}}))?", lower):
        month, day = MONTHS[m.group(1)[:3]], int(m.group(2))
        year = int(m.group(3)) if m.group(3) else _recent_year(month, day, today)
        try:
            d = date(year, month, day)
            return build(m, d, d, "that day")
        except ValueError:
            pass

    # "20 Sep", "on 20th September"
    if m := re.search(rf"\b(?:on )?(\d{{1,2}})(?:st|nd|rd|th)? ({MONTH})\b(?:,? (\d{{4}}))?", lower):
        day, month = int(m.group(1)), MONTHS[m.group(2)[:3]]
        year = int(m.group(3)) if m.group(3) else _recent_year(month, day, today)
        try:
            d = date(year, month, day)
            return build(m, d, d, "that day")
        except ValueError:
            pass

    # "in September", "during March 2026" — requires "in"/"during", so
    # words like "may" in "I may have" are never mistaken for a month.
    if m := re.search(rf"\b(?:in|during) ({MONTH})\b(?: (\d{{4}}))?", lower):
        month = MONTHS[m.group(1)[:3]]
        year = int(m.group(2)) if m.group(2) else (today.year if month <= today.month else today.year - 1)
        return build(m, date(year, month, 1), _month_end(year, month), "that month")

    return None