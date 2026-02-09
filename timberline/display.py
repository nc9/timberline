from __future__ import annotations

import json
from datetime import UTC, datetime

from rich.console import Console
from rich.table import Table

from timberline.models import TimberlineConfig, WorktreeInfo

_console = Console(stderr=True)
_stdout = Console()


def printWorktreeTable(worktrees: list[WorktreeInfo]) -> None:
    if not worktrees:
        _console.print("[dim]No worktrees found[/dim]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("Branch")
    table.add_column("Status")
    table.add_column("Age")

    for wt in worktrees:
        status = wt.status or "clean"
        style = "green" if status == "clean" else "yellow"
        age = formatAge(wt.created_at) if wt.created_at else ""
        table.add_row(wt.name, wt.branch, f"[{style}]{status}[/{style}]", age)

    _console.print(table)


def printWorktreeJson(worktrees: list[WorktreeInfo]) -> None:
    data = [
        {
            "name": wt.name,
            "branch": wt.branch,
            "base_branch": wt.base_branch,
            "type": wt.type,
            "path": wt.path,
            "created_at": wt.created_at,
            "status": wt.status,
        }
        for wt in worktrees
    ]
    _stdout.print(json.dumps(data, indent=2))


def printWorktreePaths(worktrees: list[WorktreeInfo]) -> None:
    for wt in worktrees:
        print(wt.path)


def printStatusList(worktrees: list[WorktreeInfo]) -> None:
    for wt in worktrees:
        status = wt.status or "clean"
        icon = "[green]✓[/green]" if status == "clean" else "[yellow]✗[/yellow]"
        ahead_behind = ""
        if wt.ahead or wt.behind:
            parts = []
            if wt.ahead:
                parts.append(f"↑{wt.ahead}")
            if wt.behind:
                parts.append(f"↓{wt.behind}")
            ahead_behind = " ".join(parts)
        _console.print(f"  {icon} {wt.name:<20} {status:<12} {ahead_behind}")


def printCreateSummary(info: WorktreeInfo, steps: list[str]) -> None:
    _console.print(f"\n[bold green]✓[/bold green] Created worktree: [bold]{info.name}[/bold]")
    _console.print(f"  Branch: {info.branch}")
    _console.print(f"  Path:   {info.path}")
    for step in steps:
        _console.print(f"  [green]✓[/green] {step}")
    _console.print()


def printConfig(config: TimberlineConfig) -> None:
    _console.print("[bold]Timberline Config[/bold]")
    _console.print(f"  worktree_dir:    {config.worktree_dir}")
    _console.print(f"  branch_template: {config.branch_template}")
    _console.print(f"  user:            {config.user}")
    _console.print(f"  default_type:    {config.default_type}")
    _console.print(f"  base_branch:     {config.base_branch}")
    _console.print(f"  naming_scheme:   {config.naming_scheme.value}")
    _console.print(f"  init.auto_init:  {config.init.auto_init}")
    _console.print(f"  env.auto_copy:   {config.env.auto_copy}")


def printError(msg: str) -> None:
    _console.print(f"[bold red]✗[/bold red] {msg}", style="red")


def printSuccess(msg: str) -> None:
    _console.print(f"[bold green]✓[/bold green] {msg}")


def printWarning(msg: str) -> None:
    _console.print(f"[bold yellow]![/bold yellow] {msg}")


def formatAge(iso_timestamp: str) -> str:
    if not iso_timestamp:
        return ""
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        now = datetime.now(UTC)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        delta = now - dt
        seconds = int(delta.total_seconds())

        if seconds < 60:
            return "just now"
        if seconds < 3600:
            m = seconds // 60
            return f"{m}m ago"
        if seconds < 86400:
            h = seconds // 3600
            return f"{h}h ago"
        days = seconds // 86400
        return f"{days}d ago"
    except (ValueError, TypeError):
        return ""


def confirm(msg: str, default: bool = True) -> bool:
    """Simple y/n prompt."""
    suffix = " [Y/n]: " if default else " [y/N]: "
    try:
        response = input(msg + suffix).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    if not response:
        return default
    return response in ("y", "yes")
