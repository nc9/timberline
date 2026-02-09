from __future__ import annotations

import json
from pathlib import Path

from timberline.types import StateFile, WorktreeInfo

STATE_FILENAME = ".tl-state.json"


def _stateFilePath(repo_root: Path, worktree_dir: str) -> Path:
    return repo_root / worktree_dir / STATE_FILENAME


def loadState(repo_root: Path, worktree_dir: str) -> StateFile:
    path = _stateFilePath(repo_root, worktree_dir)
    if not path.exists():
        return StateFile(repo_root=str(repo_root))

    data = json.loads(path.read_text())
    return StateFile(
        version=data.get("version", 1),
        repo_root=data.get("repo_root", str(repo_root)),
        worktrees=data.get("worktrees", {}),
    )


def saveState(repo_root: Path, worktree_dir: str, state: StateFile) -> None:
    path = _stateFilePath(repo_root, worktree_dir)
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


def reconcileState(
    state: StateFile, git_worktrees: list[dict[str, str]], worktree_dir: str
) -> StateFile:
    """Remove orphaned entries, add untracked worktrees."""
    git_paths = {wt["worktree"] for wt in git_worktrees}

    # remove orphaned
    new_worktrees: dict[str, dict[str, str]] = {}
    for name, info in state.worktrees.items():
        if info.get("path") in git_paths:
            new_worktrees[name] = info

    # add untracked (worktrees in tl dir not in state)
    known_paths = {info.get("path") for info in new_worktrees.values()}
    repo_root = state.repo_root
    tl_prefix = f"{repo_root}/{worktree_dir}/"

    for wt in git_worktrees:
        wt_path = wt["worktree"]
        if wt_path.startswith(tl_prefix) and wt_path not in known_paths:
            name = wt_path.removeprefix(tl_prefix).split("/")[0]
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
