from __future__ import annotations

import json
import subprocess
from pathlib import Path

from timberline.models import InitConfig

# command → ecosystem mapping
_ECOSYSTEM: dict[str, str] = {
    "bun": "js",
    "npm": "js",
    "yarn": "js",
    "pnpm": "js",
    "uv": "python",
    "pip": "python",
    "cargo": "rust",
    "go": "go",
    "composer": "php",
    "bundle": "ruby",
}

# detection priority order — lockfiles before project files, grouped by ecosystem
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
    ("Cargo.lock", ["cargo", "fetch"]),
    ("Cargo.toml", ["cargo", "fetch"]),
    ("go.sum", ["go", "mod", "download"]),
    ("go.mod", ["go", "mod", "download"]),
    ("composer.lock", ["composer", "install"]),
    ("composer.json", ["composer", "install"]),
    ("Gemfile.lock", ["bundle", "install"]),
    ("Gemfile", ["bundle", "install"]),
]


def detectInstaller(project_dir: Path) -> list[str] | None:
    for filename, cmd in _LOCKFILE_MAP:
        if (project_dir / filename).exists():
            return cmd
    return None


def isDifferentEcosystem(cmd_a: list[str] | None, cmd_b: list[str] | None) -> bool:
    if not cmd_a or not cmd_b:
        return True
    eco_a = _ECOSYSTEM.get(cmd_a[0])
    eco_b = _ECOSYSTEM.get(cmd_b[0])
    if eco_a is None or eco_b is None:
        return True
    return eco_a != eco_b


def findProjectDirs(root: Path, max_depth: int = 3) -> list[Path]:
    """Find subdirectories that have their own package manager files."""
    skip = {
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


def _hasJsonScript(json_file: Path, script: str) -> bool:
    """Check if a JSON file (package.json, composer.json) has a script."""
    if not json_file.exists():
        return False
    try:
        data = json.loads(json_file.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    return script in data.get("scripts", {})


def _hasPackageScript(project_dir: Path, script: str) -> str | None:
    """Return runner command if package.json has script, else None."""
    if not _hasJsonScript(project_dir / "package.json", script):
        return None
    has_bun = (project_dir / "bun.lock").exists() or (project_dir / "bun.lockb").exists()
    runner = "bun run" if has_bun else "npm run"
    return f"{runner} {script}"


def _hasComposerScript(project_dir: Path, script: str) -> str | None:
    """Return composer run-script command if composer.json has script, else None."""
    if not _hasJsonScript(project_dir / "composer.json", script):
        return None
    return f"composer run-script {script}"


def detectPreLand(project_dir: Path) -> str | None:
    # Makefile check target (highest priority — explicit user config)
    if _hasMakeTarget(project_dir, "check"):
        return "make check"
    # package.json check script
    pkg_check = _hasPackageScript(project_dir, "check")
    if pkg_check:
        return pkg_check
    # composer.json check script
    composer_check = _hasComposerScript(project_dir, "check")
    if composer_check:
        return composer_check
    # fallback: Makefile test target
    if _hasMakeTarget(project_dir, "test"):
        return "make test"
    # fallback: package.json test script
    pkg_test = _hasPackageScript(project_dir, "test")
    if pkg_test:
        return pkg_test
    # fallback: composer.json test script
    composer_test = _hasComposerScript(project_dir, "test")
    if composer_test:
        return composer_test
    # fallback: cargo test
    if (project_dir / "Cargo.toml").exists():
        return "cargo test"
    # fallback: go test
    if (project_dir / "go.mod").exists():
        return "go test ./..."
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
