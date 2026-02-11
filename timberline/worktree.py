from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from pathlib import Path

from timberline.git import (
    branchExists,
    fetchBranch,
    getStatusShort,
    hasTrackedChanges,
    listWorktreesRaw,
    runGit,
)
from timberline.models import (
    TimberlineConfig,
    TimberlineError,
    WorktreeInfo,
    getWorktreeBasePath,
    resolveProjectName,
    writeRepoRootMarker,
)
from timberline.names import generateName
from timberline.state import (
    addWorktreeToState,
    loadState,
    reconcileState,
    removeWorktreeFromState,
    saveState,
)
from timberline.state import (
    archiveWorktree as archiveWorktreeState,
)
from timberline.state import (
    unarchiveWorktree as unarchiveWorktreeState,
)


def _projectName(config: TimberlineConfig, repo_root: Path) -> str:
    return resolveProjectName(repo_root, config.project_name)


def getWorktreePath(config: TimberlineConfig, name: str, repo_root: Path) -> Path:
    return getWorktreeBasePath(_projectName(config, repo_root)) / name


def resolveBranchName(config: TimberlineConfig, name: str, type_: str | None = None) -> str:
    branch_type = type_ or config.default_type
    return config.branch_template.format(user=config.user, type=branch_type, name=name)


def createWorktree(
    repo_root: Path,
    config: TimberlineConfig,
    name: str | None = None,
    branch: str | None = None,
    base: str | None = None,
    type_: str | None = None,
) -> WorktreeInfo:
    """Create git worktree + update state. Returns WorktreeInfo."""
    project_name = _projectName(config, repo_root)

    # resolve name
    if not name:
        state = loadState(project_name, repo_root)
        existing = set(state.worktrees.keys())
        name = generateName(config.naming_scheme, existing)

    wt_path = getWorktreeBasePath(project_name) / name
    if wt_path.exists():
        raise TimberlineError(f"Worktree '{name}' already exists at {wt_path}")

    # resolve branch
    branch_type = type_ or config.default_type
    if not branch:
        branch = resolveBranchName(config, name, branch_type)

    base_branch = base or config.base_branch

    # check branch doesn't already exist
    if branchExists(branch, cwd=repo_root):
        raise TimberlineError(f"Branch '{branch}' already exists")

    # ensure project dir + repo_root marker
    writeRepoRootMarker(project_name, repo_root)

    # create worktree
    runGit("worktree", "add", "-b", branch, str(wt_path), base_branch, cwd=repo_root)

    now = datetime.now(UTC).isoformat()
    info = WorktreeInfo(
        name=name,
        branch=branch,
        base_branch=base_branch,
        type=branch_type,
        path=str(wt_path),
        created_at=now,
    )

    # update state
    state = loadState(project_name, repo_root)
    state = addWorktreeToState(state, info)
    saveState(project_name, state)

    return info


def deriveName(branch: str) -> str:
    """Extract worktree name from branch: last `/`-separated segment."""
    return branch.rsplit("/", 1)[-1]


def checkoutWorktree(
    repo_root: Path,
    config: TimberlineConfig,
    branch: str,
    name: str | None = None,
    base_branch: str | None = None,
    pr: int = 0,
) -> WorktreeInfo:
    """Create worktree from existing branch. Returns WorktreeInfo."""
    project_name = _projectName(config, repo_root)

    if not name:
        name = deriveName(branch)

    wt_path = getWorktreeBasePath(project_name) / name
    if wt_path.exists():
        raise TimberlineError(f"Worktree '{name}' already exists at {wt_path}")

    # try fetch from remote, fall back to local branch check
    try:
        fetchBranch(branch, cwd=repo_root)
    except TimberlineError:
        if not branchExists(branch, cwd=repo_root):
            raise TimberlineError(f"Branch '{branch}' not found locally or on remote") from None

    # ensure project dir + repo_root marker
    writeRepoRootMarker(project_name, repo_root)

    # create worktree from existing branch (no -b)
    runGit("worktree", "add", str(wt_path), branch, cwd=repo_root)

    now = datetime.now(UTC).isoformat()
    info = WorktreeInfo(
        name=name,
        branch=branch,
        base_branch=base_branch or config.base_branch,
        type="",
        path=str(wt_path),
        created_at=now,
        pr=pr,
    )

    # update state
    state = loadState(project_name, repo_root)
    state = addWorktreeToState(state, info)
    saveState(project_name, state)

    return info


