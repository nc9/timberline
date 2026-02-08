from __future__ import annotations

from pathlib import Path

from lumberjack.state import (
    addWorktreeToState,
    loadState,
    reconcileState,
    removeWorktreeFromState,
    saveState,
)
from lumberjack.types import StateFile, WorktreeInfo


def test_loadState_missing(tmp_path: Path):
    state = loadState(tmp_path, ".lj")
    assert state.version == 1
    assert state.worktrees == {}


def test_saveState_and_load_roundTrip(tmp_path: Path):
    state = StateFile(
        repo_root=str(tmp_path),
        worktrees={
            "obsidian": {
                "branch": "nik/feature/obsidian",
                "base_branch": "main",
                "type": "feature",
                "created_at": "2026-01-01T00:00:00+00:00",
                "path": str(tmp_path / ".lj" / "obsidian"),
            }
        },
    )
    saveState(tmp_path, ".lj", state)
    loaded = loadState(tmp_path, ".lj")
    assert loaded.worktrees["obsidian"]["branch"] == "nik/feature/obsidian"


def test_addWorktreeToState():
    state = StateFile(repo_root="/repo")
    info = WorktreeInfo(
        name="test",
        branch="nik/feature/test",
        base_branch="main",
        type="feature",
        path="/repo/.lj/test",
        created_at="2026-01-01T00:00:00+00:00",
    )
    new_state = addWorktreeToState(state, info)
    assert "test" in new_state.worktrees
    # original unchanged
    assert "test" not in state.worktrees


def test_removeWorktreeFromState():
    state = StateFile(
        repo_root="/repo",
        worktrees={"a": {"branch": "b", "path": "/repo/.lj/a"}},
    )
    new_state = removeWorktreeFromState(state, "a")
    assert "a" not in new_state.worktrees
    # original unchanged
    assert "a" in state.worktrees


def test_reconcileState_removes_orphans():
    state = StateFile(
        repo_root="/repo",
        worktrees={
            "exists": {"branch": "b", "path": "/repo/.lj/exists"},
            "gone": {"branch": "c", "path": "/repo/.lj/gone"},
        },
    )
    git_wts = [
        {"worktree": "/repo", "branch": "main"},
        {"worktree": "/repo/.lj/exists", "branch": "b"},
    ]
    result = reconcileState(state, git_wts, ".lj")
    assert "exists" in result.worktrees
    assert "gone" not in result.worktrees


def test_reconcileState_adds_untracked():
    state = StateFile(repo_root="/repo", worktrees={})
    git_wts = [
        {"worktree": "/repo", "branch": "main"},
        {"worktree": "/repo/.lj/unknown", "branch": "feat/unknown"},
    ]
    result = reconcileState(state, git_wts, ".lj")
    assert "unknown" in result.worktrees
    assert result.worktrees["unknown"]["branch"] == "feat/unknown"
