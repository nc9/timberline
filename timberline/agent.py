from __future__ import annotations

import os
import shutil
from pathlib import Path

from timberline.models import AgentDef, WorktreeInfo

_MARKER_START = "<!-- timberline:start -->"
_MARKER_END = "<!-- timberline:end -->"

DEFAULT_CONTEXT_FILE = "AGENTS.md"

KNOWN_AGENTS: dict[str, AgentDef] = {
    "claude": AgentDef(binary="claude", context_file="CLAUDE.md"),
    "codex": AgentDef(binary="codex", context_file="AGENTS.md"),
    "opencode": AgentDef(binary="opencode", context_file="AGENTS.md"),
    "aider": AgentDef(binary="aider", context_file="CONVENTIONS.md"),
}


def detectInstalledAgents() -> list[str]:
    """Return names of known agents whose binary is on PATH."""
    return [name for name, defn in KNOWN_AGENTS.items() if shutil.which(defn.binary)]


def getAgentDef(name: str, context_file_override: str | None = None) -> AgentDef:
    """Lookup agent definition by name. Unknown agents use DEFAULT_CONTEXT_FILE."""
    if name in KNOWN_AGENTS:
        defn = KNOWN_AGENTS[name]
        if context_file_override:
            return AgentDef(binary=defn.binary, context_file=context_file_override)
        return defn
    return AgentDef(
        binary=name,
        context_file=context_file_override or DEFAULT_CONTEXT_FILE,
    )


def validateAgentBinary(name: str) -> str | None:
    """Check if agent binary exists on PATH. Returns path or None."""
    if name in KNOWN_AGENTS:
        return shutil.which(KNOWN_AGENTS[name].binary)
    return shutil.which(name)


def buildEnvVars(info: WorktreeInfo, repo_root: Path) -> dict[str, str]:
    return {
        "TL_WORKTREE": info.name,
        "TL_BRANCH": info.branch,
        "TL_BASE": info.base_branch,
        "TL_ROOT": str(repo_root),
        "TL_TYPE": info.type,
    }


def buildContextBlock(
    info: WorktreeInfo, all_worktrees: list[WorktreeInfo], repo_root: Path
) -> str:
    others = [wt.name for wt in all_worktrees if wt.name != info.name]
    others_str = ", ".join(others) if others else "none"

    return f"""{_MARKER_START}

# Timberline Worktree Context

You are working in a **Timberline-managed git worktree**.

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

- `tl status` — see all worktrees and their git status
- `tl sync` — rebase this worktree onto the latest base branch
- `tl env sync` — refresh .env files from the main repo
- `tl ls` — list all active worktrees

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
