from __future__ import annotations

from pathlib import Path

from lumberjack.env import copyEnvFiles, diffEnvFiles, discoverEnvFiles
from lumberjack.types import EnvConfig


def test_discoverEnvFiles_basic(tmp_path: Path):
    (tmp_path / ".env").write_text("KEY=val")
    (tmp_path / ".env.local").write_text("KEY=val")
    (tmp_path / ".env.example").write_text("KEY=")

    config = EnvConfig()
    files = discoverEnvFiles(tmp_path, config)
    names = [f.name for f in files]
    assert ".env" in names
    assert ".env.local" in names
    assert ".env.example" not in names  # excluded


def test_discoverEnvFiles_nested(tmp_path: Path):
    sub = tmp_path / "apps" / "web"
    sub.mkdir(parents=True)
    (sub / ".env").write_text("KEY=val")

    config = EnvConfig()
    files = discoverEnvFiles(tmp_path, config)
    assert any("apps" in str(f) for f in files)


def test_discoverEnvFiles_depth_limit(tmp_path: Path):
    deep = tmp_path / "a" / "b" / "c" / "d" / "e"
    deep.mkdir(parents=True)
    (deep / ".env").write_text("KEY=val")

    config = EnvConfig(scan_depth=2)
    files = discoverEnvFiles(tmp_path, config)
    assert not any("e" in str(f) for f in files)


def test_discoverEnvFiles_skip_lj(tmp_path: Path):
    lj_dir = tmp_path / ".lj" / "worktree"
    lj_dir.mkdir(parents=True)
    (lj_dir / ".env").write_text("KEY=val")

    config = EnvConfig()
    files = discoverEnvFiles(tmp_path, config)
    assert not any(".lj" in str(f) for f in files)


def test_copyEnvFiles(tmp_path: Path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()

    (src / ".env").write_text("KEY=val")
    sub = src / "apps" / "web"
    sub.mkdir(parents=True)
    (sub / ".env").write_text("KEY2=val2")

    env_files = [Path(".env"), Path("apps/web/.env")]
    copied = copyEnvFiles(src, dst, env_files)
    assert copied == 2
    assert (dst / ".env").read_text() == "KEY=val"
    assert (dst / "apps" / "web" / ".env").read_text() == "KEY2=val2"


def test_diffEnvFiles(tmp_path: Path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()

    (src / ".env").write_text("KEY=val")
    (src / ".env.local").write_text("A=1")
    (dst / ".env").write_text("KEY=val")
    # .env.local missing from dst

    env_files = [Path(".env"), Path(".env.local")]
    diff = diffEnvFiles(src, dst, env_files)
    assert diff[".env"] == "same"
    assert diff[".env.local"] == "missing"
