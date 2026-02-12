from __future__ import annotations

import subprocess
from pathlib import Path

from timberline.models import TimberlineError


def runGit(*args: str, cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise TimberlineError(f"git {' '.join(args)} failed: {e.stderr.strip()}") from e
    except FileNotFoundError:
        raise TimberlineError("git not found — is it installed?") from None


def findRepoRoot(cwd: Path | None = None) -> Path:
    """Find main repo root, resolving through worktrees if needed."""
    start = cwd or Path.cwd()
    toplevel = Path(runGit("rev-parse", "--show-toplevel", cwd=start))

    git_path = toplevel / ".git"
    if git_path.is_file():
        # worktree: .git file contains "gitdir: /path/to/main/.git/worktrees/<n>"
        gitdir = git_path.read_text().strip().removeprefix("gitdir: ")
        main_git_dir = Path(gitdir).resolve()
        # walk up: /repo/.git/worktrees/<n> -> /repo
        return main_git_dir.parent.parent.parent

    return toplevel


def getCurrentBranch(cwd: Path | None = None) -> str:
    return runGit("rev-parse", "--abbrev-ref", "HEAD", cwd=cwd)


def getDefaultBranch(cwd: Path | None = None) -> str:
    """Detect main/master/develop."""
    for candidate in ("main", "master", "develop"):
        if branchExists(candidate, cwd=cwd):
            return candidate
    return "main"


def resolveUser() -> str | None:
    """Resolve username: gh CLI -> git config fallback."""
    try:
        result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    try:
        name = runGit("config", "user.name")
        if name:
            return name.lower().replace(" ", "-")
    except TimberlineError:
        pass

    return None


def listWorktreesRaw(repo_root: Path) -> list[dict[str, str]]:
    """Parse `git worktree list --porcelain`."""
    output = runGit("worktree", "list", "--porcelain", cwd=repo_root)
    worktrees: list[dict[str, str]] = []
    current: dict[str, str] = {}

    for line in output.splitlines():
        if not line.strip():
            if current:
                worktrees.append(current)
                current = {}
            continue

        if line.startswith("worktree "):
            current["worktree"] = line.removeprefix("worktree ")
        elif line.startswith("HEAD "):
            current["HEAD"] = line.removeprefix("HEAD ")
        elif line.startswith("branch "):
            current["branch"] = line.removeprefix("branch refs/heads/")
        elif line == "bare":
            current["bare"] = "true"
        elif line == "detached":
            current["detached"] = "true"

    if current:
        worktrees.append(current)

    return worktrees


def getStatusShort(cwd: Path) -> str:
    return runGit("status", "--short", cwd=cwd)


def _parseNumstat(output: str) -> tuple[int, int]:
    """Parse git diff --numstat output into (added, removed). Binary lines treated as 0."""
    added = 0
    removed = 0
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        a, r = parts[0], parts[1]
        if a != "-":
            added += int(a)
        if r != "-":
            removed += int(r)
    return added, removed


def getDiffNumstat(cwd: Path) -> tuple[int, int]:
    """Uncommitted changes: (added, removed) line counts (staged + unstaged)."""
    unstaged = runGit("diff", "--numstat", cwd=cwd)
    staged = runGit("diff", "--numstat", "--cached", cwd=cwd)
    ua, ur = _parseNumstat(unstaged)
    sa, sr = _parseNumstat(staged)
    return ua + sa, ur + sr


def getCommittedDiffStats(branch: str, base: str, cwd: Path) -> tuple[int, int, int]:
    """Committed changes vs base: (added, removed, files)."""
    try:
        output = runGit("diff", "--numstat", f"{base}...{branch}", cwd=cwd)
    except TimberlineError:
        return 0, 0, 0
    added, removed = _parseNumstat(output)
    files = sum(1 for line in output.splitlines() if line.strip())
    return added, removed, files


def getLastCommitTime(cwd: Path) -> str:
    """ISO timestamp of most recent commit. Empty string if no commits."""
    try:
        return runGit("log", "-1", "--format=%aI", cwd=cwd)
    except TimberlineError:
        return ""


def hasTrackedChanges(cwd: Path) -> bool:
    """Check for modified/staged tracked files only (ignores untracked)."""
    output = runGit("status", "--short", "--untracked-files=no", cwd=cwd)
    return bool(output.strip())


def getAheadBehind(branch: str, base: str, cwd: Path) -> tuple[int, int]:
    try:
        output = runGit("rev-list", "--left-right", "--count", f"{base}...{branch}", cwd=cwd)
        parts = output.split()
        if len(parts) == 2:
            return int(parts[1]), int(parts[0])
    except TimberlineError:
        pass
    return 0, 0


def isBranchMerged(branch: str, remote_base: str, cwd: Path) -> bool:
    """Tree-content check for squash-merge detection."""
    try:
        runGit("diff", "--quiet", remote_base, branch, cwd=cwd)
        return True  # exit 0 = identical trees
    except TimberlineError:
        return False  # diff exists OR git error (offline, missing ref)


def renameBranch(old: str, new: str, cwd: Path | None = None) -> None:
    runGit("branch", "-m", old, new, cwd=cwd)


def branchExists(name: str, cwd: Path | None = None) -> bool:
    try:
        runGit("rev-parse", "--verify", f"refs/heads/{name}", cwd=cwd)
        return True
    except TimberlineError:
        return False


def fetchBranch(branch: str, remote: str = "origin", cwd: Path | None = None) -> None:
    runGit("fetch", remote, branch, cwd=cwd)


def resolvePrBranch(pr_number: int, cwd: Path | None = None) -> tuple[str, str]:
    """Resolve PR head/base branches via gh CLI. Returns (head_branch, base_branch)."""
    try:
        result = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "headRefName,baseRefName"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        import json

        data = json.loads(result.stdout)
        return data["headRefName"], data["baseRefName"]
    except (subprocess.CalledProcessError, FileNotFoundError, KeyError) as e:
        raise TimberlineError(f"Failed to resolve PR #{pr_number} (is gh CLI installed?)") from e
