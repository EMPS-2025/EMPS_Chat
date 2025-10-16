from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Dict, Optional

MONTH_LOOKUP = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

ISO_DATE_RE = re.compile(r"(20\d{2})-(\d{2})-(\d{2})")
ISO_MONTH_RE = re.compile(r"(20\d{2})-(\d{2})")
HOUR_RANGE_RE = re.compile(r"(\d{1,2})\s*(?:-|to|–)\s*(\d{1,2})")


def _normalise_hours(text: str) -> Optional[Dict[str, int]]:
    match = HOUR_RANGE_RE.search(text)
    if not match:
        return None
    start = int(match.group(1))
    end = int(match.group(2))
    if end <= start:
        end = start + 1
    return {"start_hour": start, "end_hour": end}


def _normalise_date(text: str, today: Optional[date]) -> Dict[str, str]:
    if today is None:
        today = date.today()
    lower = text.lower()
    if "yesterday" in lower:
        return {"date": (today - timedelta(days=1)).isoformat()}
    if "today" in lower:
        return {"date": today.isoformat()}

    match = ISO_DATE_RE.search(text)
    if match:
        return {"date": f"{match.group(1)}-{match.group(2)}-{match.group(3)}"}

    match_month = ISO_MONTH_RE.search(text)
    if match_month:
        return {"month": f"{match_month.group(1)}-{match_month.group(2)}"}

    for name, month_index in MONTH_LOOKUP.items():
        if name in lower:
            year_match = re.search(r"20\d{2}", lower)
            if year_match:
                month = month_index
                return {"month": f"{year_match.group(0)}-{month:02d}"}

    return {}


def parse_message(message: str, *, today: Optional[date] = None) -> Dict[str, object]:
    lower = message.lower()
    market = "DAM"
    if "gdam" in lower:
        market = "GDAM"
    elif "rtm" in lower:
        market = "RTM"

    params: Dict[str, object] = {"market": market, "start_hour": 0, "end_hour": 24, "weighted": False}

    hours = _normalise_hours(lower)
    if hours:
        params.update(hours)

    params.update(_normalise_date(message, today))

    if "weight" in lower or "volume" in lower:
        params["weighted"] = True

    if "min" in lower:
        params["aggregate"] = "min"
    elif "max" in lower:
        params["aggregate"] = "max"
    else:
        params["aggregate"] = "avg"

    return params


__all__ = ["parse_message"]
