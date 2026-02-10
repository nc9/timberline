from __future__ import annotations

import warnings
from pathlib import Path

from timberline.config import (
    configExists,
    loadConfig,
    updateConfigField,
    writeConfig,
    writeInitConfig,
)
from timberline.models import AgentConfig, NamingScheme, TimberlineConfig


def test_configExists_false(tmp_path: Path):
    assert not configExists(tmp_path)


def test_configExists_true(tmp_path: Path):
    (tmp_path / ".timberline.toml").write_text("[timberline]\n")
    assert configExists(tmp_path)


def test_loadConfig_defaults(tmp_path: Path):
    cfg = loadConfig(tmp_path)
    assert cfg.worktree_dir == ".tl"
    assert cfg.naming_scheme == NamingScheme.COMPOUND
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


def test_writeConfig_context_file_roundTrip(tmp_path: Path):
    cfg = TimberlineConfig(
        default_agent="cc",
        agent=AgentConfig(context_file="CLAUDE.md"),
    )
    writeConfig(tmp_path, cfg)
    loaded = loadConfig(tmp_path)
    assert loaded.default_agent == "cc"
    assert loaded.agent.context_file == "CLAUDE.md"


def test_writeConfig_context_file_none_omitted(tmp_path: Path):
    cfg = TimberlineConfig(default_agent="z")
    writeConfig(tmp_path, cfg)
    content = (tmp_path / ".timberline.toml").read_text()
    assert "context_file" not in content
    loaded = loadConfig(tmp_path)
    assert loaded.agent.context_file is None


def test_updateConfigField(tmp_path: Path):
    cfg = TimberlineConfig(user="old")
    writeConfig(tmp_path, cfg)

    updated = updateConfigField(tmp_path, "user", "new")
    assert updated.user == "new"

    # verify persisted
    reloaded = loadConfig(tmp_path)
    assert reloaded.user == "new"


# ─── New tests ────────────────────────────────────────────────────────────────


def test_updateConfigField_dotNotation(tmp_path: Path):
    cfg = TimberlineConfig()
    writeConfig(tmp_path, cfg)

    updated = updateConfigField(tmp_path, "env.auto_copy", "false")
    assert updated.env.auto_copy is False

    reloaded = loadConfig(tmp_path)
    assert reloaded.env.auto_copy is False


def test_updateConfigField_bool(tmp_path: Path):
    cfg = TimberlineConfig()
    writeConfig(tmp_path, cfg)

    updated = updateConfigField(tmp_path, "agent.auto_launch", "true")
    assert updated.agent.auto_launch is True


def test_loadConfig_unknownKey_warns(tmp_path: Path):
    (tmp_path / ".timberline.toml").write_text(
        '[timberline]\nunknown_field = "val"\nuser = "test"\n'
    )
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        cfg = loadConfig(tmp_path)
        assert cfg.user == "test"
        assert any("Unknown config key: 'unknown_field'" in str(warning.message) for warning in w)


def test_writeInitConfig_commented(tmp_path: Path):
    from timberline.models import InitConfig

    cfg = TimberlineConfig(
        user="nc9",
        base_branch="main",
        default_agent="claude",
        pre_land="make check",
        init=InitConfig(init_command="uv sync"),
    )
    writeInitConfig(tmp_path, cfg)
    content = (tmp_path / ".timberline.toml").read_text()

    # non-default values written directly
    assert 'user = "nc9"' in content
    assert 'pre_land = "make check"' in content
    assert 'init_command = "uv sync"' in content

    # defaults commented out
    assert "# worktree_dir" in content
    assert "# auto_init" in content

    # roundtrip: should load back correctly
    loaded = loadConfig(tmp_path)
    assert loaded.user == "nc9"
    assert loaded.pre_land == "make check"
    assert loaded.init.init_command == "uv sync"
