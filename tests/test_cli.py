from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from timberline.cli import app
from timberline.git import runGit
from timberline.models import getProjectDir

runner = CliRunner()


@pytest.fixture
def repo_dir(tmp_git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_git_repo)
    return tmp_git_repo


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "worktree" in result.output.lower()


def test_init_defaults(repo_dir: Path):
    result = runner.invoke(app, ["init", "--defaults"])
    assert result.exit_code == 0
    assert (repo_dir / ".timberline.toml").exists()


def test_init_creates_project_dir(repo_dir: Path):
    result = runner.invoke(app, ["init", "--defaults"])
    assert result.exit_code == 0
    project_dir = getProjectDir(repo_dir.name)
    assert project_dir.exists()
    assert (project_dir / "repo_root").exists()


def test_new_and_ls(repo_dir: Path):
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    result = runner.invoke(app, ["new", "obsidian", "--no-init"])
    assert result.exit_code == 0
    assert "obsidian" in result.output

    result = runner.invoke(app, ["ls"])
    assert result.exit_code == 0
    assert "obsidian" in result.output


def test_new_autoname(repo_dir: Path):
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    result = runner.invoke(app, ["new", "--no-init"])
    assert result.exit_code == 0
    assert "Created worktree" in result.output


def test_new_with_type(repo_dir: Path):
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    result = runner.invoke(app, ["new", "bugfix", "--type", "fix", "--no-init"])
    assert result.exit_code == 0
    assert "test/fix/bugfix" in result.output


def test_cd(repo_dir: Path):
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["new", "obsidian", "--no-init"])

    result = runner.invoke(app, ["cd", "obsidian"])
    assert result.exit_code == 0
    assert "obsidian" in result.output


def test_cd_nonexistent(repo_dir: Path):
    runner.invoke(app, ["init", "--defaults"])
    result = runner.invoke(app, ["cd", "nonexistent"])
    assert result.exit_code == 1


def test_rm(repo_dir: Path):
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["new", "obsidian", "--no-init"])

    result = runner.invoke(app, ["rm", "obsidian"])
    assert result.exit_code == 0
    assert "Removed" in result.output

    result = runner.invoke(app, ["ls"])
    assert "obsidian" not in result.output


def test_rm_nonexistent(repo_dir: Path):
    runner.invoke(app, ["init", "--defaults"])
    result = runner.invoke(app, ["rm", "nonexistent"])
    assert result.exit_code == 1


def test_ls_json(repo_dir: Path):
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["new", "obsidian", "--no-init"])

    result = runner.invoke(app, ["ls", "--json"])
    assert result.exit_code == 0
    assert '"name"' in result.output


def test_ls_paths(repo_dir: Path):
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["new", "obsidian", "--no-init"])

    result = runner.invoke(app, ["ls", "--paths"])
    assert result.exit_code == 0
    assert "obsidian" in result.output


def test_config_show(repo_dir: Path):
    runner.invoke(app, ["init", "--defaults"])
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "worktree_dir" in result.output


def test_config_set(repo_dir: Path):
    runner.invoke(app, ["init", "--defaults"])
    result = runner.invoke(app, ["config", "set", "user", "newuser"])
    assert result.exit_code == 0
    assert "newuser" in result.output


def test_shell_init():
    result = runner.invoke(app, ["shell-init"])
    assert result.exit_code == 0
    assert "tlcd" in result.output


def test_status(repo_dir: Path):
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["new", "obsidian", "--no-init"])

    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0


def test_clean(repo_dir: Path):
    runner.invoke(app, ["init", "--defaults"])
    result = runner.invoke(app, ["clean"])
    assert result.exit_code == 0
    assert "Pruned" in result.output


def test_env_ls(repo_dir: Path):
    runner.invoke(app, ["init", "--defaults"])
    (repo_dir / ".env").write_text("KEY=val")

    result = runner.invoke(app, ["env", "ls"])
    assert result.exit_code == 0
    assert ".env" in result.output


def test_create_alias(repo_dir: Path):
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    result = runner.invoke(app, ["create", "aliased", "--no-init"])
    assert result.exit_code == 0
    assert "aliased" in result.output


def test_full_lifecycle(repo_dir: Path):
    """Full tl init -> new -> ls -> rm lifecycle."""
    r = runner.invoke(app, ["init", "--defaults", "--user", "test"])
    assert r.exit_code == 0

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


