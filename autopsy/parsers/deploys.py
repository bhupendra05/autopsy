"""Deploy history parser — supports JSON array or plain text."""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Optional

from autopsy.types import Event, EventKind


def _ts(raw: str) -> Optional[datetime]:
    for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
        try:
            return datetime.strptime(raw[:len(fmt)], fmt)
        except ValueError:
            continue
    return None


def parse_deploys(content: str, source: str = "deploys") -> list[Event]:
    events: list[Event] = []

    # Try JSON first
    try:
        data = json.loads(content)
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict):
                    ts_raw = entry.get("timestamp") or entry.get("time") or entry.get("date") or ""
                    service = entry.get("service") or entry.get("app") or "unknown"
                    version = entry.get("version") or entry.get("tag") or entry.get("sha", "")[:8] or ""
                    status = entry.get("status") or entry.get("result") or "deployed"
                    summary = f"[deploy] {service} {version} → {status}"
                    events.append(Event(
                        timestamp=_ts(str(ts_raw)) if ts_raw else None,
                        kind=EventKind.deploy,
                        source=source,
                        raw=json.dumps(entry),
                        summary=summary,
                    ))
        return events
    except (json.JSONDecodeError, TypeError):
        pass

    # Plain text: one deploy per line
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        ts_match = re.search(r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})", line)
        ts = _ts(ts_match.group(1)) if ts_match else None
        events.append(Event(
            timestamp=ts,
            kind=EventKind.deploy,
            source=source,
            raw=line,
            summary=f"[deploy] {line[:180]}",
        ))

    return events
