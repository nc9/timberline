from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from timberline.cli import app
from timberline.config import writeConfig
from timberline.git import (
    cloneCheckoutExistingBranch,
    cloneCheckoutNewBranch,
    cloneLocal,
    findRepoRoot,
    getRemoteUrl,
    runGit,
)
from timberline.models import (
    StateFile,
    TimberlineConfig,
    TimberlineError,
    WorktreeInfo,
    WorktreeMode,
    getWorktreeBasePath,
    writeRepoRootMarker,
)
from timberline.state import addWorktreeToState, loadState, reconcileState, saveState
from timberline.worktree import (
    checkoutClone,
    createCheckoutClone,
    getWorktree,
    listWorktrees,
    removeWorktree,
)

runner = CliRunner()


def _run(cmd: str, cwd: Path) -> None:
    subprocess.run(cmd.split(), cwd=cwd, capture_output=True, check=True)


@pytest.fixture
def checkout_cfg(tmp_git_repo: Path) -> tuple[Path, TimberlineConfig]:
    cfg = TimberlineConfig(
        user="test",
        base_branch="main",
        project_name="testrepo",
        mode=WorktreeMode.CHECKOUT,
    )
    writeConfig(tmp_git_repo, cfg)
    return tmp_git_repo, cfg


# ─── git.py clone helpers ────────────────────────────────────────────────────


def test_getRemoteUrl(tmp_git_repo: Path):
    url = getRemoteUrl(cwd=tmp_git_repo)
    assert url  # should be the bare repo path


def test_getRemoteUrl_no_remote(tmp_path: Path):
    """Repo without remote raises TimberlineError."""
    repo = tmp_path / "no-remote"
    repo.mkdir()
    _run("git init -b main", repo)
    _run("git config user.email test@test.com", repo)
    _run("git config user.name Test", repo)
    (repo / "README.md").write_text("# Test")
    _run("git add .", repo)
    _run("git commit -m init", repo)
    with pytest.raises(TimberlineError):
        getRemoteUrl(cwd=repo)


def test_cloneLocal(tmp_git_repo: Path, tl_home: Path):
    target = tl_home / "projects" / "test" / "worktrees" / "myclone"
    remote_url = getRemoteUrl(cwd=tmp_git_repo)
    cloneLocal(tmp_git_repo, target, remote_url)

    assert target.exists()
    assert (target / ".git").is_dir()
    # remote should point to actual origin, not parent repo
    clone_url = getRemoteUrl(cwd=target)
    assert clone_url == remote_url


def test_cloneCheckoutNewBranch(tmp_git_repo: Path, tl_home: Path):
    target = tl_home / "projects" / "test" / "worktrees" / "newbranch"
    remote_url = getRemoteUrl(cwd=tmp_git_repo)
    cloneLocal(tmp_git_repo, target, remote_url)
    cloneCheckoutNewBranch("feat/test", "main", target)

    branch = runGit("rev-parse", "--abbrev-ref", "HEAD", cwd=target)
    assert branch == "feat/test"


def test_cloneCheckoutExistingBranch(tmp_git_repo: Path, tl_home: Path):
    # create and push a branch
    _run("git checkout -b feat/existing", tmp_git_repo)
    (tmp_git_repo / "new.txt").write_text("hello")
    _run("git add .", tmp_git_repo)
    _run("git commit -m add-file", tmp_git_repo)
    _run("git push origin feat/existing", tmp_git_repo)
    _run("git checkout main", tmp_git_repo)

    target = tl_home / "projects" / "test" / "worktrees" / "existing"
    remote_url = getRemoteUrl(cwd=tmp_git_repo)
    cloneLocal(tmp_git_repo, target, remote_url)
    cloneCheckoutExistingBranch("feat/existing", target)

    branch = runGit("rev-parse", "--abbrev-ref", "HEAD", cwd=target)
    assert branch == "feat/existing"
    assert (target / "new.txt").exists()


# ─── findRepoRoot clone detection ────────────────────────────────────────────


def test_findRepoRoot_from_clone(tmp_git_repo: Path, tl_home: Path):
    """findRepoRoot resolves clone back to parent repo."""
    project_name = "testrepo"
    writeRepoRootMarker(project_name, tmp_git_repo)

    target = getWorktreeBasePath(project_name) / "myclone"
    remote_url = getRemoteUrl(cwd=tmp_git_repo)
    cloneLocal(tmp_git_repo, target, remote_url)
    cloneCheckoutNewBranch("feat/test", "main", target)

    root = findRepoRoot(target)
    assert root == tmp_git_repo


