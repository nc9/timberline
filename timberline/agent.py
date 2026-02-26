from __future__ import annotations

import os
import re
import shlex
import shutil
from collections.abc import Callable
from pathlib import Path

from timberline.models import AgentDef, WorktreeInfo

_MARKER_START = "<!-- timberline:start -->"
_MARKER_END = "<!-- timberline:end -->"

DEFAULT_CONTEXT_FILE = "AGENTS.md"

KNOWN_AGENTS: dict[str, AgentDef] = {
    "claude": AgentDef(binary="claude", context_file=".claude/rules/worktrees.md"),
    "codex": AgentDef(binary="codex", context_file="AGENTS.md"),
    "gemini": AgentDef(binary="gemini", context_file="GEMINI.md"),
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
    info: WorktreeInfo, all_worktrees: list[WorktreeInfo], project_name: str
) -> str:
    others = [wt.name for wt in all_worktrees if wt.name != info.name]
    others_str = ", ".join(others) if others else "none"
    mode_desc = "local clone" if info.mode == "checkout" else "git worktree"

    return f"""{_MARKER_START}

# Timberline Worktree Context

You are working in a **Timberline-managed {mode_desc}**.

| Key         | Value                            |
|-------------|----------------------------------|
| Project     | {project_name} |
| Worktree    | {info.name} |
| Branch      | {info.branch} |
| Base branch | {info.base_branch} |

## Guidelines

- Your working directory is this worktree. All file operations MUST stay within this directory.
- Do NOT write files outside this worktree.
- Commit to this branch (`{info.branch}`). It can be merged via PR.
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
    project_name: str,
) -> None:
    context_file = worktree_path / agent.context_file
    block = buildContextBlock(info, all_worktrees, project_name)

    context_file.parent.mkdir(parents=True, exist_ok=True)
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


def launchAgent(
    agent: AgentDef,
    worktree_path: Path,
    env_vars: dict[str, str],
    command: str | None = None,
) -> None:
    env = {**os.environ, **env_vars}
    os.chdir(worktree_path)
    if command:
        parts = shlex.split(command)
        os.execvpe(parts[0], parts, env)
    else:
        os.execvpe(agent.binary, [agent.binary], env)


# ─── Session linking ──────────────────────────────────────────────────────────


def encodeClaudePath(path: str) -> str:
    """Encode absolute path the way Claude Code does: replace /. and space with -."""
    return re.sub(r"[/. ]", "-", path)


def getClaudeProjectDir(path: str) -> Path:
    """Return ~/.claude/projects/<encoded-path> for a given absolute path."""
    return Path.home() / ".claude" / "projects" / encodeClaudePath(path)


def _linkClaudeSession(worktree_path: Path, repo_root: Path) -> bool:
    """Symlink worktree's Claude project dir → main repo's Claude project dir."""
    target = getClaudeProjectDir(str(repo_root))
    link = getClaudeProjectDir(str(worktree_path))

    # already correct symlink
    if link.is_symlink() and link.resolve() == target.resolve():
        return False

    # real directory exists — don't clobber
    if link.exists() and not link.is_symlink():
        return False

    # stale symlink — replace
    if link.is_symlink():
        link.unlink()

    # ensure target exists
    target.mkdir(parents=True, exist_ok=True)

    # ensure parent of link exists
    link.parent.mkdir(parents=True, exist_ok=True)

    link.symlink_to(target)
    return True


def _unlinkClaudeSession(worktree_path: Path) -> bool:
    """Remove worktree's Claude project dir symlink."""
    link = getClaudeProjectDir(str(worktree_path))
    if link.is_symlink():
        link.unlink()
        return True
    return False


_SESSION_LINKERS: dict[str, Callable[[Path, Path], bool]] = {"claude": _linkClaudeSession}
_SESSION_UNLINKERS: dict[str, Callable[[Path], bool]] = {"claude": _unlinkClaudeSession}


def linkProjectSession(agent_name: str, worktree_path: Path, repo_root: Path) -> bool:
    """Link worktree agent session to main repo session. Returns True if linked."""
    linker = _SESSION_LINKERS.get(agent_name)
    if linker:
        return linker(worktree_path, repo_root)
    return False


def unlinkProjectSession(agent_name: str, worktree_path: Path) -> bool:
    """Unlink worktree agent session. Returns True if unlinked."""
    unlinker = _SESSION_UNLINKERS.get(agent_name)
    if unlinker:
        return unlinker(worktree_path)
    return False
