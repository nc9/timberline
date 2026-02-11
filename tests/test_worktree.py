from __future__ import annotations

from pathlib import Path

import pytest

from timberline.config import writeConfig
from timberline.git import runGit
from timberline.models import TimberlineConfig, TimberlineError, getWorktreeBasePath
from timberline.worktree import (
    checkoutWorktree,
    createWorktree,
    deriveName,
    getWorktree,
    getWorktreePath,
    listWorktrees,
    removeWorktree,
    resolveBranchName,
)


@pytest.fixture
def repo_with_config(tmp_git_repo: Path) -> tuple[Path, TimberlineConfig]:
    cfg = TimberlineConfig(user="test", base_branch="main", project_name="testrepo")
    writeConfig(tmp_git_repo, cfg)
    return tmp_git_repo, cfg


def test_getWorktreePath(tmp_path: Path):
    cfg = TimberlineConfig(project_name="myproj")
    path = getWorktreePath(cfg, "obsidian", tmp_path)
    assert path == getWorktreeBasePath("myproj") / "obsidian"


def test_resolveBranchName():
    cfg = TimberlineConfig(user="nik", branch_template="{user}/{type}/{name}")
    assert resolveBranchName(cfg, "obsidian") == "nik/feature/obsidian"
    assert resolveBranchName(cfg, "auth", "fix") == "nik/fix/auth"


def test_createWorktree(repo_with_config: tuple[Path, TimberlineConfig]):
    repo, cfg = repo_with_config
    info = createWorktree(repo, cfg, name="obsidian")
    assert info.name == "obsidian"
    assert info.branch == "test/feature/obsidian"
    assert Path(info.path).exists()


def test_createWorktree_autoname(repo_with_config: tuple[Path, TimberlineConfig]):
    repo, cfg = repo_with_config
    info = createWorktree(repo, cfg)
    assert info.name  # should have a generated name
    assert Path(info.path).exists()


def test_createWorktree_duplicate_fails(repo_with_config: tuple[Path, TimberlineConfig]):
    repo, cfg = repo_with_config
    createWorktree(repo, cfg, name="obsidian")
    with pytest.raises(TimberlineError, match="already exists"):
        createWorktree(repo, cfg, name="obsidian")


def test_listWorktrees(repo_with_config: tuple[Path, TimberlineConfig]):
    repo, cfg = repo_with_config
    createWorktree(repo, cfg, name="alpha")
    createWorktree(repo, cfg, name="beta")
    wts = listWorktrees(repo, cfg)
    names = {wt.name for wt in wts}
    assert "alpha" in names
    assert "beta" in names


def test_removeWorktree(repo_with_config: tuple[Path, TimberlineConfig]):
    repo, cfg = repo_with_config
    info = createWorktree(repo, cfg, name="obsidian")
    assert Path(info.path).exists()

    removeWorktree(repo, cfg, "obsidian")
    assert not Path(info.path).exists()
    assert getWorktree(repo, cfg, "obsidian") is None


def test_removeWorktree_dirty_fails(repo_with_config: tuple[Path, TimberlineConfig]):
    repo, cfg = repo_with_config
    info = createWorktree(repo, cfg, name="dirty")
    # modify a tracked file (README.md comes from initial commit)
    (Path(info.path) / "README.md").write_text("modified")

    with pytest.raises(TimberlineError, match="uncommitted"):
        removeWorktree(repo, cfg, "dirty")


def test_removeWorktree_force(repo_with_config: tuple[Path, TimberlineConfig]):
    repo, cfg = repo_with_config
    info = createWorktree(repo, cfg, name="dirty")
    (Path(info.path) / "README.md").write_text("modified")

    removeWorktree(repo, cfg, "dirty", force=True)
    assert not Path(info.path).exists()


def test_getWorktree(repo_with_config: tuple[Path, TimberlineConfig]):
    repo, cfg = repo_with_config
    createWorktree(repo, cfg, name="obsidian")
    wt = getWorktree(repo, cfg, "obsidian")
    assert wt is not None
    assert wt.name == "obsidian"


