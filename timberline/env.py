from __future__ import annotations

import os
import shutil
from fnmatch import fnmatch
from pathlib import Path

from timberline.models import EnvConfig

_SKIP_DIRS = {
    ".tl",
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "dist",
    "target",
    "vendor",
    ".bundle",
}


def discoverEnvFiles(repo_root: Path, config: EnvConfig) -> list[Path]:
    """Find all .env files that should be copied to worktrees."""
    include = [p for p in config.patterns if not p.startswith("!")]
    exclude = [p.removeprefix("!") for p in config.patterns if p.startswith("!")]

    env_files: list[Path] = []

    for root, dirs, files in os.walk(repo_root):
        rel_root = Path(root).relative_to(repo_root)
        depth = len(rel_root.parts) if str(rel_root) != "." else 0

        if depth > config.scan_depth:
            dirs.clear()
            continue

        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]

        # if scan_dirs specified, filter at depth 1
        if config.scan_dirs and depth == 1:
            dirs[:] = [d for d in dirs if str(rel_root / d) in config.scan_dirs]

        for f in files:
            if _matchesPatterns(f, include) and not _matchesPatterns(f, exclude):
                rel_path = Path(root, f).relative_to(repo_root)
                env_files.append(rel_path)

    return sorted(env_files)


def _matchesPatterns(filename: str, patterns: list[str]) -> bool:
    return any(fnmatch(filename, p) for p in patterns)


def copyEnvFiles(repo_root: Path, worktree_path: Path, env_files: list[Path]) -> int:
    copied = 0
    for rel_path in env_files:
        src = repo_root / rel_path
        dst = worktree_path / rel_path
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
    return copied


def diffEnvFiles(repo_root: Path, worktree_path: Path, env_files: list[Path]) -> dict[str, str]:
    """Compare env files. Returns {rel_path: status} — 'missing', 'different', or 'same'."""
    result: dict[str, str] = {}
    for rel_path in env_files:
        src = repo_root / rel_path
        dst = worktree_path / rel_path
        if not dst.exists():
            result[str(rel_path)] = "missing"
        elif src.read_bytes() != dst.read_bytes():
            result[str(rel_path)] = "different"
        else:
            result[str(rel_path)] = "same"
    return result


def listEnvFiles(repo_root: Path, config: EnvConfig) -> list[Path]:
    return discoverEnvFiles(repo_root, config)
