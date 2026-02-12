from __future__ import annotations

from datetime import UTC, datetime, timedelta

from timberline.display import formatAge, formatLastActive, printWorktreeTable
from timberline.models import WorktreeInfo


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


# ─── formatLastActive tests ──────────────────────────────────────────────────


def test_formatLastActive_today():
    # use 1 minute ago to avoid crossing midnight boundary
    t = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    result = formatLastActive(t)
    assert "ago" in result


def test_formatLastActive_yesterday():
    t = (datetime.now(UTC) - timedelta(days=1, hours=12)).isoformat()
    result = formatLastActive(t)
    # should be "Nth Mon YY" format
    assert "ago" not in result
    assert len(result) > 0


def test_formatLastActive_older():
    t = (datetime.now(UTC) - timedelta(days=30)).isoformat()
    result = formatLastActive(t)
    assert "ago" not in result
    assert len(result) > 0


def test_formatLastActive_empty():
    assert formatLastActive("") == ""


def test_formatLastActive_invalid():
    assert formatLastActive("not-a-date") == ""
