from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from timberline.git import (
    _parseNumstat,
    branchExists,
    fetchBranch,
    findRepoRoot,
    getAheadBehind,
    getCommittedDiffStats,
    getCurrentBranch,
    getDefaultBranch,
    getDiffNumstat,
    getLastCommitTime,
    getStatusShort,
    isBranchMerged,
    listWorktreesRaw,
    renameBranch,
    resolvePrBranch,
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


# ─── isBranchMerged tests ────────────────────────────────────────────────────


def _run(cmd: str, cwd: Path) -> None:
    subprocess.run(cmd.split(), cwd=cwd, capture_output=True, check=True)


def _setup_remote(tmp_path: Path) -> tuple[Path, Path]:
    """Create bare remote + clone with initial commit."""
    bare = tmp_path / "remote.git"
    bare.mkdir()
    _run("git init --bare", bare)

    clone = tmp_path / "clone"
    _run(f"git clone {bare} {clone}", tmp_path)
    _run("git config user.email test@test.com", clone)
    _run("git config user.name Test", clone)
    _run("git checkout -b main", clone)
    (clone / "README.md").write_text("# init")
    _run("git add .", clone)
    _run("git commit -m init", clone)
    _run("git push -u origin main", clone)
    return bare, clone


def test_isBranchMerged_squash_merged(tmp_path: Path):
    _, clone = _setup_remote(tmp_path)

    # create feature branch with multiple commits
    _run("git checkout -b feat/test", clone)
    (clone / "a.txt").write_text("a")
    _run("git add .", clone)
    _run("git commit -m one", clone)
    (clone / "b.txt").write_text("b")
    _run("git add .", clone)
    _run("git commit -m two", clone)

    # squash merge into main and push
    _run("git checkout main", clone)
    _run("git merge --squash feat/test", clone)
    _run("git commit -m squashed", clone)
    _run("git push origin main", clone)

    # back on feature branch — trees should match
    _run("git checkout feat/test", clone)
    assert isBranchMerged("feat/test", "origin/main", clone)


def test_isBranchMerged_not_merged(tmp_path: Path):
    _, clone = _setup_remote(tmp_path)

    _run("git checkout -b feat/test", clone)
    (clone / "a.txt").write_text("a")
    _run("git add .", clone)
    _run("git commit -m one", clone)

    assert not isBranchMerged("feat/test", "origin/main", clone)


def test_isBranchMerged_diverged_after_merge(tmp_path: Path):
    _, clone = _setup_remote(tmp_path)

    _run("git checkout -b feat/test", clone)
    (clone / "a.txt").write_text("a")
    _run("git add .", clone)
    _run("git commit -m one", clone)

    # squash merge
    _run("git checkout main", clone)
    _run("git merge --squash feat/test", clone)
    _run("git commit -m squashed", clone)
    _run("git push origin main", clone)

    # add extra commit on feature after merge
    _run("git checkout feat/test", clone)
    (clone / "c.txt").write_text("c")
    _run("git add .", clone)
    _run("git commit -m extra", clone)

    assert not isBranchMerged("feat/test", "origin/main", clone)


def test_isBranchMerged_no_remote_ref(tmp_git_repo: Path):
    """Missing remote ref returns False (safe default)."""
    assert not isBranchMerged("main", "origin/main", tmp_git_repo)


# ─── fetchBranch tests ────────────────────────────────────────────────────────


def test_fetchBranch_no_remote(tmp_git_repo: Path):
    """fetchBranch raises TimberlineError when no remote exists."""
    with pytest.raises(TimberlineError):
        fetchBranch("main", cwd=tmp_git_repo)


# ─── resolvePrBranch tests ───────────────────────────────────────────────────


def test_resolvePrBranch_mock():
    """resolvePrBranch returns head/base from gh CLI output."""
    mock_result = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout='{"headRefName":"feat/auth","baseRefName":"main"}',
    )
    with patch("subprocess.run", return_value=mock_result):
        head, base = resolvePrBranch(42)
        assert head == "feat/auth"
        assert base == "main"


def test_resolvePrBranch_gh_not_found():
    """resolvePrBranch raises TimberlineError when gh not found."""
    with (
        patch("subprocess.run", side_effect=FileNotFoundError),
        pytest.raises(TimberlineError, match="PR #99"),
    ):
        resolvePrBranch(99)


# ─── _parseNumstat tests ────────────────────────────────────────────────────


def test_parseNumstat_normal():
    output = "10\t5\tsrc/main.py\n3\t0\tREADME.md"
    assert _parseNumstat(output) == (13, 5)


def test_parseNumstat_binary():
    output = "-\t-\timage.png\n4\t2\tcode.py"
    assert _parseNumstat(output) == (4, 2)


def test_parseNumstat_empty():
    assert _parseNumstat("") == (0, 0)


def test_parseNumstat_mixed():
    output = "100\t50\tbig.py\n-\t-\tbin.wasm\n1\t1\tsmall.py"
    assert _parseNumstat(output) == (101, 51)


# ─── getDiffNumstat tests ───────────────────────────────────────────────────


def test_getDiffNumstat_clean(tmp_git_repo: Path):
    added, removed = getDiffNumstat(tmp_git_repo)
    assert added == 0
    assert removed == 0


def test_getDiffNumstat_with_changes(tmp_git_repo: Path):
    (tmp_git_repo / "README.md").write_text("line1\nline2\nline3\n")
    added, removed = getDiffNumstat(tmp_git_repo)
    assert added > 0


# ─── getCommittedDiffStats tests ────────────────────────────────────────────


def test_getCommittedDiffStats_no_diff(tmp_git_repo: Path):
    added, removed, files = getCommittedDiffStats("main", "main", tmp_git_repo)
    assert added == 0 and removed == 0 and files == 0


def test_getCommittedDiffStats_with_commits(tmp_git_repo: Path):
    _run("git checkout -b feat/stats", tmp_git_repo)
    (tmp_git_repo / "new.txt").write_text("hello\nworld\n")
    _run("git add .", tmp_git_repo)
    _run("git commit -m add-file", tmp_git_repo)
    added, removed, files = getCommittedDiffStats("feat/stats", "main", tmp_git_repo)
    assert added == 2
    assert removed == 0
    assert files == 1


# ─── getLastCommitTime tests ────────────────────────────────────────────────


def test_getLastCommitTime(tmp_git_repo: Path):
    ts = getLastCommitTime(tmp_git_repo)
    assert ts  # should have ISO timestamp from initial commit
    assert "T" in ts  # ISO format