def test_findRepoRoot_from_clone_subdir(tmp_git_repo: Path, tl_home: Path):
    """findRepoRoot resolves from subdir inside clone."""
    project_name = "testrepo"
    writeRepoRootMarker(project_name, tmp_git_repo)

    target = getWorktreeBasePath(project_name) / "myclone"
    remote_url = getRemoteUrl(cwd=tmp_git_repo)
    cloneLocal(tmp_git_repo, target, remote_url)
    cloneCheckoutNewBranch("feat/test", "main", target)

    subdir = target / "sub"
    subdir.mkdir()
    root = findRepoRoot(subdir)
    assert root == tmp_git_repo


# ─── worktree.py clone functions ─────────────────────────────────────────────


def test_createCheckoutClone(checkout_cfg: tuple[Path, TimberlineConfig]):
    repo, cfg = checkout_cfg
    info = createCheckoutClone(repo, cfg, name="obsidian")
    assert info.name == "obsidian"
    assert info.branch == "test/feature/obsidian"
    assert info.mode == "checkout"
    assert Path(info.path).exists()
    assert (Path(info.path) / ".git").is_dir()  # full clone, not worktree


def test_createCheckoutClone_autoname(checkout_cfg: tuple[Path, TimberlineConfig]):
    repo, cfg = checkout_cfg
    info = createCheckoutClone(repo, cfg)
    assert info.name
    assert info.mode == "checkout"
    assert Path(info.path).exists()


def test_createCheckoutClone_duplicate_fails(checkout_cfg: tuple[Path, TimberlineConfig]):
    repo, cfg = checkout_cfg
    createCheckoutClone(repo, cfg, name="obsidian")
    with pytest.raises(TimberlineError, match="already exists"):
        createCheckoutClone(repo, cfg, name="obsidian")


def test_checkoutClone_existing_branch(checkout_cfg: tuple[Path, TimberlineConfig]):
    repo, cfg = checkout_cfg
    # create and push branch
    _run("git checkout -b feat/login", repo)
    (repo / "login.txt").write_text("login")
    _run("git add .", repo)
    _run("git commit -m login", repo)
    _run("git push origin feat/login", repo)
    _run("git checkout main", repo)

    info = checkoutClone(repo, cfg, "feat/login")
    assert info.branch == "feat/login"
    assert info.mode == "checkout"
    assert (Path(info.path) / "login.txt").exists()


def test_checkoutClone_with_pr(checkout_cfg: tuple[Path, TimberlineConfig]):
    repo, cfg = checkout_cfg
    _run("git checkout -b feat/pr-test", repo)
    _run("git push origin feat/pr-test", repo)
    _run("git checkout main", repo)

    info = checkoutClone(repo, cfg, "feat/pr-test", pr=42)
    assert info.pr == 42
    assert info.mode == "checkout"


# ─── removeWorktree mode dispatch ────────────────────────────────────────────


def test_removeWorktree_checkout_mode(checkout_cfg: tuple[Path, TimberlineConfig]):
    repo, cfg = checkout_cfg
    info = createCheckoutClone(repo, cfg, name="toberm")
    assert Path(info.path).exists()

    removeWorktree(repo, cfg, "toberm")
    assert not Path(info.path).exists()
    assert getWorktree(repo, cfg, "toberm") is None


def test_removeWorktree_checkout_no_branch_delete(checkout_cfg: tuple[Path, TimberlineConfig]):
    """Checkout removal should NOT delete branch in parent repo."""
    repo, cfg = checkout_cfg
    info = createCheckoutClone(repo, cfg, name="nobranch")

    # branch should NOT exist in parent (it only lives in clone)
    from timberline.git import branchExists

    assert not branchExists(info.branch, cwd=repo)

    removeWorktree(repo, cfg, "nobranch")
    # still no branch in parent
    assert not branchExists(info.branch, cwd=repo)


def test_removeWorktree_checkout_dirty_fails(checkout_cfg: tuple[Path, TimberlineConfig]):
    repo, cfg = checkout_cfg
    info = createCheckoutClone(repo, cfg, name="dirty")
    (Path(info.path) / "README.md").write_text("modified")

    with pytest.raises(TimberlineError, match="uncommitted"):
        removeWorktree(repo, cfg, "dirty")


