from __future__ import annotations

import tomllib
from enum import StrEnum
from pathlib import Path

import tomlkit
from pydantic import BaseModel

from timberline.models import (
    AgentConfig,
    EnvConfig,
    InitConfig,
    SubmodulesConfig,
    TimberlineConfig,
)

CONFIG_FILENAME = ".timberline.toml"
GLOBAL_CONFIG_PATH = Path.home() / ".config" / "timberline" / "config.toml"

_NESTED_SECTIONS = {
    "init": InitConfig,
    "env": EnvConfig,
    "submodules": SubmodulesConfig,
    "agent": AgentConfig,
}


def configExists(repo_root: Path) -> bool:
    return (repo_root / CONFIG_FILENAME).exists()


def loadConfig(repo_root: Path) -> TimberlineConfig:
    """Load config: repo .timberline.toml > global config > defaults."""
    data: dict = {}

    # global config
    if GLOBAL_CONFIG_PATH.exists():
        with open(GLOBAL_CONFIG_PATH, "rb") as f:
            global_data = tomllib.load(f)
        data.update(global_data.get("timberline", {}))

    # repo config — deep-merge nested dicts
    repo_config = repo_root / CONFIG_FILENAME
    if repo_config.exists():
        with open(repo_config, "rb") as f:
            repo_data = tomllib.load(f)
        repo_tl = repo_data.get("timberline", {})
        for key, val in repo_tl.items():
            if isinstance(val, dict) and isinstance(data.get(key), dict):
                data[key] = {**data[key], **val}
            else:
                data[key] = val

    return TimberlineConfig.model_validate(data)


def _buildTomlDocument(config: TimberlineConfig) -> tomlkit.TOMLDocument:
    """Build a tomlkit document with comments from Field descriptions."""
    doc = tomlkit.document()
    tl = tomlkit.table()

    for name, field_info in TimberlineConfig.model_fields.items():
        if name in _NESTED_SECTIONS:
            continue
        val = getattr(config, name)
        if val is None:
            continue
        desc = field_info.description
        if desc:
            tl.add(tomlkit.comment(desc))
        tl.add(name, _tomlValue(val))

    # nested sections
    for section_name, model_cls in _NESTED_SECTIONS.items():
        sub_config = getattr(config, section_name)
        sub_table = tomlkit.table()
        for name, field_info in model_cls.model_fields.items():
            val = getattr(sub_config, name)
            if val is None:
                continue
            desc = field_info.description
            if desc:
                sub_table.add(tomlkit.comment(desc))
            sub_table.add(name, _tomlValue(val))
        if sub_table:
            tl.add(section_name, sub_table)

    doc.add("timberline", tl)
    return doc


def _tomlValue(val: object) -> object:
    """Convert Python values to TOML-compatible types."""
    if isinstance(val, bool):
        return val
    if isinstance(val, BaseModel):
        return val.model_dump()
    if isinstance(val, StrEnum):
        return val.value
    if isinstance(val, list):
        return list(val)
    return val


def writeConfig(repo_root: Path, config: TimberlineConfig) -> Path:
    path = repo_root / CONFIG_FILENAME
    doc = _buildTomlDocument(config)
    path.write_text(tomlkit.dumps(doc))
    return path


def writeInitConfig(repo_root: Path, config: TimberlineConfig) -> Path:
    """Write minimal config with commented-out defaults for self-documentation."""
    path = repo_root / CONFIG_FILENAME
    defaults = TimberlineConfig()
    doc = tomlkit.document()
    tl = tomlkit.table()

    # top-level: write non-default values, comment out defaults
    for name, field_info in TimberlineConfig.model_fields.items():
        if name in _NESTED_SECTIONS:
            continue
        val = getattr(config, name)
        default_val = getattr(defaults, name)
        desc = field_info.description or ""

        if val != default_val and val is not None:
            tl.add(name, _tomlValue(val))
        elif val is None:
            continue
        else:
            tl.add(tomlkit.comment(f"{name} = {_formatTomlLiteral(default_val)}  # {desc}"))

    # nested sections
    for section_name, model_cls in _NESTED_SECTIONS.items():
        sub_config = getattr(config, section_name)
        sub_defaults = getattr(defaults, section_name)
        sub_table = tomlkit.table()
        has_non_default = False

        for name, field_info in model_cls.model_fields.items():
            val = getattr(sub_config, name)
            default_val = getattr(sub_defaults, name)
            desc = field_info.description or ""

            if val != default_val and val is not None:
                sub_table.add(name, _tomlValue(val))
                has_non_default = True
            elif val is None:
                continue
            else:
                sub_table.add(
                    tomlkit.comment(f"{name} = {_formatTomlLiteral(default_val)}  # {desc}")
                )

        # only add section if it has non-default values or useful comments
        if has_non_default or sub_table:
            tl.add(section_name, sub_table)

    doc.add("timberline", tl)
    path.write_text(tomlkit.dumps(doc))
    return path


def _formatTomlLiteral(val: object) -> str:
    """Format a value as a TOML literal string for commented-out lines."""
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, str):
        return f'"{val}"'
    if isinstance(val, int):
        return str(val)
    if isinstance(val, list):
        items = ", ".join(f'"{v}"' if isinstance(v, str) else str(v) for v in val)
        return f"[{items}]"
    if isinstance(val, StrEnum):
        return f'"{val.value}"'
    return str(val)


def _coerceValue(value: str) -> str | bool | int:
    """Coerce CLI string to appropriate type."""
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    try:
        return int(value)
    except ValueError:
        return value


def updateConfigField(repo_root: Path, key: str, value: str) -> TimberlineConfig:
    """Update a config field. Supports dot-notation (e.g. 'env.auto_copy')."""
    config_path = repo_root / CONFIG_FILENAME
    if config_path.exists():
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    else:
        data = {"timberline": {}}

    coerced = _coerceValue(value)
    tl = data.setdefault("timberline", {})

    parts = key.split(".", maxsplit=1)
    if len(parts) == 2:
        section, field_name = parts
        tl.setdefault(section, {})[field_name] = coerced
    else:
        tl[key] = coerced

    config_path.write_text(tomlkit.dumps(data))
    return loadConfig(repo_root)
