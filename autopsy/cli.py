"""CLI — `autopsy analyze` command."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

import click

from autopsy.parsers import parse_logs, parse_git_log, parse_deploys
from autopsy.types import ParsedInput
from autopsy.report import print_terminal, to_markdown


@click.group()
def main():
    """autopsy — AI-powered production incident root cause analyzer.

    Uses Claude Opus 4.7 with extended thinking to trace causal chains
    through your logs, deploys, and git history — and writes the post-mortem.
    """


@main.command()
@click.option("--logs", "-l", multiple=True, type=click.Path(exists=True), help="Log file(s)")
@click.option("--git-log", "-g", type=click.Path(exists=True), help="Git log file (git log --oneline or full)")
@click.option("--deploys", "-d", type=click.Path(exists=True), help="Deploy history (JSON or plain text)")
@click.option("--metrics", "-m", type=click.Path(exists=True), help="Metrics/context file")
@click.option("--text", "-t", "extra_text", help="Paste raw text context directly")
@click.option("--output", "-o", type=click.Choice(["terminal", "markdown", "json"]), default="terminal")
@click.option("--thinking-budget", default=8000, show_default=True, help="Extended thinking token budget")
@click.option("--model", default="claude-opus-4-7", show_default=True)
@click.option("--api-key", envvar="ANTHROPIC_API_KEY", help="Anthropic API key")
def analyze(
    logs, git_log, deploys, metrics, extra_text,
    output, thinking_budget, model, api_key,
):
    """Analyze a production incident and generate a post-mortem.

    \b
    Examples:
      autopsy analyze --logs app.log --git-log git.log --deploys deploys.json
      autopsy analyze --logs error.log --text "Deploy at 14:32 UTC"
      cat app.log | autopsy analyze --logs /dev/stdin
    """
    if not api_key:
        click.echo("Error: ANTHROPIC_API_KEY not set. Run: export ANTHROPIC_API_KEY=sk-...", err=True)
        sys.exit(1)

    parsed = ParsedInput()
    all_events = []

    # Parse log files
    log_texts = []
    for log_path in logs:
        content = Path(log_path).read_text(errors="replace")
        log_texts.append(content)
        all_events.extend(parse_logs(content, source=Path(log_path).name))
    parsed.raw_logs = "\n".join(log_texts)

    # Git log
    if git_log:
        content = Path(git_log).read_text(errors="replace")
        parsed.raw_git = content
        all_events.extend(parse_git_log(content))

    # Deploy history
    if deploys:
        content = Path(deploys).read_text(errors="replace")
        parsed.raw_deploys = content
        all_events.extend(parse_deploys(content))

    # Metrics / extra context
    if metrics:
        parsed.raw_metrics = Path(metrics).read_text(errors="replace")

    if extra_text:
        parsed.raw_metrics += f"\n\n## Additional Context\n{extra_text}"

    if not parsed.raw_logs and not parsed.raw_git and not parsed.raw_deploys and not parsed.raw_metrics:
        click.echo("Error: provide at least one input (--logs, --git-log, --deploys, or --text)", err=True)
        sys.exit(1)

    parsed.events = all_events

    import anthropic as _anthropic
    client = _anthropic.Anthropic(api_key=api_key)

    click.echo("🔍 Analyzing incident with extended thinking...", err=True)

    from autopsy.analyzer import analyze as _analyze
    try:
        pm = _analyze(parsed, client, thinking_budget=thinking_budget, model=model)
    except Exception as e:
        click.echo(f"Error during analysis: {e}", err=True)
        sys.exit(1)

    if output == "terminal":
        print_terminal(pm)
    elif output == "markdown":
        click.echo(to_markdown(pm))
    elif output == "json":
        click.echo(pm.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
