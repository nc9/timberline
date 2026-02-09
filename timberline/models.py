from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class _StrictConfig(BaseModel):
    """Base that warns on unknown keys and strips them."""

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="before")
    @classmethod
    def warnUnknownKeys(cls, data: object) -> object:
        if isinstance(data, dict):
            known = set(cls.model_fields.keys())
            for key in sorted(set(data.keys()) - known):
                warnings.warn(f"Unknown config key: '{key}'", stacklevel=2)
            return {k: v for k, v in data.items() if k in known}
        return data


class InitConfig(_StrictConfig):
    init_command: str | None = Field(
        None, description="Command to run in new worktrees (e.g. 'uv sync', 'npm install')"
    )
    auto_init: bool = Field(True, description="Auto-run init_command when creating worktrees")
    post_init: list[str] = Field(
        default_factory=list, description="Additional commands to run after init_command"
    )


class EnvConfig(_StrictConfig):
    auto_copy: bool = Field(True, description="Copy .env files into new worktrees")
    patterns: list[str] = Field(
        default_factory=lambda: [".env", ".env.*", "!.env.example", "!.env.template"],
        description="Glob patterns for env files (prefix ! to exclude)",
    )
    scan_depth: int = Field(3, description="Directory depth to scan for env files")
    scan_dirs: list[str] | None = Field(
        None, description="Specific directories to scan (default: repo root)"
    )

    @field_validator("scan_depth")
    @classmethod
    def scanDepthPositive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("scan_depth must be >= 1")
        return v


class SubmodulesConfig(_StrictConfig):
    auto_init: bool = Field(True, description="Auto-init submodules in new worktrees")
    recursive: bool = Field(True, description="Recursively init nested submodules")


class AgentConfig(_StrictConfig):
    auto_launch: bool = Field(False, description="Launch coding agent after creating worktree")
    inject_context: bool = Field(True, description="Inject worktree context file for the agent")
    context_file: str | None = Field(
        None, description="Custom context file path (default: agent-specific)"
    )


class TimberlineConfig(_StrictConfig):
    worktree_dir: str = Field(".tl", description="Directory for worktrees (relative to repo root)")
    branch_template: str = Field(
        "{user}/{type}/{name}",
        description="Branch name template. Must contain {name}. Vars: {user}, {type}, {name}",
    )
    user: str = Field("", description="Username prefix for branches")
    default_type: str = Field(
        "feature", description="Default branch type (feature, fix, hotfix, chore, refactor)"
    )
    base_branch: str = Field("main", description="Base branch to create worktrees from")
    naming_scheme: NamingScheme = Field(
        NamingScheme.MINERALS, description="Auto-name scheme: minerals, cities, or compound"
    )
    default_agent: str = Field(
        "claude", description="Coding agent to launch (claude, codex, aider, opencode)"
    )
    pre_land: str | None = Field(
        None, description="Command to run before landing (e.g. 'make check')"
    )
    init: InitConfig = Field(
        default_factory=lambda: InitConfig(), description="Worktree initialization settings"
    )
    env: EnvConfig = Field(
        default_factory=lambda: EnvConfig(), description="Environment file copying settings"
    )
    submodules: SubmodulesConfig = Field(
        default_factory=lambda: SubmodulesConfig(), description="Git submodule settings"
    )
    agent: AgentConfig = Field(
        default_factory=lambda: AgentConfig(), description="Coding agent settings"
    )

    @field_validator("branch_template")
    @classmethod
    def branchTemplateHasName(cls, v: str) -> str:
        if "{name}" not in v:
            raise ValueError("branch_template must contain {name}")
        return v


@dataclass(frozen=True)
class AgentDef:
    binary: str
    context_file: str


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


class TimberlineError(Exception):
    pass
