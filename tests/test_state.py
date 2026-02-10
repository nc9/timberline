from __future__ import annotations

from pathlib import Path

from timberline.models import StateFile, WorktreeInfo, getWorktreeBasePath
from timberline.state import (
    addWorktreeToState,
    loadState,
    reconcileState,
    removeWorktreeFromState,
    saveState,
    updateWorktreeBranch,
)


def test_loadState_missing():
    state = loadState("testproj", Path("/repo"))
    assert state.version == 1
    assert state.worktrees == {}


def test_saveState_and_load_roundTrip(tl_home: Path):
    project = "roundtrip"
    wt_base = str(getWorktreeBasePath(project))
    state = StateFile(
        repo_root="/repo",
        worktrees={
            "obsidian": {
                "branch": "nik/feature/obsidian",
                "base_branch": "main",
                "type": "feature",
                "created_at": "2026-01-01T00:00:00+00:00",
                "path": f"{wt_base}/obsidian",
            }
        },
    )
    saveState(project, state)
    loaded = loadState(project)
    assert loaded.worktrees["obsidian"]["branch"] == "nik/feature/obsidian"


def test_addWorktreeToState():
    state = StateFile(repo_root="/repo")
    info = WorktreeInfo(
        name="test",
        branch="nik/feature/test",
        base_branch="main",
        type="feature",
        path="/global/.timberline/projects/repo/worktrees/test",
        created_at="2026-01-01T00:00:00+00:00",
    )
    new_state = addWorktreeToState(state, info)
    assert "test" in new_state.worktrees
    # original unchanged
    assert "test" not in state.worktrees


def test_removeWorktreeFromState():
    state = StateFile(
        repo_root="/repo",
        worktrees={"a": {"branch": "b", "path": "/global/worktrees/a"}},
    )
    new_state = removeWorktreeFromState(state, "a")
    assert "a" not in new_state.worktrees
    # original unchanged
    assert "a" in state.worktrees


def test_reconcileState_removes_orphans(tl_home: Path):
    wt_base = str(getWorktreeBasePath("myproj"))
    state = StateFile(
        repo_root="/repo",
        worktrees={
            "exists": {"branch": "b", "path": f"{wt_base}/exists"},
            "gone": {"branch": "c", "path": f"{wt_base}/gone"},
        },
    )
    git_wts = [
        {"worktree": "/repo", "branch": "main"},
        {"worktree": f"{wt_base}/exists", "branch": "b"},
    ]
    result = reconcileState(state, git_wts, "myproj")
    assert "exists" in result.worktrees
    assert "gone" not in result.worktrees


def test_reconcileState_adds_untracked(tl_home: Path):
    wt_base = str(getWorktreeBasePath("myproj"))
    state = StateFile(repo_root="/repo", worktrees={})
    git_wts = [
        {"worktree": "/repo", "branch": "main"},
        {"worktree": f"{wt_base}/unknown", "branch": "feat/unknown"},
    ]
    result = reconcileState(state, git_wts, "myproj")
    assert "unknown" in result.worktrees
    assert result.worktrees["unknown"]["branch"] == "feat/unknown"


def test_reconcileState_legacy_prefix(tl_home: Path):
    """Backward compat: recognizes worktrees in old .tl/ dir."""
    state = StateFile(repo_root="/repo", worktrees={})
    git_wts = [
        {"worktree": "/repo", "branch": "main"},
        {"worktree": "/repo/.tl/legacy", "branch": "feat/legacy"},
    ]
    result = reconcileState(state, git_wts, "myproj")
    assert "legacy" in result.worktrees


def test_updateWorktreeBranch():
    state = StateFile(
        repo_root="/repo",
        worktrees={"a": {"branch": "old/branch", "path": "/global/worktrees/a"}},
    )
    new_state = updateWorktreeBranch(state, "a", "new/branch")
    assert new_state.worktrees["a"]["branch"] == "new/branch"
    # original unchanged
    assert state.worktrees["a"]["branch"] == "old/branch"


def test_updateWorktreeBranch_missing_name():
    state = StateFile(repo_root="/repo", worktrees={})
    new_state = updateWorktreeBranch(state, "nonexistent", "new/branch")
    assert new_state is state
