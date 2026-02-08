from __future__ import annotations

import tomllib
from pathlib import Path

import tomli_w

from lumberjack.types import (
    AgentConfig,
    EnvConfig,
    InitConfig,
    LumberjackConfig,
    NamingScheme,
    SubmodulesConfig,
)

CONFIG_FILENAME = ".lumberjack.toml"
GLOBAL_CONFIG_PATH = Path.home() / ".config" / "lumberjack" / "config.toml"

DEFAULT_CONFIG = LumberjackConfig()


def configExists(repo_root: Path) -> bool:
    return (repo_root / CONFIG_FILENAME).exists()


def loadConfig(repo_root: Path) -> LumberjackConfig:
    """Load config: repo .lumberjack.toml > global config > defaults."""
    data: dict = {}

    # global config
    if GLOBAL_CONFIG_PATH.exists():
        with open(GLOBAL_CONFIG_PATH, "rb") as f:
            global_data = tomllib.load(f)
        data.update(global_data.get("lumberjack", {}))

    # repo config
    repo_config = repo_root / CONFIG_FILENAME
    if repo_config.exists():
        with open(repo_config, "rb") as f:
            repo_data = tomllib.load(f)
        data.update(repo_data.get("lumberjack", {}))

    return _parseConfig(data)


def _parseConfig(data: dict) -> LumberjackConfig:
    init_data = data.pop("init", {})
    env_data = data.pop("env", {})
    sub_data = data.pop("submodules", {})
    agent_data = data.pop("agent", {})

    naming = data.pop("naming_scheme", DEFAULT_CONFIG.naming_scheme)
    if isinstance(naming, str):
        naming = NamingScheme(naming)

    return LumberjackConfig(
        worktree_dir=data.get("worktree_dir", DEFAULT_CONFIG.worktree_dir),
        branch_template=data.get("branch_template", DEFAULT_CONFIG.branch_template),
        user=data.get("user", DEFAULT_CONFIG.user),
        default_type=data.get("default_type", DEFAULT_CONFIG.default_type),
        base_branch=data.get("base_branch", DEFAULT_CONFIG.base_branch),
        naming_scheme=naming,
        default_agent=data.get("default_agent", DEFAULT_CONFIG.default_agent),
        init=InitConfig(
            init_command=init_data.get("init_command"),
            auto_init=init_data.get("auto_init", True),
            post_init=init_data.get("post_init", []),
        ),
        env=EnvConfig(
            auto_copy=env_data.get("auto_copy", True),
            patterns=env_data.get("patterns", DEFAULT_CONFIG.env.patterns),
            scan_depth=env_data.get("scan_depth", DEFAULT_CONFIG.env.scan_depth),
            scan_dirs=env_data.get("scan_dirs"),
        ),
        submodules=SubmodulesConfig(
            auto_init=sub_data.get("auto_init", True),
            recursive=sub_data.get("recursive", True),
        ),
        agent=AgentConfig(
            auto_launch=agent_data.get("auto_launch", False),
            inject_context=agent_data.get("inject_context", True),
        ),
    )


def writeConfig(repo_root: Path, config: LumberjackConfig) -> Path:
    path = repo_root / CONFIG_FILENAME
    data = _serializeConfig(config)
    path.write_bytes(tomli_w.dumps(data).encode())
    return path


def _serializeConfig(config: LumberjackConfig) -> dict:
    lj: dict = {
        "worktree_dir": config.worktree_dir,
        "branch_template": config.branch_template,
        "user": config.user,
        "default_type": config.default_type,
        "base_branch": config.base_branch,
        "naming_scheme": config.naming_scheme.value,
        "default_agent": config.default_agent,
    }

    init: dict = {}
    if config.init.init_command:
        init["init_command"] = config.init.init_command
    init["auto_init"] = config.init.auto_init
    if config.init.post_init:
        init["post_init"] = config.init.post_init
    lj["init"] = init

    lj["env"] = {
        "auto_copy": config.env.auto_copy,
        "patterns": list(config.env.patterns),
        "scan_depth": config.env.scan_depth,
    }
    if config.env.scan_dirs:
        lj["env"]["scan_dirs"] = list(config.env.scan_dirs)

    lj["submodules"] = {
        "auto_init": config.submodules.auto_init,
        "recursive": config.submodules.recursive,
    }

    lj["agent"] = {
        "auto_launch": config.agent.auto_launch,
        "inject_context": config.agent.inject_context,
    }

    return {"lumberjack": lj}


def updateConfigField(repo_root: Path, key: str, value: str) -> LumberjackConfig:
    """Update a single top-level config field."""
    config_path = repo_root / CONFIG_FILENAME
    if config_path.exists():
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    else:
        data = {"lumberjack": {}}

    data.setdefault("lumberjack", {})[key] = value
    config_path.write_bytes(tomli_w.dumps(data).encode())
    return loadConfig(repo_root)
