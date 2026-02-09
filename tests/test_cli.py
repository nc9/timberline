from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from timberline.cli import app

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


def test_init_creates_gitignore_entry(repo_dir: Path):
    result = runner.invoke(app, ["init", "--defaults"])
    assert result.exit_code == 0
    content = (repo_dir / ".gitignore").read_text()
    assert ".tl/" in content


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
    # stdout path is last line (bare print)
    lines = result.output.strip().splitlines()
    assert any("obsidian" in line and str(repo_dir) in line for line in lines)


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
