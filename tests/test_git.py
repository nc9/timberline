from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from timberline.git import (
    branchExists,
    findRepoRoot,
    getAheadBehind,
    getCurrentBranch,
    getDefaultBranch,
    getStatusShort,
    listWorktreesRaw,
    renameBranch,
    runGit,
)
from timberline.models import TimberlineError


def test_runGit_basic(tmp_git_repo: Path):
    out = runGit("rev-parse", "--is-inside-work-tree", cwd=tmp_git_repo)
    assert out == "true"


def test_runGit_fails_on_bad_command(tmp_git_repo: Path):
    with pytest.raises(TimberlineError):
        runGit("nonexistent-command", cwd=tmp_git_repo)


def test_findRepoRoot(tmp_git_repo: Path):
    root = findRepoRoot(tmp_git_repo)
    assert root == tmp_git_repo


def test_findRepoRoot_from_subdir(tmp_git_repo: Path):
    subdir = tmp_git_repo / "a" / "b"
    subdir.mkdir(parents=True)
    root = findRepoRoot(subdir)
    assert root == tmp_git_repo


def test_findRepoRoot_from_worktree(tmp_git_repo: Path):
    wt_dir = tmp_git_repo / ".tl" / "test-wt"
    subprocess.run(
        ["git", "worktree", "add", "-b", "test-branch", str(wt_dir)],
        cwd=tmp_git_repo,
        capture_output=True,
        check=True,
    )
    root = findRepoRoot(wt_dir)
    assert root == tmp_git_repo


def test_getCurrentBranch(tmp_git_repo: Path):
    assert getCurrentBranch(tmp_git_repo) == "main"


def test_getDefaultBranch(tmp_git_repo: Path):
    assert getDefaultBranch(tmp_git_repo) == "main"


def test_branchExists(tmp_git_repo: Path):
    assert branchExists("main", cwd=tmp_git_repo)
    assert not branchExists("nonexistent", cwd=tmp_git_repo)


def test_listWorktreesRaw(tmp_git_repo: Path):
    wts = listWorktreesRaw(tmp_git_repo)
    assert len(wts) >= 1
    assert wts[0]["worktree"] == str(tmp_git_repo)
    assert wts[0]["branch"] == "main"


def test_listWorktreesRaw_with_worktree(tmp_git_repo: Path):
    wt_dir = tmp_git_repo / ".tl" / "obsidian"
    subprocess.run(
        ["git", "worktree", "add", "-b", "feat/obsidian", str(wt_dir)],
        cwd=tmp_git_repo,
        capture_output=True,
        check=True,
    )
    wts = listWorktreesRaw(tmp_git_repo)
    assert len(wts) == 2
    branches = {wt.get("branch") for wt in wts}
    assert "feat/obsidian" in branches


def test_getStatusShort_clean(tmp_git_repo: Path):
    assert getStatusShort(tmp_git_repo) == ""


def test_getStatusShort_dirty(tmp_git_repo: Path):
    (tmp_git_repo / "new.txt").write_text("new")
    status = getStatusShort(tmp_git_repo)
    assert "new.txt" in status


def test_getAheadBehind(tmp_git_repo: Path):
    ahead, behind = getAheadBehind("main", "main", tmp_git_repo)
    assert ahead == 0
    assert behind == 0


def test_renameBranch(tmp_git_repo: Path):
    subprocess.run(
        ["git", "checkout", "-b", "old-branch"],
        cwd=tmp_git_repo,
        capture_output=True,
        check=True,
    )
    renameBranch("old-branch", "new-branch", cwd=tmp_git_repo)
    assert getCurrentBranch(tmp_git_repo) == "new-branch"
    assert branchExists("new-branch", cwd=tmp_git_repo)
    assert not branchExists("old-branch", cwd=tmp_git_repo)
