from __future__ import annotations

import json
from pathlib import Path

from timberline.models import StateFile, WorktreeInfo, getProjectDir, getWorktreeBasePath

STATE_FILENAME = "state.json"


def _stateFilePath(project_name: str) -> Path:
    return getProjectDir(project_name) / STATE_FILENAME


def loadState(project_name: str, repo_root: Path | None = None) -> StateFile:
    path = _stateFilePath(project_name)
    if not path.exists():
        return StateFile(repo_root=str(repo_root) if repo_root else "")

    data = json.loads(path.read_text())
    return StateFile(
        version=data.get("version", 1),
        repo_root=data.get("repo_root", str(repo_root) if repo_root else ""),
        worktrees=data.get("worktrees", {}),
    )


def saveState(project_name: str, state: StateFile) -> None:
    path = _stateFilePath(project_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": state.version,
        "repo_root": state.repo_root,
        "worktrees": state.worktrees,
    }
    path.write_text(json.dumps(data, indent=2) + "\n")


def addWorktreeToState(state: StateFile, info: WorktreeInfo) -> StateFile:
    new_worktrees = dict(state.worktrees)
    new_worktrees[info.name] = {
        "branch": info.branch,
        "base_branch": info.base_branch,
        "type": info.type,
        "created_at": info.created_at,
        "path": info.path,
    }
    return StateFile(
        version=state.version,
        repo_root=state.repo_root,
        worktrees=new_worktrees,
    )


def updateWorktreeBranch(state: StateFile, name: str, new_branch: str) -> StateFile:
    if name not in state.worktrees:
        return state
    new_worktrees = dict(state.worktrees)
    new_worktrees[name] = {**new_worktrees[name], "branch": new_branch}
    return StateFile(
        version=state.version,
        repo_root=state.repo_root,
        worktrees=new_worktrees,
    )


def removeWorktreeFromState(state: StateFile, name: str) -> StateFile:
    new_worktrees = {k: v for k, v in state.worktrees.items() if k != name}
    return StateFile(
        version=state.version,
        repo_root=state.repo_root,
        worktrees=new_worktrees,
    )


def archiveWorktree(state: StateFile, name: str, timestamp: str) -> StateFile:
    if name not in state.worktrees:
        return state
    new_worktrees = dict(state.worktrees)
    new_worktrees[name] = {**new_worktrees[name], "archived": timestamp}
    return StateFile(
        version=state.version,
        repo_root=state.repo_root,
        worktrees=new_worktrees,
    )


def unarchiveWorktree(state: StateFile, name: str) -> StateFile:
    if name not in state.worktrees:
        return state
    new_worktrees = dict(state.worktrees)
    entry = {k: v for k, v in new_worktrees[name].items() if k != "archived"}
    new_worktrees[name] = entry
    return StateFile(
        version=state.version,
        repo_root=state.repo_root,
        worktrees=new_worktrees,
    )


def reconcileState(
    state: StateFile, git_worktrees: list[dict[str, str]], project_name: str
) -> StateFile:
    """Remove orphaned entries, add untracked worktrees."""
    git_paths = {wt["worktree"] for wt in git_worktrees}

    # remove orphaned (keep archived entries whose directory still exists)
    new_worktrees: dict[str, dict[str, str]] = {}
    for name, info in state.worktrees.items():
        in_git = info.get("path") in git_paths
        archived_on_disk = info.get("archived") and Path(info.get("path", "")).exists()
        if in_git or archived_on_disk:
            new_worktrees[name] = info

    # add untracked (worktrees in global dir not in state)
    known_paths = {info.get("path") for info in new_worktrees.values()}
    tl_prefix = str(getWorktreeBasePath(project_name)) + "/"

    # also check legacy .tl/ prefix for backward compat
    repo_root = state.repo_root
    legacy_prefix = f"{repo_root}/.tl/" if repo_root else ""

    for wt in git_worktrees:
        wt_path = wt["worktree"]
        if wt_path in known_paths:
            continue

        prefix = ""
        if wt_path.startswith(tl_prefix):
            prefix = tl_prefix
        elif legacy_prefix and wt_path.startswith(legacy_prefix):
            prefix = legacy_prefix

        if prefix:
            name = wt_path.removeprefix(prefix).split("/")[0]
            if name and name not in new_worktrees:
                new_worktrees[name] = {
                    "branch": wt.get("branch", ""),
                    "base_branch": "",
                    "type": "",
                    "created_at": "",
                    "path": wt_path,
                }

    return StateFile(
        version=state.version,
        repo_root=state.repo_root,
        worktrees=new_worktrees,
    )
