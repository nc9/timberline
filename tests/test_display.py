from __future__ import annotations

from datetime import UTC, datetime, timedelta

from timberline.display import formatAge, printWorktreeTable
from timberline.types import WorktreeInfo


def test_formatAge_just_now():
    now = datetime.now(UTC).isoformat()
    assert formatAge(now) == "just now"


def test_formatAge_minutes():
    t = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    assert formatAge(t) == "5m ago"


def test_formatAge_hours():
    t = (datetime.now(UTC) - timedelta(hours=3)).isoformat()
    assert formatAge(t) == "3h ago"


def test_formatAge_days():
    t = (datetime.now(UTC) - timedelta(days=7)).isoformat()
    assert formatAge(t) == "7d ago"


def test_formatAge_empty():
    assert formatAge("") == ""


def test_formatAge_invalid():
    assert formatAge("not-a-date") == ""


def test_printWorktreeTable_no_worktrees(capsys):
    # just ensure no crash
    printWorktreeTable([])


def test_printWorktreeTable_with_data():
    wt = WorktreeInfo(
        name="obsidian",
        branch="nik/feature/obsidian",
        base_branch="main",
        type="feature",
        path="/repo/.tl/obsidian",
        status="clean",
    )
    # should not crash
    printWorktreeTable([wt])
