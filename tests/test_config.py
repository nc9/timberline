from __future__ import annotations

from pathlib import Path

from timberline.config import configExists, loadConfig, updateConfigField, writeConfig
from timberline.types import NamingScheme, TimberlineConfig


def test_configExists_false(tmp_path: Path):
    assert not configExists(tmp_path)


def test_configExists_true(tmp_path: Path):
    (tmp_path / ".timberline.toml").write_text("[timberline]\n")
    assert configExists(tmp_path)


def test_loadConfig_defaults(tmp_path: Path):
    cfg = loadConfig(tmp_path)
    assert cfg.worktree_dir == ".tl"
    assert cfg.naming_scheme == NamingScheme.MINERALS
    assert cfg.init.auto_init is True


def test_writeConfig_roundTrip(tmp_path: Path):
    cfg = TimberlineConfig(user="nik", base_branch="develop", naming_scheme=NamingScheme.CITIES)
    writeConfig(tmp_path, cfg)

    loaded = loadConfig(tmp_path)
    assert loaded.user == "nik"
    assert loaded.base_branch == "develop"
    assert loaded.naming_scheme == NamingScheme.CITIES


def test_writeConfig_partial_override(tmp_path: Path):
    # write full config, then load — ensure nested configs survive
    cfg = TimberlineConfig(user="test")
    writeConfig(tmp_path, cfg)

    loaded = loadConfig(tmp_path)
    assert loaded.user == "test"
    assert loaded.env.auto_copy is True  # default preserved


def test_updateConfigField(tmp_path: Path):
    cfg = TimberlineConfig(user="old")
    writeConfig(tmp_path, cfg)

    updated = updateConfigField(tmp_path, "user", "new")
    assert updated.user == "new"

    # verify persisted
    reloaded = loadConfig(tmp_path)
    assert reloaded.user == "new"
