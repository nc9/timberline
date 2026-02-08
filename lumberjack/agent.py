from __future__ import annotations

import os
import shutil
from pathlib import Path

from lumberjack.types import AgentDef, WorktreeInfo

_MARKER_START = "<!-- lumberjack:start -->"
_MARKER_END = "<!-- lumberjack:end -->"

KNOWN_AGENTS: dict[str, AgentDef] = {
    "claude": AgentDef(binary="claude", context_file="CLAUDE.md"),
    "codex": AgentDef(binary="codex", context_file="AGENTS.md"),
    "opencode": AgentDef(binary="opencode", context_file="AGENTS.md"),
    "aider": AgentDef(binary="aider", context_file="CONVENTIONS.md"),
}


def detectInstalledAgents() -> list[str]:
    """Return names of known agents whose binary is on PATH."""
    return [name for name, defn in KNOWN_AGENTS.items() if shutil.which(defn.binary)]


def getAgentDef(name: str) -> AgentDef:
    """Lookup agent definition by name. Raises KeyError if unknown."""
    if name not in KNOWN_AGENTS:
        msg = f"Unknown agent '{name}'. Known: {', '.join(KNOWN_AGENTS)}"
        raise KeyError(msg)
    return KNOWN_AGENTS[name]


def buildEnvVars(info: WorktreeInfo, repo_root: Path) -> dict[str, str]:
    return {
        "LJ_WORKTREE": info.name,
        "LJ_BRANCH": info.branch,
        "LJ_BASE": info.base_branch,
        "LJ_ROOT": str(repo_root),
        "LJ_TYPE": info.type,
    }


def buildContextBlock(
    info: WorktreeInfo, all_worktrees: list[WorktreeInfo], repo_root: Path
) -> str:
    others = [wt.name for wt in all_worktrees if wt.name != info.name]
    others_str = ", ".join(others) if others else "none"

    return f"""{_MARKER_START}

# Lumberjack Worktree Context

You are working in a **Lumberjack-managed git worktree**.

| Key         | Value                            |
|-------------|----------------------------------|
| Worktree    | {info.name} |
| Branch      | {info.branch} |
| Base branch | {info.base_branch} |
| Main repo   | {repo_root} |

## Guidelines

- This is an isolated worktree. Changes here do not affect other worktrees or the main checkout.
- Commit to this branch (`{info.branch}`). It can be merged via PR.
- The main repo is at `{repo_root}` — reference it read-only if needed.
- Other active worktrees: {others_str}. Do not modify those.

## Useful Commands

- `lj status` — see all worktrees and their git status
- `lj sync` — rebase this worktree onto the latest base branch
- `lj env sync` — refresh .env files from the main repo
- `lj ls` — list all active worktrees

{_MARKER_END}"""


def injectAgentContext(
    agent: AgentDef,
    worktree_path: Path,
    info: WorktreeInfo,
    all_worktrees: list[WorktreeInfo],
    repo_root: Path,
) -> None:
    context_file = worktree_path / agent.context_file
    block = buildContextBlock(info, all_worktrees, repo_root)

    if context_file.exists():
        content = context_file.read_text()
        if _MARKER_START in content and _MARKER_END in content:
            before = content[: content.index(_MARKER_START)]
            after = content[content.index(_MARKER_END) + len(_MARKER_END) :]
            content = before + block + after
        else:
            content = content.rstrip() + "\n\n" + block + "\n"
        context_file.write_text(content)
    else:
        context_file.write_text(block + "\n")


def launchAgent(agent: AgentDef, worktree_path: Path, env_vars: dict[str, str]) -> None:
    env = {**os.environ, **env_vars}
    os.chdir(worktree_path)
    os.execvpe(agent.binary, [agent.binary], env)
