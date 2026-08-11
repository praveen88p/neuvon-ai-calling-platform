"""Callback time parsing utilities.

Converts various time expressions from Dograh ``gathered_context``
into a proper UTC-aware ``datetime`` suitable for storing in
``scheduled_callbacks.callback_at``.

Dograh agents may return callback_time in many formats:
  - ISO 8601:           "2026-08-11T17:00:00"
  - ISO with TZ:        "2026-08-11T17:00:00+05:30"
  - Human-readable:     "tomorrow 5pm"
  - Time only:          "5:30 PM"
  - Relative:           "in 2 hours"
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from dateutil import parser as dateutil_parser

from app.core.logging import logger


# ── Public API ────────────────────────────────────────────────────────────────


def parse_callback_time(
    raw: str,
    reference_tz_offset_hours: float = 5.5,  # IST default (UTC+5:30)
) -> datetime | None:
    """Parse a raw callback time string into a UTC datetime.

    Returns ``None`` if the string cannot be parsed or resolves to a
    time in the past.

    Args:
        raw: Raw string from gathered_context (e.g. "5pm tomorrow")
        reference_tz_offset_hours: Fallback timezone offset when the
            string has no timezone info. Defaults to IST (UTC+5:30).
    """
    if not raw or not isinstance(raw, str):
        return None

    raw = raw.strip()
    if not raw:
        return None

    # Reference "now" in the target timezone
    tz_offset = timezone(timedelta(hours=reference_tz_offset_hours))
    now_local = datetime.now(tz_offset)

    result = (
        _try_iso(raw)
        or _try_relative(raw, now_local)
        or _try_time_only(raw, now_local)
        or _try_dateutil(raw, now_local)
    )

    if result is None:
        logger.warning("callback_parser.unparseable", raw=raw)
        return None

    # Convert to UTC
    if result.tzinfo is None:
        result = result.replace(tzinfo=tz_offset)
    result_utc = result.astimezone(timezone.utc)

    # Reject if in the past (allow 60-second grace for clock skew)
    now_utc = datetime.now(timezone.utc)
    if result_utc < now_utc - timedelta(seconds=60):
        logger.warning(
            "callback_parser.past_time",
            raw=raw,
            parsed=result_utc.isoformat(),
        )
        return None

    # Cap at 30 days in the future
    if result_utc > now_utc + timedelta(days=30):
        logger.warning(
            "callback_parser.too_far_future",
            raw=raw,
            parsed=result_utc.isoformat(),
        )
        return None

    logger.info(
        "callback_parser.success",
        raw=raw,
        parsed_utc=result_utc.isoformat(),
    )
    return result_utc


def format_for_display(dt: datetime) -> str:
    """Format a UTC datetime for display in IST."""
    ist = timezone(timedelta(hours=5, minutes=30))
    dt_ist = dt.astimezone(ist)
    return dt_ist.strftime("%d %b %Y %I:%M %p IST")


# ── Internal parsers ──────────────────────────────────────────────────────────


def _try_iso(raw: str) -> datetime | None:
    """Try strict ISO 8601 formats first."""
    try:
        # Standard ISO with or without TZ
        return dateutil_parser.isoparse(raw)
    except (ValueError, OverflowError):
        return None


_RELATIVE_PATTERNS = [
    # "in 2 hours", "in 30 minutes", "in 1 day"
    (re.compile(r"in\s+(\d+)\s+(hour|hr)s?", re.I),   "hours"),
    (re.compile(r"in\s+(\d+)\s+(minute|min)s?", re.I), "minutes"),
    (re.compile(r"in\s+(\d+)\s+days?", re.I),          "days"),
    # "2 hours later", "30 minutes later"
    (re.compile(r"(\d+)\s+(hour|hr)s?\s+later", re.I),   "hours"),
    (re.compile(r"(\d+)\s+(minute|min)s?\s+later", re.I), "minutes"),
]

_RELATIVE_KEYWORDS = {
    "now":       timedelta(minutes=5),  # give agent 5 min buffer
    "tonight":   None,                  # handled below
    "tomorrow":  None,
    "day after": None,
}


def _try_relative(raw: str, now_local: datetime) -> datetime | None:
    """Handle relative expressions like 'in 2 hours', 'tomorrow 5pm'."""
    lower = raw.lower()

    # Pure relative offsets
    for pattern, unit in _RELATIVE_PATTERNS:
        m = pattern.search(lower)
        if m:
            amount = int(m.group(1))
            delta = timedelta(**{unit: amount})
            return now_local + delta

    # "tomorrow [time]" or "day after [time]"
    if "day after tomorrow" in lower or "day after" in lower:
        base = now_local + timedelta(days=2)
    elif "tomorrow" in lower:
        base = now_local + timedelta(days=1)
    elif "tonight" in lower:
        base = now_local
    else:
        return None

    # Extract a time component if present
    time_match = _extract_time(lower)
    if time_match is not None:
        h, m = time_match
        return base.replace(hour=h, minute=m, second=0, microsecond=0)
    else:
        # Default to 10am if no time given
        return base.replace(hour=10, minute=0, second=0, microsecond=0)


_TIME_PATTERNS = [
    # "5:30 PM", "17:30"
    re.compile(r"(\d{1,2}):(\d{2})\s*(am|pm)?", re.I),
    # "5 PM", "5pm", "17"
    re.compile(r"(\d{1,2})\s*(am|pm)", re.I),
]


def _extract_time(text: str) -> tuple[int, int] | None:
    """Return (hour_24, minute) from a string, or None."""
    for pat in _TIME_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        groups = m.groups()
        hour = int(groups[0])
        minute = int(groups[1]) if groups[1] and groups[1].isdigit() else 0
        ampm = groups[-1]

        if ampm:
            ampm = ampm.lower()
            if ampm == "pm" and hour != 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
        return hour, minute
    return None


def _try_time_only(raw: str, now_local: datetime) -> datetime | None:
    """Handle bare times like '5pm', '17:30' — assume today or tomorrow."""
    result = _extract_time(raw.lower())
    if result is None:
        return None

    h, m = result
    candidate = now_local.replace(hour=h, minute=m, second=0, microsecond=0)
    # If time has passed today, schedule for tomorrow
    if candidate <= now_local:
        candidate += timedelta(days=1)
    return candidate


def _try_dateutil(raw: str, now_local: datetime) -> datetime | None:
    """Last resort: use dateutil's fuzzy parser."""
    try:
        return dateutil_parser.parse(
            raw,
            fuzzy=True,
            default=now_local,
        )
    except (ValueError, OverflowError, dateutil_parser.ParserError):
        return None
