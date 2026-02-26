from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def tmp_git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repo with a bare remote and initial commit."""
    bare = tmp_path / "remote.git"
    bare.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=bare, capture_output=True, check=True)

    repo = tmp_path / "repo"
    subprocess.run(
        ["git", "clone", str(bare), str(repo)], cwd=tmp_path, capture_output=True, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=repo, capture_output=True, check=True
    )
    subprocess.run(["git", "checkout", "-b", "main"], cwd=repo, capture_output=True, check=True)
    (repo / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "push", "-u", "origin", "main"], cwd=repo, capture_output=True, check=True
    )
    return repo


@pytest.fixture(autouse=True)
def tl_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect TIMBERLINE_HOME to temp dir for all tests."""
    home = tmp_path / ".timberline"
    monkeypatch.setenv("TIMBERLINE_HOME", str(home))
    return home