def removeWorktree(
    repo_root: Path,
    config: TimberlineConfig,
    name: str,
    force: bool = False,
    keep_branch: bool = False,
) -> None:
    project_name = _projectName(config, repo_root)
    wt_path = getWorktreeBasePath(project_name) / name
    if not wt_path.exists():
        raise TimberlineError(f"Worktree '{name}' not found at {wt_path}")

    # check dirty (tracked files only — untracked like CLAUDE.md are expected)
    if not force and hasTrackedChanges(wt_path):
        raise TimberlineError(
            f"Worktree '{name}' has uncommitted changes. Use --force to override."
        )

    # get branch before removing
    state = loadState(project_name, repo_root)
    branch = state.worktrees.get(name, {}).get("branch", "")

    # remove worktree (always --force: git rejects even untracked files without it)
    runGit("worktree", "remove", "--force", str(wt_path), cwd=repo_root)

    # prune
    runGit("worktree", "prune", cwd=repo_root)

    # delete branch
    if branch and not keep_branch:
        with contextlib.suppress(TimberlineError):
            runGit("branch", "-D", branch, cwd=repo_root)

    # update state
    state = removeWorktreeFromState(state, name)
    saveState(project_name, state)


def listWorktrees(
    repo_root: Path, config: TimberlineConfig, *, include_archived: bool = False
) -> list[WorktreeInfo]:
    """List managed worktrees. Excludes archived unless include_archived=True."""
    project_name = _projectName(config, repo_root)
    state = loadState(project_name, repo_root)
    git_wts = listWorktreesRaw(repo_root)

    state = reconcileState(state, git_wts, project_name)
    saveState(project_name, state)

    worktrees: list[WorktreeInfo] = []
    for name, data in state.worktrees.items():
        archived = data.get("archived", "")
        if archived and not include_archived:
            continue

        wt_path = Path(data.get("path", ""))
        status = ""
        if archived:
            status = "archived"
        elif wt_path.exists():
            short = getStatusShort(wt_path)
            if short:
                lines = [ln for ln in short.splitlines() if ln.strip()]
                status = f"{len(lines)} modified"
            else:
                status = "clean"

        worktrees.append(
            WorktreeInfo(
                name=name,
                branch=data.get("branch", ""),
                base_branch=data.get("base_branch", ""),
                type=data.get("type", ""),
                path=data.get("path", ""),
                created_at=data.get("created_at", ""),
                status=status,
                pr=int(data.get("pr", 0)),
                archived=archived,
            )
        )

    return sorted(worktrees, key=lambda w: w.name)


def getWorktree(
    repo_root: Path, config: TimberlineConfig, name: str, *, include_archived: bool = True
) -> WorktreeInfo | None:
    for wt in listWorktrees(repo_root, config, include_archived=include_archived):
        if wt.name == name:
            return wt
    return None


def archiveWorktreeDomain(repo_root: Path, config: TimberlineConfig, name: str) -> WorktreeInfo:
    """Archive a worktree (soft-remove). Returns the WorktreeInfo."""
    project_name = _projectName(config, repo_root)
    wt = getWorktree(repo_root, config, name, include_archived=True)
    if not wt:
        raise TimberlineError(f"Worktree '{name}' not found")
    if wt.archived:
        raise TimberlineError(f"Worktree '{name}' is already archived")

    now = datetime.now(UTC).isoformat()
    state = loadState(project_name, repo_root)
    state = archiveWorktreeState(state, name, now)
    saveState(project_name, state)

    wt.archived = now
    return wt


def unarchiveWorktreeDomain(repo_root: Path, config: TimberlineConfig, name: str) -> WorktreeInfo:
    """Unarchive a worktree. Returns the WorktreeInfo."""
    project_name = _projectName(config, repo_root)
    wt = getWorktree(repo_root, config, name, include_archived=True)
    if not wt:
        raise TimberlineError(f"Worktree '{name}' not found")
    if not wt.archived:
        raise TimberlineError(f"Worktree '{name}' is not archived")

    state = loadState(project_name, repo_root)
    state = unarchiveWorktreeState(state, name)
    saveState(project_name, state)

    wt.archived = ""
    return wt