def test_getWorktree_missing(repo_with_config: tuple[Path, TimberlineConfig]):
    repo, cfg = repo_with_config
    assert getWorktree(repo, cfg, "nonexistent") is None


def test_worktree_path_outside_repo(repo_with_config: tuple[Path, TimberlineConfig]):
    """Worktrees should be created outside the repo directory."""
    repo, cfg = repo_with_config
    info = createWorktree(repo, cfg, name="external")
    wt_path = Path(info.path)
    # worktree should NOT be under repo_root
    assert not str(wt_path).startswith(str(repo))
    # should be under TIMBERLINE_HOME
    assert ".timberline" in str(wt_path)


# ─── deriveName tests ────────────────────────────────────────────────────────


def test_deriveName_simple():
    assert deriveName("feature/auth") == "auth"


def test_deriveName_nested():
    assert deriveName("nc9/feature/agent-setup") == "agent-setup"


def test_deriveName_no_slash():
    assert deriveName("mybranch") == "mybranch"


# ─── checkoutWorktree tests ──────────────────────────────────────────────────


def test_checkoutWorktree_local_branch(repo_with_config: tuple[Path, TimberlineConfig]):
    """Checkout an existing local branch into a worktree."""
    repo, cfg = repo_with_config
    # create a branch to check out
    runGit("branch", "feature/login", cwd=repo)

    info = checkoutWorktree(repo, cfg, "feature/login")
    assert info.name == "login"  # derived from branch
    assert info.branch == "feature/login"
    assert info.type == ""
    assert info.pr == 0
    assert Path(info.path).exists()


def test_checkoutWorktree_name_override(repo_with_config: tuple[Path, TimberlineConfig]):
    """Name override takes precedence over derived name."""
    repo, cfg = repo_with_config
    runGit("branch", "feature/login", cwd=repo)

    info = checkoutWorktree(repo, cfg, "feature/login", name="myname")
    assert info.name == "myname"
    assert Path(info.path).exists()


def test_checkoutWorktree_missing_branch(repo_with_config: tuple[Path, TimberlineConfig]):
    """Missing branch raises TimberlineError."""
    repo, cfg = repo_with_config
    with pytest.raises(TimberlineError, match="not found"):
        checkoutWorktree(repo, cfg, "nonexistent/branch")


def test_checkoutWorktree_duplicate_name(repo_with_config: tuple[Path, TimberlineConfig]):
    """Duplicate worktree name raises error."""
    repo, cfg = repo_with_config
    runGit("branch", "feat/alpha", cwd=repo)
    runGit("branch", "feat/beta", cwd=repo)

    checkoutWorktree(repo, cfg, "feat/alpha", name="samename")
    with pytest.raises(TimberlineError, match="already exists"):
        checkoutWorktree(repo, cfg, "feat/beta", name="samename")


def test_checkoutWorktree_with_pr(repo_with_config: tuple[Path, TimberlineConfig]):
    """PR number is stored on WorktreeInfo."""
    repo, cfg = repo_with_config
    runGit("branch", "feature/pr-test", cwd=repo)

    info = checkoutWorktree(repo, cfg, "feature/pr-test", pr=42)
    assert info.pr == 42

    # verify persisted in state via getWorktree
    wt = getWorktree(repo, cfg, "pr-test")
    assert wt is not None
    assert wt.pr == 42


def test_checkoutWorktree_shows_in_list(repo_with_config: tuple[Path, TimberlineConfig]):
    """Checked out worktree appears in listWorktrees."""
    repo, cfg = repo_with_config
    runGit("branch", "feature/visible", cwd=repo)

    checkoutWorktree(repo, cfg, "feature/visible")
    wts = listWorktrees(repo, cfg)
    names = {wt.name for wt in wts}
    assert "visible" in names