def test_removeWorktree_checkout_force(checkout_cfg: tuple[Path, TimberlineConfig]):
    repo, cfg = checkout_cfg
    info = createCheckoutClone(repo, cfg, name="dirty")
    (Path(info.path) / "README.md").write_text("modified")

    removeWorktree(repo, cfg, "dirty", force=True)
    assert not Path(info.path).exists()


# ─── listWorktrees with checkout mode ────────────────────────────────────────


def test_listWorktrees_shows_checkout_mode(checkout_cfg: tuple[Path, TimberlineConfig]):
    repo, cfg = checkout_cfg
    createCheckoutClone(repo, cfg, name="alpha")
    wts = listWorktrees(repo, cfg)
    assert len(wts) == 1
    assert wts[0].mode == "checkout"


def test_listWorktrees_diff_stats_in_checkout(checkout_cfg: tuple[Path, TimberlineConfig]):
    """Diff stats for checkout clones should work (using clone as cwd)."""
    repo, cfg = checkout_cfg
    info = createCheckoutClone(repo, cfg, name="stats")
    wt_path = Path(info.path)

    # add uncommitted change
    (wt_path / "README.md").write_text("modified content\n")

    wts = listWorktrees(repo, cfg)
    wt = next(w for w in wts if w.name == "stats")
    assert wt.uncommitted_added > 0 or wt.uncommitted_removed > 0


# ─── state mode persistence ─────────────────────────────────────────────────


def test_addWorktreeToState_persists_mode():
    state = StateFile(repo_root="/repo")
    info = WorktreeInfo(
        name="test",
        branch="feat/test",
        base_branch="main",
        type="feature",
        path="/path/test",
        created_at="2026-01-01T00:00:00+00:00",
        mode="checkout",
    )
    new_state = addWorktreeToState(state, info)
    assert new_state.worktrees["test"]["mode"] == "checkout"


def test_addWorktreeToState_omits_worktree_mode():
    """Default worktree mode is not persisted (backward compat)."""
    state = StateFile(repo_root="/repo")
    info = WorktreeInfo(
        name="test",
        branch="feat/test",
        base_branch="main",
        type="feature",
        path="/path/test",
        created_at="2026-01-01T00:00:00+00:00",
    )
    new_state = addWorktreeToState(state, info)
    assert "mode" not in new_state.worktrees["test"]


# ─── reconcileState mode-aware ───────────────────────────────────────────────


def test_reconcileState_checkout_validates_by_dir(tl_home: Path, tmp_path: Path):
    """Checkout entries validated by directory existence, not git worktree list."""
    wt_base = str(getWorktreeBasePath("myproj"))
    clone_path = f"{wt_base}/myclone"

    # create the directory so it passes validation
    Path(clone_path).mkdir(parents=True)

    state = StateFile(
        repo_root="/repo",
        worktrees={
            "myclone": {
                "branch": "feat/test",
                "base_branch": "main",
                "type": "feature",
                "path": clone_path,
                "mode": "checkout",
            },
        },
    )
    # empty git worktrees — clone should survive (not in git worktree list)
    git_wts = [{"worktree": "/repo", "branch": "main"}]
    result = reconcileState(state, git_wts, "myproj")
    assert "myclone" in result.worktrees


def test_reconcileState_checkout_removed_when_dir_gone(tl_home: Path):
    """Checkout entries removed when directory doesn't exist."""
    state = StateFile(
        repo_root="/repo",
        worktrees={
            "gone": {
                "branch": "feat/gone",
                "path": "/nonexistent/path",
                "mode": "checkout",
            },
        },
    )
    git_wts = [{"worktree": "/repo", "branch": "main"}]
    result = reconcileState(state, git_wts, "myproj")
    assert "gone" not in result.worktrees


def test_reconcileState_no_untracked_discovery_for_clones(tl_home: Path):
    """Untracked discovery only applies to worktree mode, not clones."""
    # even if a dir exists under worktrees/, if it's not in state and not in
    # git worktree list, it won't be auto-discovered
    state = StateFile(repo_root="/repo", worktrees={})
    git_wts = [{"worktree": "/repo", "branch": "main"}]
    result = reconcileState(state, git_wts, "myproj")
    assert len(result.worktrees) == 0


# ─── CLI integration tests ──────────────────────────────────────────────────


@pytest.fixture
def checkout_repo_dir(tmp_git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_git_repo)
    return tmp_git_repo


