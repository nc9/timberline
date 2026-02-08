from __future__ import annotations

from pathlib import Path

from lumberjack.init_deps import (
    detectInstaller,
    findProjectDirs,
    isDifferentEcosystem,
)


def test_detectInstaller_bun(tmp_path: Path):
    (tmp_path / "bun.lock").write_text("")
    assert detectInstaller(tmp_path) == ["bun", "install"]


def test_detectInstaller_npm(tmp_path: Path):
    (tmp_path / "package-lock.json").write_text("{}")
    assert detectInstaller(tmp_path) == ["npm", "install"]


def test_detectInstaller_uv(tmp_path: Path):
    (tmp_path / "uv.lock").write_text("")
    (tmp_path / "pyproject.toml").write_text("")
    assert detectInstaller(tmp_path) == ["uv", "sync"]


def test_detectInstaller_requirements(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("flask")
    assert detectInstaller(tmp_path) == ["uv", "pip", "install", "-r", "requirements.txt"]


def test_detectInstaller_none(tmp_path: Path):
    assert detectInstaller(tmp_path) is None


def test_detectInstaller_priority(tmp_path: Path):
    """bun.lock takes priority over package-lock.json."""
    (tmp_path / "bun.lock").write_text("")
    (tmp_path / "package-lock.json").write_text("{}")
    assert detectInstaller(tmp_path) == ["bun", "install"]


def test_isDifferentEcosystem():
    assert isDifferentEcosystem(["bun", "install"], ["uv", "sync"])
    assert not isDifferentEcosystem(["bun", "install"], ["npm", "install"])
    assert not isDifferentEcosystem(["uv", "sync"], ["uv", "pip", "install"])
    assert isDifferentEcosystem(None, ["bun", "install"])


def test_findProjectDirs(tmp_path: Path):
    # root has bun
    (tmp_path / "package.json").write_text("{}")
    # subdir has python
    sub = tmp_path / "apps" / "ml"
    sub.mkdir(parents=True)
    (sub / "pyproject.toml").write_text("")

    dirs = findProjectDirs(tmp_path)
    assert sub in dirs


def test_findProjectDirs_skips_node_modules(tmp_path: Path):
    nm = tmp_path / "node_modules" / "pkg"
    nm.mkdir(parents=True)
    (nm / "package.json").write_text("{}")

    assert findProjectDirs(tmp_path) == []
