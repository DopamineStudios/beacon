import re
from datetime import datetime, timedelta, timezone
from typing import Optional


def duration_to_seconds(duration_str: str) -> int:
    """Parse a compact duration string into a total number of seconds.

    Args:
        duration_str: Human-readable duration string (for example "2h30m").

    Returns:
        int: Computed Unix timestamp/seconds value.
    """
    total_seconds = 0
    patterns = {
        'mon': 2592000,
        'w': 604800,
        'd': 86400,
        'h': 3600,
        'm': 60,
        's': 1
    }

    matches = re.findall(r'(\d+)\s*(mon|w|d|h|m|s)', duration_str.lower())

    for amount, unit in matches:
        total_seconds += int(amount) * patterns[unit]

    return total_seconds

def now_plus_seconds_unix(seconds: int) -> int:
    """Return the future Unix timestamp for now plus the given seconds.

    Args:
        seconds: Duration in seconds.

    Returns:
        int: Computed Unix timestamp/seconds value.
    """
    future_dt = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    return int(future_dt.timestamp())