def test_cli_new_checkout_mode(checkout_repo_dir: Path):
    """tl new creates clone when mode=checkout."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["config", "set", "mode", "checkout"])

    result = runner.invoke(app, ["new", "obsidian", "--no-init"])
    assert result.exit_code == 0
    assert "obsidian" in result.output


def test_cli_checkout_checkout_mode(checkout_repo_dir: Path):
    """tl checkout creates clone when mode=checkout."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["config", "set", "mode", "checkout"])

    _run("git checkout -b feat/cli-co", checkout_repo_dir)
    _run("git push origin feat/cli-co", checkout_repo_dir)
    _run("git checkout main", checkout_repo_dir)

    result = runner.invoke(app, ["checkout", "feat/cli-co", "--no-init"])
    assert result.exit_code == 0
    assert "Checked out" in result.output


def test_cli_rm_checkout_mode(checkout_repo_dir: Path):
    """tl rm removes checkout clone."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["config", "set", "mode", "checkout"])

    runner.invoke(app, ["new", "toberm", "--no-init"])
    result = runner.invoke(app, ["rm", "toberm"])
    assert result.exit_code == 0
    assert "Removed" in result.output

    result = runner.invoke(app, ["ls"])
    assert "toberm" not in result.output


def test_cli_ls_json_has_mode(checkout_repo_dir: Path):
    """tl ls --json includes mode field."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["config", "set", "mode", "checkout"])
    runner.invoke(app, ["new", "obsidian", "--no-init"])

    result = runner.invoke(app, ["ls", "--json"])
    assert result.exit_code == 0
    assert '"mode"' in result.output
    assert '"checkout"' in result.output


def test_cli_full_lifecycle_checkout(checkout_repo_dir: Path):
    """Full lifecycle: init -> new -> ls -> rm in checkout mode."""
    r = runner.invoke(app, ["init", "--defaults", "--user", "test"])
    assert r.exit_code == 0
    runner.invoke(app, ["config", "set", "mode", "checkout"])

    r = runner.invoke(app, ["new", "alpha", "--no-init"])
    assert r.exit_code == 0

    r = runner.invoke(app, ["new", "beta", "--no-init"])
    assert r.exit_code == 0

    r = runner.invoke(app, ["ls"])
    assert r.exit_code == 0
    assert "alpha" in r.output
    assert "beta" in r.output

    r = runner.invoke(app, ["rm", "alpha"])
    assert r.exit_code == 0

    r = runner.invoke(app, ["ls"])
    assert "alpha" not in r.output
    assert "beta" in r.output

    r = runner.invoke(app, ["rm", "--all"])
    assert r.exit_code == 0

    r = runner.invoke(app, ["ls"])
    assert "beta" not in r.output


def test_cli_clean_removes_checkout_orphans(checkout_repo_dir: Path, tl_home: Path):
    """tl clean removes orphaned checkout directories."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["config", "set", "mode", "checkout"])

    # create a clone, then manually delete from state to make it orphaned
    r = runner.invoke(app, ["new", "orphan", "--no-init"])
    assert r.exit_code == 0

    from timberline.config import loadConfig
    from timberline.models import resolveProjectName
    from timberline.state import removeWorktreeFromState

    cfg = loadConfig(checkout_repo_dir)
    project_name = resolveProjectName(checkout_repo_dir, cfg.project_name)
    state = loadState(project_name, checkout_repo_dir)
    orphan_path = Path(state.worktrees["orphan"]["path"])
    assert orphan_path.exists()

    # remove from state only (dir still exists)
    state = removeWorktreeFromState(state, "orphan")
    saveState(project_name, state)

    result = runner.invoke(app, ["clean"])
    assert result.exit_code == 0
    assert not orphan_path.exists()


# ─── WorktreeMode enum ──────────────────────────────────────────────────────


def test_worktree_mode_enum():
    assert WorktreeMode.WORKTREE == "worktree"
    assert WorktreeMode.CHECKOUT == "checkout"
    assert WorktreeMode("worktree") == WorktreeMode.WORKTREE
    assert WorktreeMode("checkout") == WorktreeMode.CHECKOUT


def test_config_mode_default():
    cfg = TimberlineConfig()
    assert cfg.mode == WorktreeMode.CHECKOUT


def test_config_mode_checkout():
    cfg = TimberlineConfig(mode=WorktreeMode.CHECKOUT)
    assert cfg.mode == WorktreeMode.CHECKOUT


def test_worktreeinfo_mode_default():
    info = WorktreeInfo(name="test", branch="b", base_branch="main", type="feature", path="/p")
    assert info.mode == "worktree"
