"""Log file parser — extracts ERROR/WARN lines with optional timestamp detection."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from autopsy.types import Event, EventKind

# Common timestamp patterns in log files
_TS_PATTERNS = [
    # 2024-01-15T14:32:01.123Z  (ISO 8601)
    r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)",
    # Jan 15 14:32:01 (syslog)
    r"([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})",
    # 15/Jan/2024:14:32:01 (nginx)
    r"(\d{2}/[A-Z][a-z]{2}/\d{4}:\d{2}:\d{2}:\d{2})",
]

_ERROR_PATTERN = re.compile(r"\b(ERROR|FATAL|CRITICAL|EXCEPTION|TRACEBACK|panic|segfault)\b", re.IGNORECASE)
_WARN_PATTERN = re.compile(r"\b(WARN|WARNING)\b", re.IGNORECASE)
_RESTART_PATTERN = re.compile(r"\b(restart|restarted|started|stopped|killed|OOM|out of memory)\b", re.IGNORECASE)


def _parse_timestamp(line: str) -> Optional[datetime]:
    for pattern in _TS_PATTERNS:
        m = re.search(pattern, line)
        if m:
            raw = m.group(1)
            for fmt in [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%b %d %H:%M:%S",
            ]:
                try:
                    return datetime.strptime(raw[:len(fmt)], fmt)
                except ValueError:
                    continue
    return None


def parse_logs(content: str, source: str = "logs") -> list[Event]:
    events: list[Event] = []
    lines = content.splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        ts = _parse_timestamp(line)
        summary = line[:200]  # cap length

        if _ERROR_PATTERN.search(line):
            events.append(Event(
                timestamp=ts,
                kind=EventKind.log_error,
                source=source,
                raw=line,
                summary=summary,
            ))
        elif _WARN_PATTERN.search(line):
            events.append(Event(
                timestamp=ts,
                kind=EventKind.log_warn,
                source=source,
                raw=line,
                summary=summary,
            ))
        elif _RESTART_PATTERN.search(line):
            events.append(Event(
                timestamp=ts,
                kind=EventKind.service_restart,
                source=source,
                raw=line,
                summary=summary,
            ))

    return events