def test_new_outputs_path_to_stdout(repo_dir: Path):
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    result = runner.invoke(app, ["new", "obsidian", "--no-init"])
    assert result.exit_code == 0
    # stdout path is last line (bare print) — now under .timberline
    lines = result.output.strip().splitlines()
    assert any("obsidian" in line and ".timberline" in line for line in lines)


def test_rename(repo_dir: Path):
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["new", "obsidian", "--no-init"])

    result = runner.invoke(app, ["rename", "test/fix/new-name", "-n", "obsidian"])
    assert result.exit_code == 0
    assert "Renamed" in result.output
    assert "new-name" in result.output

    # verify branch updated in ls
    result = runner.invoke(app, ["ls", "--json"])
    assert "test/fix/new-name" in result.output


def test_setup_and_uninstall(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("timberline.shell.rcFilePath", lambda s: tmp_path / ".zshrc")
    monkeypatch.setattr("timberline.cli.detectShell", lambda: "zsh")

    result = runner.invoke(app, ["setup"])
    assert result.exit_code == 0
    assert "Added" in result.output
    assert (tmp_path / ".zshrc").exists()

    result = runner.invoke(app, ["setup", "--uninstall"])
    assert result.exit_code == 0
    assert "Removed" in result.output


def test_help_shows_new_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "setup" in result.output
    assert "rename" in result.output
    assert "land" in result.output


def test_init_detects_pre_land(repo_dir: Path):
    (repo_dir / "Makefile").write_text("check: fmt lint test\n")
    result = runner.invoke(app, ["init", "--defaults", "--user", "test"])
    assert result.exit_code == 0
    # config should have pre_land
    import tomllib

    with open(repo_dir / ".timberline.toml", "rb") as f:
        data = tomllib.load(f)
    assert data["timberline"]["pre_land"] == "make check"


def test_config_show_toml(repo_dir: Path):
    runner.invoke(app, ["init", "--defaults"])
    result = runner.invoke(app, ["config", "show", "--format", "toml"])
    assert result.exit_code == 0
    assert "[timberline]" in result.output


def test_config_set_dotNotation(repo_dir: Path):
    runner.invoke(app, ["init", "--defaults"])
    result = runner.invoke(app, ["config", "set", "env.auto_copy", "false"])
    assert result.exit_code == 0
    assert "env.auto_copy" in result.output


def test_config_set_agent_name_known(repo_dir: Path):
    """Setting agent.name to a known agent succeeds."""
    runner.invoke(app, ["init", "--defaults"])
    result = runner.invoke(app, ["config", "set", "agent.name", "codex"])
    assert result.exit_code == 0
    assert "agent.name" in result.output


def test_config_set_agent_name_unknown_rejects(repo_dir: Path):
    """Setting agent.name to unknown binary fails."""
    runner.invoke(app, ["init", "--defaults"])
    result = runner.invoke(app, ["config", "set", "agent.name", "nonexistent-agent-xyz"])
    assert result.exit_code == 1
    assert "Unknown agent" in result.output


def test_init_writes_commented_config(repo_dir: Path):
    result = runner.invoke(app, ["init", "--defaults", "--user", "test"])
    assert result.exit_code == 0
    content = (repo_dir / ".timberline.toml").read_text()
    # should have comments for default values
    assert "# worktree_dir" in content or "# default_type" in content


def test_worktree_not_in_repo(repo_dir: Path):
    """Worktrees created via CLI should not be under repo dir."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    result = runner.invoke(app, ["new", "isolated", "--no-init"])
    assert result.exit_code == 0
    # the path in output should NOT be under repo_dir
    lines = result.output.strip().splitlines()
    path_line = [ln for ln in lines if ".timberline" in ln]
    assert path_line  # should have a line with global path


# ─── Session linking CLI tests ────────────────────────────────────────────────


def test_new_no_link_flag(repo_dir: Path):
    """--no-link skips session linking even when config enabled."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["config", "set", "agent.link_project_session", "true"])

    with patch("timberline.cli.linkProjectSession") as mock_link:
        result = runner.invoke(app, ["new", "obsidian", "--no-init", "--no-link"])
        assert result.exit_code == 0
        mock_link.assert_not_called()


def test_new_links_session_when_enabled(repo_dir: Path):
    """tl new calls linkProjectSession when config enabled."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["config", "set", "agent.link_project_session", "true"])

    with patch("timberline.cli.linkProjectSession", return_value=True) as mock_link:
        result = runner.invoke(app, ["new", "obsidian", "--no-init"])
        assert result.exit_code == 0
        mock_link.assert_called_once()
        assert "Linked agent session" in result.output


def test_new_no_link_when_config_disabled(repo_dir: Path):
    """tl new does not call linkProjectSession when config disabled."""
    runner.invoke(app, ["init", "--defaults", "--user", "test", "--no-link-session"])

    with patch("timberline.cli.linkProjectSession") as mock_link:
        result = runner.invoke(app, ["new", "obsidian", "--no-init"])
        assert result.exit_code == 0
        mock_link.assert_not_called()


def test_rm_unlinks_session(repo_dir: Path):
    """tl rm calls unlinkProjectSession when config enabled."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["config", "set", "agent.link_project_session", "true"])
    runner.invoke(app, ["new", "obsidian", "--no-init"])

    with patch("timberline.cli.unlinkProjectSession") as mock_unlink:
        result = runner.invoke(app, ["rm", "obsidian"])
        assert result.exit_code == 0
        mock_unlink.assert_called_once()


def test_rm_all_unlinks_sessions(repo_dir: Path):
    """tl rm --all calls unlinkProjectSession for each worktree."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["config", "set", "agent.link_project_session", "true"])
    runner.invoke(app, ["new", "alpha", "--no-init"])
    runner.invoke(app, ["new", "beta", "--no-init"])

    with patch("timberline.cli.unlinkProjectSession") as mock_unlink:
        result = runner.invoke(app, ["rm", "--all"])
        assert result.exit_code == 0
        assert mock_unlink.call_count == 2


def test_rm_no_unlink_when_config_disabled(repo_dir: Path):
    """tl rm does not call unlinkProjectSession when config disabled."""
    runner.invoke(app, ["init", "--defaults", "--user", "test", "--no-link-session"])
    runner.invoke(app, ["new", "obsidian", "--no-init"])

    with patch("timberline.cli.unlinkProjectSession") as mock_unlink:
        result = runner.invoke(app, ["rm", "obsidian"])
        assert result.exit_code == 0
        mock_unlink.assert_not_called()


# ─── Init prompt/flag tests ──────────────────────────────────────────────────


def test_init_defaults_sets_link_session_false(repo_dir: Path):
    """--defaults sets link_project_session=false."""
    from timberline.config import loadConfig

    result = runner.invoke(app, ["init", "--defaults"])
    assert result.exit_code == 0
    cfg = loadConfig(repo_dir)
    assert cfg.agent.link_project_session is False


def test_init_defaults_sets_auto_launch_false(repo_dir: Path):
    """--defaults sets auto_launch=false."""
    from timberline.config import loadConfig

    result = runner.invoke(app, ["init", "--defaults"])
    assert result.exit_code == 0
    cfg = loadConfig(repo_dir)
    assert cfg.agent.auto_launch is False


def test_init_link_session_flag(repo_dir: Path):
    """--no-link-session overrides default."""
    from timberline.config import loadConfig

    result = runner.invoke(app, ["init", "--defaults", "--no-link-session"])
    assert result.exit_code == 0
    cfg = loadConfig(repo_dir)
    assert cfg.agent.link_project_session is False


def test_init_auto_launch_flag(repo_dir: Path):
    """--auto-launch flag sets auto_launch=true."""
    from timberline.config import loadConfig

    result = runner.invoke(app, ["init", "--defaults", "--auto-launch"])
    assert result.exit_code == 0
    cfg = loadConfig(repo_dir)
    assert cfg.agent.auto_launch is True


# ─── done / unarchive tests ──────────────────────────────────────────────────


def test_done_archives_worktree(repo_dir: Path):
    """tl done --force archives worktree, hides from ls, directory persists."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["new", "obsidian", "--no-init"])

    result = runner.invoke(app, ["done", "--name", "obsidian", "--force"])
    assert result.exit_code == 0
    assert "Archived" in result.output

    # hidden from regular ls
    result = runner.invoke(app, ["ls"])
    assert "obsidian" not in result.output

    # directory still exists
    from timberline.models import getWorktreeBasePath, resolveProjectName

    project = resolveProjectName(repo_dir, repo_dir.name)
    assert (getWorktreeBasePath(project) / "obsidian").exists()


def test_done_with_name_flag(repo_dir: Path):
    """tl done --name works."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["new", "alpha", "--no-init"])

    result = runner.invoke(app, ["done", "--name", "alpha", "--force"])
    assert result.exit_code == 0
    assert "Archived" in result.output
    # stdout should contain repo root for shell cd
    assert str(repo_dir) in result.output


def test_ls_archived_shows_archived(repo_dir: Path):
    """tl ls --archived shows only archived worktrees."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["new", "alpha", "--no-init"])
    runner.invoke(app, ["new", "beta", "--no-init"])
    runner.invoke(app, ["done", "--name", "alpha", "--force"])

    result = runner.invoke(app, ["ls", "--archived"])
    assert result.exit_code == 0
    assert "alpha" in result.output
    assert "beta" not in result.output


def test_unarchive_restores_worktree(repo_dir: Path):
    """tl unarchive restores worktree to active."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["new", "obsidian", "--no-init"])
    runner.invoke(app, ["done", "--name", "obsidian", "--force"])

    result = runner.invoke(app, ["unarchive", "obsidian"])
    assert result.exit_code == 0
    assert "Unarchived" in result.output

    # visible in ls again
    result = runner.invoke(app, ["ls"])
    assert "obsidian" in result.output


def test_rm_on_archived_worktree(repo_dir: Path):
    """tl rm on archived worktree still works (full removal)."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["new", "obsidian", "--no-init"])
    runner.invoke(app, ["done", "--name", "obsidian", "--force"])

    result = runner.invoke(app, ["rm", "obsidian"])
    assert result.exit_code == 0
    assert "Removed" in result.output

    # gone from archived ls too
    result = runner.invoke(app, ["ls", "--archived"])
    assert "obsidian" not in result.output


def test_done_unlinks_agent_session(repo_dir: Path):
    """tl done calls unlinkProjectSession when config enabled."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["config", "set", "agent.link_project_session", "true"])
    runner.invoke(app, ["new", "obsidian", "--no-init"])

    with patch("timberline.cli.unlinkProjectSession") as mock_unlink:
        result = runner.invoke(app, ["done", "--name", "obsidian", "--force"])
        assert result.exit_code == 0
        mock_unlink.assert_called_once()


def test_unarchive_relinks_agent_session(repo_dir: Path):
    """tl unarchive calls linkProjectSession when config enabled."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["config", "set", "agent.link_project_session", "true"])
    runner.invoke(app, ["new", "obsidian", "--no-init"])
    runner.invoke(app, ["done", "--name", "obsidian", "--force"])

    with patch("timberline.cli.linkProjectSession", return_value=True) as mock_link:
        result = runner.invoke(app, ["unarchive", "obsidian"])
        assert result.exit_code == 0
        mock_link.assert_called_once()


def test_shell_init_contains_aliases():
    """Shell init strings contain tld, tlh, and tlunarchive."""
    result = runner.invoke(app, ["shell-init"])
    assert result.exit_code == 0
    assert "tld()" in result.output or "function tld" in result.output
    assert "tlh()" in result.output or "function tlh" in result.output
    assert "tlunarchive" in result.output


def test_done_skips_warning_squash_merged(repo_dir: Path):
    """No unpushed warning when branch was squash-merged."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["new", "obsidian", "--no-init"])

    with (
        patch("timberline.cli.getAheadBehind", return_value=(3, 0)),
        patch("timberline.cli.isBranchMerged", return_value=True),
        patch("timberline.cli.runGit"),
    ):
        result = runner.invoke(app, ["done", "--name", "obsidian"])
        assert result.exit_code == 0
        assert "unpushed" not in result.output
        assert "Archived" in result.output


def test_done_warns_when_not_merged(repo_dir: Path):
    """Unpushed warning shown when branch not squash-merged."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["new", "obsidian", "--no-init"])

    with (
        patch("timberline.cli.getAheadBehind", return_value=(3, 0)),
        patch("timberline.cli.isBranchMerged", return_value=False),
        patch("timberline.cli.runGit"),
    ):
        result = runner.invoke(app, ["done", "--name", "obsidian"], input="n\n")
        assert result.exit_code == 1
        assert "unpushed" in result.output


def test_help_shows_done_unarchive():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "done" in result.output
    assert "unarchive" in result.output
    assert "home" in result.output


def test_home_prints_repo_root(repo_dir: Path):
    result = runner.invoke(app, ["home"])
    assert result.exit_code == 0
    assert str(repo_dir) in result.output


# ─── checkout / co tests ─────────────────────────────────────────────────────


def test_checkout_local_branch(repo_dir: Path):
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runGit("branch", "feature/login", cwd=repo_dir)
    runGit("push", "origin", "feature/login", cwd=repo_dir)

    result = runner.invoke(app, ["checkout", "feature/login", "--no-init"])
    assert result.exit_code == 0
    assert "Checked out" in result.output


def test_checkout_with_name_override(repo_dir: Path):
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runGit("branch", "feature/login", cwd=repo_dir)
    runGit("push", "origin", "feature/login", cwd=repo_dir)

    result = runner.invoke(app, ["checkout", "feature/login", "--name", "myname", "--no-init"])
    assert result.exit_code == 0
    assert "myname" in result.output


def test_checkout_pr_hash_syntax(repo_dir: Path):
    """#42 positional arg parsed as PR number."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])

    with patch("timberline.cli.resolvePrBranch", return_value=("feat/pr-branch", "main")):
        runGit("branch", "feat/pr-branch", cwd=repo_dir)
        runGit("push", "origin", "feat/pr-branch", cwd=repo_dir)
        result = runner.invoke(app, ["checkout", "#42", "--no-init"])
        assert result.exit_code == 0
        assert "Checked out" in result.output


def test_checkout_pr_flag(repo_dir: Path):
    """--pr flag works."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])

    with patch("timberline.cli.resolvePrBranch", return_value=("feat/pr-flag", "main")):
        runGit("branch", "feat/pr-flag", cwd=repo_dir)
        runGit("push", "origin", "feat/pr-flag", cwd=repo_dir)
        result = runner.invoke(app, ["checkout", "--pr", "99", "--no-init"])
        assert result.exit_code == 0
        assert "Checked out" in result.output


def test_checkout_both_pr_args_error(repo_dir: Path):
    """#N and --pr together is an error."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    result = runner.invoke(app, ["checkout", "#42", "--pr", "99"])
    assert result.exit_code == 1
    assert "not both" in result.output


def test_checkout_no_args_error(repo_dir: Path):
    """No branch or PR is an error."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    result = runner.invoke(app, ["checkout"])
    assert result.exit_code == 1
    assert "Specify" in result.output


def test_co_alias(repo_dir: Path):
    """co alias works same as checkout."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runGit("branch", "feature/alias-test", cwd=repo_dir)
    runGit("push", "origin", "feature/alias-test", cwd=repo_dir)

    result = runner.invoke(app, ["co", "feature/alias-test", "--no-init"])
    assert result.exit_code == 0
    assert "Checked out" in result.output


def test_checkout_shows_in_ls(repo_dir: Path):
    """Checked out worktree appears in ls."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runGit("branch", "feature/visible", cwd=repo_dir)
    runGit("push", "origin", "feature/visible", cwd=repo_dir)

    runner.invoke(app, ["checkout", "feature/visible", "--no-init"])
    result = runner.invoke(app, ["ls", "--json"])
    assert result.exit_code == 0
    assert "feature/visible" in result.output


def test_checkout_pr_aware_push(repo_dir: Path):
    """PR-aware push skips gh pr create when wt.pr is set."""
    from timberline.config import loadConfig
    from timberline.worktree import listWorktrees

    runner.invoke(app, ["init", "--defaults", "--user", "test"])

    with patch("timberline.cli.resolvePrBranch", return_value=("feat/pr-push", "main")):
        runGit("branch", "feat/pr-push", cwd=repo_dir)
        runGit("push", "origin", "feat/pr-push", cwd=repo_dir)
        runner.invoke(app, ["checkout", "#42", "--no-init"])

    # get generated worktree name from state
    cfg = loadConfig(repo_dir)
    wts = listWorktrees(repo_dir, cfg)
    wt_name = wts[0].name

    with (
        patch("timberline.cli.runGit"),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "https://github.com/org/repo/pull/42"
        runner.invoke(app, ["pr", "--name", wt_name])
        # should NOT try gh pr create — should push + show existing PR
        for call in mock_run.call_args_list:
            args = call[0][0] if call[0] else call[1].get("args", [])
            assert "create" not in args


def test_help_shows_checkout():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "checkout" in result.output


def test_shell_init_contains_tlc():
    result = runner.invoke(app, ["shell-init"])
    assert result.exit_code == 0
    assert "tlc()" in result.output or "function tlc" in result.output
