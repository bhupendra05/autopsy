"""Git log parser — extracts commits from `git log --oneline --date=iso` output."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from autopsy.types import Event, EventKind

# git log --format="%H %ad %s" --date=iso-strict
_GIT_FULL = re.compile(
    r"([0-9a-f]{7,40})\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^\s]*)\s+(.*)"
)
# git log --oneline
_GIT_ONELINE = re.compile(r"([0-9a-f]{7,40})\s+(.*)")

# Keywords that suggest risky changes
_RISKY = re.compile(
    r"\b(migration|rollback|revert|hotfix|fix|emergency|critical|breaking|remove|delete|drop|rename)\b",
    re.IGNORECASE,
)


def _parse_ts(raw: str) -> Optional[datetime]:
    for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"]:
        try:
            return datetime.strptime(raw[:19], fmt[:len(raw[:19])])
        except ValueError:
            continue
    return None


def parse_git_log(content: str, source: str = "git") -> list[Event]:
    events: list[Event] = []

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue

        ts: Optional[datetime] = None
        message = line

        m = _GIT_FULL.match(line)
        if m:
            sha, date_str, message = m.group(1), m.group(2), m.group(3)
            ts = _parse_ts(date_str)
        else:
            m2 = _GIT_ONELINE.match(line)
            if m2:
                message = m2.group(2)

        if _RISKY.search(message):
            summary = f"[risky commit] {message[:160]}"
        else:
            summary = f"[commit] {message[:160]}"

        events.append(Event(
            timestamp=ts,
            kind=EventKind.git_commit,
            source=source,
            raw=line,
            summary=summary,
        ))

    return events
