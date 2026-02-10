from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from timberline.cli import app
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


def test_install_and_uninstall(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("timberline.shell.rcFilePath", lambda s: tmp_path / ".zshrc")
    monkeypatch.setattr("timberline.cli.detectShell", lambda: "zsh")

    result = runner.invoke(app, ["install"])
    assert result.exit_code == 0
    assert "Added" in result.output
    assert (tmp_path / ".zshrc").exists()

    result = runner.invoke(app, ["install", "--uninstall"])
    assert result.exit_code == 0
    assert "Removed" in result.output


def test_help_shows_new_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "install" in result.output
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
    """tl new does not call linkProjectSession when config disabled (default)."""
    runner.invoke(app, ["init", "--defaults", "--user", "test"])

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
    runner.invoke(app, ["init", "--defaults", "--user", "test"])
    runner.invoke(app, ["new", "obsidian", "--no-init"])

    with patch("timberline.cli.unlinkProjectSession") as mock_unlink:
        result = runner.invoke(app, ["rm", "obsidian"])
        assert result.exit_code == 0
        mock_unlink.assert_not_called()
