from __future__ import annotations

from pathlib import Path

from timberline.models import StateFile, WorktreeInfo
from timberline.state import (
    addWorktreeToState,
    loadState,
    reconcileState,
    removeWorktreeFromState,
    saveState,
    updateWorktreeBranch,
)


def test_loadState_missing(tmp_path: Path):
    state = loadState(tmp_path, ".tl")
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
                "path": str(tmp_path / ".tl" / "obsidian"),
            }
        },
    )
    saveState(tmp_path, ".tl", state)
    loaded = loadState(tmp_path, ".tl")
    assert loaded.worktrees["obsidian"]["branch"] == "nik/feature/obsidian"


def test_addWorktreeToState():
    state = StateFile(repo_root="/repo")
    info = WorktreeInfo(
        name="test",
        branch="nik/feature/test",
        base_branch="main",
        type="feature",
        path="/repo/.tl/test",
        created_at="2026-01-01T00:00:00+00:00",
    )
    new_state = addWorktreeToState(state, info)
    assert "test" in new_state.worktrees
    # original unchanged
    assert "test" not in state.worktrees


def test_removeWorktreeFromState():
    state = StateFile(
        repo_root="/repo",
        worktrees={"a": {"branch": "b", "path": "/repo/.tl/a"}},
    )
    new_state = removeWorktreeFromState(state, "a")
    assert "a" not in new_state.worktrees
    # original unchanged
    assert "a" in state.worktrees


def test_reconcileState_removes_orphans():
    state = StateFile(
        repo_root="/repo",
        worktrees={
            "exists": {"branch": "b", "path": "/repo/.tl/exists"},
            "gone": {"branch": "c", "path": "/repo/.tl/gone"},
        },
    )
    git_wts = [
        {"worktree": "/repo", "branch": "main"},
        {"worktree": "/repo/.tl/exists", "branch": "b"},
    ]
    result = reconcileState(state, git_wts, ".tl")
    assert "exists" in result.worktrees
    assert "gone" not in result.worktrees


def test_reconcileState_adds_untracked():
    state = StateFile(repo_root="/repo", worktrees={})
    git_wts = [
        {"worktree": "/repo", "branch": "main"},
        {"worktree": "/repo/.tl/unknown", "branch": "feat/unknown"},
    ]
    result = reconcileState(state, git_wts, ".tl")
    assert "unknown" in result.worktrees
    assert result.worktrees["unknown"]["branch"] == "feat/unknown"


def test_updateWorktreeBranch():
    state = StateFile(
        repo_root="/repo",
        worktrees={"a": {"branch": "old/branch", "path": "/repo/.tl/a"}},
    )
    new_state = updateWorktreeBranch(state, "a", "new/branch")
    assert new_state.worktrees["a"]["branch"] == "new/branch"
    # original unchanged
    assert state.worktrees["a"]["branch"] == "old/branch"


def test_updateWorktreeBranch_missing_name():
    state = StateFile(repo_root="/repo", worktrees={})
    new_state = updateWorktreeBranch(state, "nonexistent", "new/branch")
    assert new_state is state
