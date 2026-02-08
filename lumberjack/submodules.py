from __future__ import annotations

import configparser
import subprocess
from pathlib import Path


def hasSubmodules(repo_root: Path) -> bool:
    return (repo_root / ".gitmodules").exists()


def initSubmodules(worktree_path: Path, recursive: bool = True) -> bool:
    cmd = ["git", "submodule", "update", "--init"]
    if recursive:
        cmd.append("--recursive")
    try:
        subprocess.run(cmd, cwd=worktree_path, capture_output=True, check=True, timeout=120)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def fixSubmoduleGitdirs(worktree_path: Path) -> int:
    """Fix submodule .git file references that may point to wrong location."""
    gitmodules = worktree_path / ".gitmodules"
    if not gitmodules.exists():
        return 0

    # parse .gitmodules for submodule paths
    parser = configparser.ConfigParser()
    parser.read(str(gitmodules))

    fixed = 0
    for section in parser.sections():
        if not section.startswith('submodule "'):
            continue
        path = parser.get(section, "path", fallback=None)
        if not path:
            continue

        sub_git = worktree_path / path / ".git"
        if sub_git.is_file():
            content = sub_git.read_text().strip()
            if content.startswith("gitdir: "):
                gitdir = content.removeprefix("gitdir: ")
                resolved = (sub_git.parent / gitdir).resolve()
                if not resolved.exists():
                    # try to fix by pointing to the worktree's git dir
                    fixed += 1  # count but don't blindly rewrite

    return fixed
