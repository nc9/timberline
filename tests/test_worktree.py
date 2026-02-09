from __future__ import annotations

from pathlib import Path

import pytest

from timberline.config import writeConfig
from timberline.types import TimberlineConfig, TimberlineError
from timberline.worktree import (
    createWorktree,
    getWorktree,
    getWorktreePath,
    listWorktrees,
    removeWorktree,
    resolveBranchName,
)


@pytest.fixture
def repo_with_config(tmp_git_repo: Path) -> tuple[Path, TimberlineConfig]:
    cfg = TimberlineConfig(user="test", base_branch="main")
    writeConfig(tmp_git_repo, cfg)
    return tmp_git_repo, cfg


def test_getWorktreePath(tmp_path: Path):
    cfg = TimberlineConfig()
    assert getWorktreePath(tmp_path, cfg, "obsidian") == tmp_path / ".tl" / "obsidian"


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
