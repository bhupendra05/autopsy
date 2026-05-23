"""Pydantic models for autopsy — incident analysis data structures."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    unknown = "unknown"


class EventKind(str, Enum):
    log_error = "log_error"
    log_warn = "log_warn"
    deploy = "deploy"
    git_commit = "git_commit"
    metric_spike = "metric_spike"
    service_restart = "service_restart"
    other = "other"


class Event(BaseModel):
    timestamp: Optional[datetime] = None
    kind: EventKind
    source: str                    # which file/input this came from
    raw: str                       # original line / text
    summary: str                   # short description


class ParsedInput(BaseModel):
    events: list[Event] = Field(default_factory=list)
    raw_logs: str = ""
    raw_git: str = ""
    raw_deploys: str = ""
    raw_metrics: str = ""


class TimelineEntry(BaseModel):
    timestamp: Optional[str] = None
    event: str
    significance: str              # why this matters


class RootCause(BaseModel):
    summary: str
    chain: list[str]               # step-by-step causal chain
    confidence: float              # 0.0 – 1.0


class ActionItem(BaseModel):
    priority: str                  # immediate / short-term / long-term
    description: str
    owner: Optional[str] = None


class PostMortem(BaseModel):
    title: str
    incident_summary: str
    severity: Severity
    duration_estimate: Optional[str] = None
    timeline: list[TimelineEntry]
    root_cause: RootCause
    contributing_factors: list[str]
    impact: str
    resolution: str
    action_items: list[ActionItem]
    lessons_learned: list[str]
    thinking_summary: Optional[str] = None   # excerpt from extended thinking
