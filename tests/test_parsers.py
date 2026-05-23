"""Tests for log/git/deploy parsers — no API key required."""
from autopsy.parsers import parse_logs, parse_git_log, parse_deploys
from autopsy.types import EventKind


def test_parse_logs_extracts_errors():
    log = """
2026-05-24T14:29:15Z ERROR database connection pool exhausted
2026-05-24T14:29:20Z FATAL unhandled panic: nil pointer
2026-05-24T14:00:01Z INFO  app started
"""
    events = parse_logs(log)
    error_events = [e for e in events if e.kind == EventKind.log_error]
    assert len(error_events) == 2, f"Expected 2 errors, got {len(error_events)}"


def test_parse_logs_extracts_restarts():
    log = "2026-05-24T14:29:20Z INFO service restarted by supervisor\n"
    events = parse_logs(log)
    restarts = [e for e in events if e.kind == EventKind.service_restart]
    assert len(restarts) == 1


def test_parse_git_log_extracts_commits():
    git = """a3f1c9d fix: remove N+1 query guard
b2e8d7a feat: add pagination
"""
    events = parse_git_log(git)
    assert len(events) == 2
    assert all(e.kind == EventKind.git_commit for e in events)


def test_parse_deploys_json():
    import json
    deploys = json.dumps([
        {"timestamp": "2026-05-24T14:28:15Z", "service": "api", "version": "v2.5.0", "status": "success"}
    ])
    events = parse_deploys(deploys)
    assert len(events) == 1
    assert events[0].kind == EventKind.deploy
    assert "v2.5.0" in events[0].summary


def test_parse_deploys_plaintext():
    events = parse_deploys("2026-05-24 14:28:15 Deployed api-server v2.5.0\n")
    assert len(events) == 1
    assert events[0].kind == EventKind.deploy
