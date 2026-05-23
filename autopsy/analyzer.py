"""Core analyzer — feeds parsed events to Opus 4.7 with extended thinking."""
from __future__ import annotations

import json
from typing import Optional

import anthropic

from autopsy.types import (
    ActionItem, Event, ParsedInput, PostMortem,
    RootCause, Severity, TimelineEntry,
)

_MODEL = "claude-opus-4-7"
_SYSTEM = """\
You are an expert Site Reliability Engineer specializing in production incident analysis and post-mortem writing.

You will receive:
- Application logs (errors, warnings, restarts)
- Git commit history (recent changes)
- Deployment history
- Any additional context

Your job is to:
1. Build a precise timeline of what happened
2. Trace the root cause through a step-by-step causal chain
3. Identify contributing factors
4. Assess impact and severity
5. Write a production-quality post-mortem

Think deeply before answering. Trace causality carefully — do not confuse correlation with causation.
Reason through each piece of evidence. Consider what was deployed BEFORE errors appeared.
Consider what changed in the codebase. Think about timing relationships.

Return ONLY valid JSON matching this schema — no markdown, no prose outside JSON:
{
  "title": "string — short incident title",
  "incident_summary": "string — 2-3 sentence summary",
  "severity": "critical|high|medium|low|unknown",
  "duration_estimate": "string or null — e.g. '45 minutes'",
  "timeline": [
    {"timestamp": "string or null", "event": "string", "significance": "string"}
  ],
  "root_cause": {
    "summary": "string — one sentence root cause",
    "chain": ["step 1", "step 2", "..."],
    "confidence": 0.0
  },
  "contributing_factors": ["string"],
  "impact": "string — who/what was affected and how",
  "resolution": "string — how was it resolved or how it could be resolved",
  "action_items": [
    {"priority": "immediate|short-term|long-term", "description": "string", "owner": null}
  ],
  "lessons_learned": ["string"]
}
"""


def _build_prompt(parsed: ParsedInput) -> str:
    sections: list[str] = []

    if parsed.raw_logs:
        # Trim to 8K chars to stay within context efficiently
        sections.append(f"## Application Logs\n```\n{parsed.raw_logs[:8000]}\n```")

    if parsed.raw_git:
        sections.append(f"## Git Commit History\n```\n{parsed.raw_git[:4000]}\n```")

    if parsed.raw_deploys:
        sections.append(f"## Deployment History\n```\n{parsed.raw_deploys[:4000]}\n```")

    if parsed.raw_metrics:
        sections.append(f"## Metrics / Other Context\n```\n{parsed.raw_metrics[:4000]}\n```")

    # Also add structured event summary
    errors = [e for e in parsed.events if e.kind.value in ("log_error", "service_restart")]
    deploys = [e for e in parsed.events if e.kind.value == "deploy"]
    commits = [e for e in parsed.events if e.kind.value == "git_commit"]

    summary_lines = [
        f"## Extracted Event Summary",
        f"- Total error/restart events: {len(errors)}",
        f"- Total deploys: {len(deploys)}",
        f"- Total commits: {len(commits)}",
    ]
    if errors[:5]:
        summary_lines.append("\nFirst error events:")
        for e in errors[:5]:
            summary_lines.append(f"  [{e.timestamp}] {e.summary}")
    if deploys:
        summary_lines.append("\nDeploy events:")
        for d in deploys:
            summary_lines.append(f"  [{d.timestamp}] {d.summary}")

    sections.append("\n".join(summary_lines))

    return "\n\n".join(sections)


def analyze(
    parsed: ParsedInput,
    client: anthropic.Anthropic,
    thinking_budget: int = 8000,
    model: str = _MODEL,
) -> PostMortem:
    prompt = _build_prompt(parsed)

    response = client.messages.create(
        model=model,
        max_tokens=thinking_budget + 4000,
        thinking={"type": "enabled", "budget_tokens": thinking_budget},
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    # Extract thinking summary (first 500 chars)
    thinking_text: Optional[str] = None
    result_text = ""

    for block in response.content:
        if block.type == "thinking":
            thinking_text = block.thinking[:500] + "..." if len(block.thinking) > 500 else block.thinking
        elif block.type == "text":
            result_text = block.text

    # Parse JSON response
    raw = result_text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    data = json.loads(raw)

    timeline = [TimelineEntry(**t) for t in data.get("timeline", [])]
    rc = RootCause(**data["root_cause"])
    actions = [ActionItem(**a) for a in data.get("action_items", [])]

    return PostMortem(
        title=data["title"],
        incident_summary=data["incident_summary"],
        severity=Severity(data.get("severity", "unknown")),
        duration_estimate=data.get("duration_estimate"),
        timeline=timeline,
        root_cause=rc,
        contributing_factors=data.get("contributing_factors", []),
        impact=data["impact"],
        resolution=data["resolution"],
        action_items=actions,
        lessons_learned=data.get("lessons_learned", []),
        thinking_summary=thinking_text,
    )
