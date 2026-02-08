from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class NamingScheme(StrEnum):
    MINERALS = "minerals"
    CITIES = "cities"
    COMPOUND = "compound"


class BranchType(StrEnum):
    FEATURE = "feature"
    FIX = "fix"
    HOTFIX = "hotfix"
    CHORE = "chore"
    REFACTOR = "refactor"


@dataclass(frozen=True)
class InitConfig:
    init_command: str | None = None
    auto_init: bool = True
    post_init: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EnvConfig:
    auto_copy: bool = True
    patterns: list[str] = field(
        default_factory=lambda: [".env", ".env.*", "!.env.example", "!.env.template"]
    )
    scan_depth: int = 3
    scan_dirs: list[str] | None = None


@dataclass(frozen=True)
class SubmodulesConfig:
    auto_init: bool = True
    recursive: bool = True


@dataclass(frozen=True)
class AgentDef:
    binary: str
    context_file: str


@dataclass(frozen=True)
class AgentConfig:
    auto_launch: bool = False
    inject_context: bool = True


@dataclass(frozen=True)
class LumberjackConfig:
    worktree_dir: str = ".lj"
    branch_template: str = "{user}/{type}/{name}"
    user: str = ""
    default_type: str = "feature"
    base_branch: str = "main"
    naming_scheme: NamingScheme = NamingScheme.MINERALS
    default_agent: str = "claude"
    init: InitConfig = field(default_factory=InitConfig)
    env: EnvConfig = field(default_factory=EnvConfig)
    submodules: SubmodulesConfig = field(default_factory=SubmodulesConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)


@dataclass
class WorktreeInfo:
    name: str
    branch: str
    base_branch: str
    type: str
    path: str
    created_at: str = ""
    status: str = ""
    ahead: int = 0
    behind: int = 0


@dataclass(frozen=True)
class StateFile:
    version: int = 1
    repo_root: str = ""
    worktrees: dict[str, dict[str, str]] = field(default_factory=dict)


class LumberjackError(Exception):
    pass
