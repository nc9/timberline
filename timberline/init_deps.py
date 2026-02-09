from __future__ import annotations

import json
import subprocess
from pathlib import Path

from timberline.types import InitConfig

# detection priority order
_LOCKFILE_MAP: list[tuple[str, list[str]]] = [
    ("bun.lock", ["bun", "install"]),
    ("bun.lockb", ["bun", "install"]),
    ("package-lock.json", ["npm", "install"]),
    ("yarn.lock", ["yarn", "install"]),
    ("pnpm-lock.yaml", ["pnpm", "install"]),
    ("package.json", ["bun", "install"]),
    ("uv.lock", ["uv", "sync"]),
    ("pyproject.toml", ["uv", "sync"]),
    ("requirements.txt", ["uv", "pip", "install", "-r", "requirements.txt"]),
]

_JS_COMMANDS = {"bun", "npm", "yarn", "pnpm"}
_PY_COMMANDS = {"uv", "pip", "python"}


def detectInstaller(project_dir: Path) -> list[str] | None:
    for filename, cmd in _LOCKFILE_MAP:
        if (project_dir / filename).exists():
            return cmd
    return None


def isDifferentEcosystem(cmd_a: list[str] | None, cmd_b: list[str] | None) -> bool:
    if not cmd_a or not cmd_b:
        return True
    a_is_js = cmd_a[0] in _JS_COMMANDS
    b_is_js = cmd_b[0] in _JS_COMMANDS
    return a_is_js != b_is_js


def findProjectDirs(root: Path, max_depth: int = 3) -> list[Path]:
    """Find subdirectories that have their own package manager files."""
    skip = {".tl", "node_modules", ".git", "__pycache__", ".venv", "dist"}
    results: list[Path] = []

    def _walk(path: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = sorted(path.iterdir())
        except PermissionError:
            return
        for entry in entries:
            if entry.is_dir() and entry.name not in skip:
                if detectInstaller(entry) is not None:
                    results.append(entry)
                _walk(entry, depth + 1)

    _walk(root, 1)
    return results


def _runCmd(cmd: list[str] | str, cwd: Path, shell: bool = False) -> tuple[str, bool]:
    """Run command, return (description, success)."""
    desc = cmd if isinstance(cmd, str) else " ".join(cmd)
    try:
        subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            shell=shell,
            timeout=300,
        )
        return desc, True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return desc, False


def _hasMakeTarget(project_dir: Path, target: str) -> bool:
    makefile = project_dir / "Makefile"
    if not makefile.exists():
        return False
    try:
        content = makefile.read_text()
    except OSError:
        return False
    return f"{target}:" in content


def _hasPackageScript(project_dir: Path, script: str) -> str | None:
    """Return runner command if package.json has script, else None."""
    pkg = project_dir / "package.json"
    if not pkg.exists():
        return None
    try:
        data = json.loads(pkg.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    scripts = data.get("scripts", {})
    if script not in scripts:
        return None
    has_bun = (project_dir / "bun.lock").exists() or (project_dir / "bun.lockb").exists()
    runner = "bun run" if has_bun else "npm run"
    return f"{runner} {script}"


def detectPreLand(project_dir: Path) -> str | None:
    # Makefile check target
    if _hasMakeTarget(project_dir, "check"):
        return "make check"
    # package.json check script
    pkg_check = _hasPackageScript(project_dir, "check")
    if pkg_check:
        return pkg_check
    # fallback: Makefile test target
    if _hasMakeTarget(project_dir, "test"):
        return "make test"
    # fallback: package.json test script
    pkg_test = _hasPackageScript(project_dir, "test")
    if pkg_test:
        return pkg_test
    return None


def detectAndInstall(worktree_path: Path, config: InitConfig) -> list[tuple[str, bool]]:
    """Full install sequence. Returns list of (description, success)."""
    results: list[tuple[str, bool]] = []

    # Phase 1: root-level install
    root_installer = detectInstaller(worktree_path)
    if root_installer:
        results.append(_runCmd(root_installer, worktree_path))

    # Phase 2: subdirectory installs (different ecosystem only)
    for subdir in findProjectDirs(worktree_path):
        sub_installer = detectInstaller(subdir)
        if sub_installer and isDifferentEcosystem(root_installer, sub_installer):
            results.append(_runCmd(sub_installer, subdir))

    # Phase 3: custom init command
    if config.init_command:
        results.append(_runCmd(config.init_command, worktree_path, shell=True))

    # Phase 4: post_init commands
    for cmd in config.post_init:
        results.append(_runCmd(cmd, worktree_path, shell=True))

    return results
