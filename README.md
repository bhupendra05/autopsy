# autopsy 🔬

> **Feed it your logs. Get back a post-mortem.** Uses Claude Opus 4.7's extended thinking to trace causal chains through logs, deploys, and git history — and writes the post-mortem for you.

[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org)
[![Built on Claude Opus 4.7](https://img.shields.io/badge/built_on-Claude_Opus_4.7-9F5EFA)](https://www.anthropic.com)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## The problem

After a production incident, your team spends hours:

- Collecting logs, metrics, traces from 4 different tools
- Building a timeline: *"what happened first? what triggered what?"*
- Arguing about the root cause
- Writing the post-mortem from scratch at midnight

The hard part isn't gathering data — it's **reasoning through it**. Causality chains like *"service A failed because B was slow because C exhausted the connection pool because D's query was missing an index after the E deploy"* require multi-step inference that current tools don't do.

**That's what extended thinking is for.**

## What it does

```
autopsy analyze --logs app.log --git-log git.log --deploys deploys.json
```

autopsy reads your evidence, then Opus 4.7 reasons step-by-step through the causal chain and outputs:

- ✅ **Root cause** with step-by-step causal chain + confidence score
- ✅ **Timeline** — what happened, in order, with significance of each event
- ✅ **Contributing factors** — what made it worse
- ✅ **Action items** — immediate, short-term, long-term
- ✅ **Draft post-mortem** — ready to paste into your wiki
- ✅ **Extended thinking excerpt** — see exactly how it reasoned

## Demo

Given these inputs:

```
# app.log shows: WARN slow queries at 14:28, ERROR pool exhausted at 14:29, FATAL nil pointer at 14:30
# git.log shows: "fix: remove N+1 query guard" deployed at 14:28
# deploys.json shows: v2.5.0 deployed at 14:28:15Z
```

autopsy outputs:

```
╔══════════════════════════════════════════════════════════╗
║  🔴 AUTOPSY REPORT — CRITICAL                           ║
║  API Server Outage — Connection Pool Exhaustion          ║
╚══════════════════════════════════════════════════════════╝

Summary: A commit in v2.5.0 removed the N+1 query guard in
OrderService.GetOrders, causing each API request to execute
O(n) database queries. Under normal load this exhausted the
20-connection pool within 45 seconds, triggering a cascade
of timeouts, a nil pointer panic, and OOM kills.

📅 Timeline
─────────────────────────────────────────────────────────
14:28:15  v2.5.0 deployed          First deploy containing the bad commit
14:28:45  Slow queries begin        N+1 queries saturating DB connections
14:29:15  Pool exhausted            All 20 connections held by slow queries
14:29:20  Service panics            Nil pointer from half-initialized state
14:31:15  OOM kill                  Memory leak from goroutine accumulation
14:35:00  v2.5.1 hotfix deployed    Reverted the query guard removal

🔍 Root Cause
  Commit a3f1c9d removed the N+1 query guard from OrderService.GetOrders.
  Confidence: 94%

  Causal chain:
  1. v2.5.0 removed batching in GetOrders (commit a3f1c9d)
  2. Each /orders request now fires one DB query per order row
  3. Under load, 20 concurrent requests × avg 15 rows = 300 queries
  4. Connection pool (size=20) exhausted within 45s of deploy
  5. Requests queue → timeout → context deadline exceeded errors
  6. Uninitialized state from timed-out requests → nil pointer panic
  7. Goroutine leak → memory climbs to 94% → OOM kill

📋 Action Items
  [IMMEDIATE]   Revert commit a3f1c9d / deploy v2.5.1 ✓ Done
  [SHORT-TERM]  Add integration test that fails on N+1 queries
  [SHORT-TERM]  Set connection pool size based on p99 query concurrency
  [LONG-TERM]   Add query count alerting to deployment pipeline
```

## Why extended thinking

Standard LLMs guess the root cause from pattern matching. Extended thinking actually **reasons**:

```
🧠 Extended Thinking Excerpt:
"Let me trace the timeline carefully. The first anomaly is slow queries
at 14:28:45, which is 30 seconds after the v2.5.0 deploy at 14:28:15.
The deploy includes commit a3f1c9d which says 'remove N+1 query guard'.
This is almost certainly causal, not coincidental. Let me verify: if
the guard was removed, each call to GetOrders would... [continues for
4000 more tokens of reasoning]"
```

Smaller models confidently blame the wrong thing (e.g., "database was overloaded"). Opus 4.7 traces the chain correctly because it actually reasons through the evidence.

## Install

```bash
pip install autopsy-ai
export ANTHROPIC_API_KEY=sk-ant-...
```

## Quick start

### CLI

```bash
# Basic: logs only
autopsy analyze --logs app.log

# Full: logs + git + deploys
autopsy analyze --logs app.log --git-log git.log --deploys deploys.json

# Output options
autopsy analyze --logs app.log --output markdown > postmortem.md
autopsy analyze --logs app.log --output json | jq .root_cause

# Paste raw context
autopsy analyze --logs app.log --text "Deploy happened at 14:28 UTC, team noticed alerts at 14:32"

# Adjust thinking depth (default: 8000 tokens)
autopsy analyze --logs app.log --thinking-budget 16000
```

### Python

```python
from anthropic import Anthropic
from autopsy import analyze, ParsedInput
from autopsy.parsers import parse_logs, parse_git_log, parse_deploys
from autopsy.report import print_terminal

log_text = open("app.log").read()
git_text = open("git.log").read()

parsed = ParsedInput(
    raw_logs=log_text,
    raw_git=git_text,
    events=parse_logs(log_text) + parse_git_log(git_text),
)

pm = analyze(parsed, Anthropic(), thinking_budget=8000)
print_terminal(pm)

# Access structured data
print(pm.root_cause.summary)
print(pm.root_cause.confidence)
for step in pm.root_cause.chain:
    print(f"  → {step}")
```

### Input formats

| Input | Flag | Format |
|-------|------|--------|
| Application logs | `--logs` | Any text log — autopsy detects ERROR/WARN/FATAL lines |
| Git history | `--git-log` | `git log --oneline` or `git log --format="%H %ad %s" --date=iso-strict` |
| Deploy history | `--deploys` | JSON array or plain text, one deploy per line |
| Metrics / extra | `--metrics` or `--text` | Any text — CPU graphs, alert descriptions, Slack threads |

## Architecture

```
autopsy/
├── cli.py          # Click CLI — autopsy analyze
├── analyzer.py     # Opus 4.7 extended thinking orchestrator
├── types.py        # Pydantic models (Event, PostMortem, RootCause)
├── report.py       # Rich terminal + Markdown output
└── parsers/
    ├── logs.py     # Regex-based error/warn/restart extraction
    ├── git.py      # Git log parser with risky commit detection
    └── deploys.py  # JSON + plain text deploy parser
```

## Use cases

| Scenario | What to feed autopsy |
|----------|----------------------|
| **API outage** | App logs + deploy history |
| **DB performance degradation** | Slow query logs + git log |
| **Memory leak** | App logs with memory metrics + recent commits |
| **Cascading microservice failure** | Logs from each service + deploy timeline |
| **Kubernetes pod crash** | kubectl logs output + recent Helm chart changes |
| **"Unknown" incident** | Everything you have — autopsy figures out what matters |

## License

MIT © [bhupendra05](https://github.com/bhupendra05)

---

*Built because every post-mortem I've written started with 2 hours of log grepping. Now it takes 30 seconds.*
