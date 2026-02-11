from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum

from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from timberline.config import _buildTomlDocument
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
        if wt.archived:
            style = "dim"
        elif status == "clean":
            style = "green"
        else:
            style = "yellow"
        age = formatAge(wt.created_at) if wt.created_at else ""
        name_str = f"[dim]{wt.name}[/dim]" if wt.archived else wt.name
        branch_str = f"[dim]{wt.branch}[/dim]" if wt.archived else wt.branch
        table.add_row(name_str, branch_str, f"[{style}]{status}[/{style}]", age)

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


def printCreateSummary(info: WorktreeInfo, steps: list[str], *, verb: str = "Created") -> None:
    _console.print(f"\n[bold green]✓[/bold green] {verb} worktree: [bold]{info.name}[/bold]")
    _console.print(f"  Branch: {info.branch}")
    _console.print(f"  Path:   {info.path}")
    for step in steps:
        _console.print(f"  [green]✓[/green] {step}")
    _console.print()


def printConfigTable(config: TimberlineConfig) -> None:
    """Rich tree view with field descriptions from schema."""
    tree = Tree("[bold]Timberline Config[/bold]")

    nested = {"init", "env", "submodules", "agent"}
    for name, field_info in TimberlineConfig.model_fields.items():
        if name in nested:
            continue
        val = getattr(config, name)
        if val is None:
            continue
        val_str = val.value if isinstance(val, StrEnum) else str(val)
        desc = field_info.description
        label = f"{name}: [cyan]{val_str}[/cyan]"
        if desc:
            label += f"  [dim]# {desc}[/dim]"
        tree.add(label)

    for section_name in nested:
        sub_config = getattr(config, section_name)
        sub_tree = tree.add(f"[bold]{section_name}[/bold]")
        for name, field_info in sub_config.__class__.model_fields.items():
            val = getattr(sub_config, name)
            if val is None:
                continue
            val_str = str(val)
            desc = field_info.description
            label = f"{name}: [cyan]{val_str}[/cyan]"
            if desc:
                label += f"  [dim]# {desc}[/dim]"
            sub_tree.add(label)

    _console.print(tree)


def printConfigToml(config: TimberlineConfig) -> None:
    """Print config as commented TOML to stdout."""
    from tomlkit import dumps

    doc = _buildTomlDocument(config)
    print(dumps(doc), end="")


# backward compat alias
printConfig = printConfigTable


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
