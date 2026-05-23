"""Report formatters — terminal (Rich) and Markdown."""
from __future__ import annotations

from autopsy.types import PostMortem, Severity

_SEVERITY_COLOR = {
    Severity.critical: "bold red",
    Severity.high: "red",
    Severity.medium: "yellow",
    Severity.low: "green",
    Severity.unknown: "dim",
}

_SEVERITY_EMOJI = {
    Severity.critical: "🔴",
    Severity.high: "🟠",
    Severity.medium: "🟡",
    Severity.low: "🟢",
    Severity.unknown: "⚪",
}


def print_terminal(pm: PostMortem) -> None:
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich import box
        from rich.text import Text
        console = Console()
    except ImportError:
        print(_to_markdown(pm))
        return

    sev_color = _SEVERITY_COLOR.get(pm.severity, "white")
    sev_emoji = _SEVERITY_EMOJI.get(pm.severity, "⚪")

    console.print()
    console.print(Panel(
        f"[bold]{pm.title}[/bold]\n\n{pm.incident_summary}",
        title=f"[{sev_color}]{sev_emoji} AUTOPSY REPORT — {pm.severity.value.upper()}[/{sev_color}]",
        border_style=sev_color,
        padding=(1, 2),
    ))

    # Timeline
    if pm.timeline:
        console.print("\n[bold cyan]📅 Timeline[/bold cyan]")
        t = Table(show_header=True, box=box.SIMPLE, header_style="bold cyan")
        t.add_column("Time", style="dim", width=20)
        t.add_column("Event", width=45)
        t.add_column("Why It Matters", width=40)
        for entry in pm.timeline:
            t.add_row(
                entry.timestamp or "—",
                entry.event,
                f"[dim]{entry.significance}[/dim]",
            )
        console.print(t)

    # Root cause
    console.print("\n[bold red]🔍 Root Cause[/bold red]")
    console.print(f"  {pm.root_cause.summary}")
    console.print(f"  Confidence: {pm.root_cause.confidence:.0%}")
    console.print("\n  [bold]Causal chain:[/bold]")
    for i, step in enumerate(pm.root_cause.chain, 1):
        console.print(f"  {i}. {step}")

    # Contributing factors
    if pm.contributing_factors:
        console.print("\n[bold yellow]⚠️  Contributing Factors[/bold yellow]")
        for f in pm.contributing_factors:
            console.print(f"  • {f}")

    # Impact + Resolution
    console.print(f"\n[bold]💥 Impact:[/bold] {pm.impact}")
    console.print(f"[bold]✅ Resolution:[/bold] {pm.resolution}")
    if pm.duration_estimate:
        console.print(f"[bold]⏱  Duration:[/bold] {pm.duration_estimate}")

    # Action items
    if pm.action_items:
        console.print("\n[bold green]📋 Action Items[/bold green]")
        for a in pm.action_items:
            badge = {"immediate": "[red]IMMEDIATE[/red]", "short-term": "[yellow]SHORT-TERM[/yellow]"}.get(
                a.priority, "[dim]LONG-TERM[/dim]"
            )
            console.print(f"  {badge}  {a.description}")

    # Lessons
    if pm.lessons_learned:
        console.print("\n[bold blue]💡 Lessons Learned[/bold blue]")
        for l in pm.lessons_learned:
            console.print(f"  • {l}")

    # Thinking snippet
    if pm.thinking_summary:
        console.print(Panel(
            f"[dim]{pm.thinking_summary}[/dim]",
            title="[dim]🧠 Extended Thinking Excerpt[/dim]",
            border_style="dim",
            padding=(0, 1),
        ))
    console.print()


def _to_markdown(pm: PostMortem) -> str:
    lines = [
        f"# {pm.title}",
        f"\n**Severity:** {pm.severity.value.upper()}",
        f"**Duration:** {pm.duration_estimate or 'Unknown'}",
        f"\n## Summary\n{pm.incident_summary}",
        "\n## Timeline",
    ]
    for e in pm.timeline:
        lines.append(f"- **{e.timestamp or '?'}** — {e.event} *(why: {e.significance})*")

    lines += [
        f"\n## Root Cause\n**{pm.root_cause.summary}** (confidence: {pm.root_cause.confidence:.0%})",
        "\n**Causal chain:**",
    ]
    for i, step in enumerate(pm.root_cause.chain, 1):
        lines.append(f"{i}. {step}")

    if pm.contributing_factors:
        lines.append("\n## Contributing Factors")
        for f in pm.contributing_factors:
            lines.append(f"- {f}")

    lines += [
        f"\n## Impact\n{pm.impact}",
        f"\n## Resolution\n{pm.resolution}",
    ]

    if pm.action_items:
        lines.append("\n## Action Items")
        for a in pm.action_items:
            lines.append(f"- [{a.priority.upper()}] {a.description}")

    if pm.lessons_learned:
        lines.append("\n## Lessons Learned")
        for l in pm.lessons_learned:
            lines.append(f"- {l}")

    return "\n".join(lines)


def to_markdown(pm: PostMortem) -> str:
    return _to_markdown(pm)
