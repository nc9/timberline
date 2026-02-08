from __future__ import annotations

import contextlib
import os
import subprocess
from pathlib import Path
from typing import Annotated

import typer

from lumberjack.agent import (
    buildEnvVars,
    detectInstalledAgents,
    getAgentDef,
    injectAgentContext,
    launchAgent,
)
from lumberjack.config import (
    configExists,
    loadConfig,
    updateConfigField,
    writeConfig,
)
from lumberjack.display import (
    printConfig,
    printCreateSummary,
    printError,
    printStatusList,
    printSuccess,
    printWarning,
    printWorktreeJson,
    printWorktreePaths,
    printWorktreeTable,
)
from lumberjack.env import copyEnvFiles, diffEnvFiles, discoverEnvFiles, listEnvFiles
from lumberjack.git import (
    findRepoRoot,
    getAheadBehind,
    getCurrentBranch,
    getDefaultBranch,
    resolveUser,
    runGit,
)
from lumberjack.init_deps import detectAndInstall, detectInstaller
from lumberjack.shell import generateShellInit
from lumberjack.submodules import hasSubmodules, initSubmodules
from lumberjack.types import (
    LumberjackConfig,
    LumberjackError,
    NamingScheme,
    WorktreeInfo,
)
from lumberjack.worktree import (
    createWorktree,
    getWorktree,
    listWorktrees,
    removeWorktree,
)

app = typer.Typer(
    name="lj",
    help="Git worktree manager for parallel coding agent development",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

env_app = typer.Typer(help="Manage .env files across worktrees", no_args_is_help=True)
config_app = typer.Typer(help="Manage lumberjack configuration", no_args_is_help=True)
app.add_typer(env_app, name="env")
app.add_typer(config_app, name="config")


def _resolveRoot() -> Path:
    try:
        return findRepoRoot()
    except LumberjackError as e:
        printError(str(e))
        raise typer.Exit(1) from e


def _loadCfg(repo_root: Path) -> LumberjackConfig:
    return loadConfig(repo_root)


# ─── init ──────────────────────────────────────────────────────────────────────


@app.command()
def init(
    defaults: Annotated[bool, typer.Option("--defaults", help="Accept all defaults")] = False,
    user: Annotated[str | None, typer.Option(help="GitHub username")] = None,
) -> None:
    """Initialize lumberjack in this repo."""
    repo_root = _resolveRoot()

    if configExists(repo_root):
        printWarning(".lumberjack.toml already exists")
        if not defaults:
            overwrite = typer.confirm("Overwrite?", default=False)
            if not overwrite:
                raise typer.Exit(0)

    # resolve user
    resolved_user = user or resolveUser() or ""
    if not defaults and not user:
        resolved_user = typer.prompt("Branch prefix (username)", default=resolved_user)

    # detect base branch
    base = getDefaultBranch(repo_root)

    # detect installer
    installer = detectInstaller(repo_root)
    init_command: str | None = None
    if installer:
        init_command = " ".join(installer)

    # detect naming scheme
    naming = NamingScheme.MINERALS

    # detect env files
    default_cfg = LumberjackConfig()
    env_files = discoverEnvFiles(repo_root, default_cfg.env)

    # detect submodules
    has_subs = hasSubmodules(repo_root)

    # detect coding agents
    installed = detectInstalledAgents()
    default_agent = "claude"
    if defaults:
        default_agent = installed[0] if installed else "claude"
    elif installed:
        if len(installed) == 1:
            default_agent = installed[0]
            printSuccess(f"Detected coding agent: {default_agent}")
        else:
            printSuccess(f"Detected coding agents: {', '.join(installed)}")
            default_agent = typer.prompt("Default agent", default=installed[0], type=str)
    else:
        printWarning("No known coding agents found on PATH")

    if not defaults:
        printSuccess(f"Git root: {repo_root}")
        if env_files:
            printSuccess(f"Found {len(env_files)} .env files to auto-copy")
        if has_subs:
            printSuccess("Found git submodules")

    config = LumberjackConfig(
        user=resolved_user,
        base_branch=base,
        naming_scheme=naming,
        default_agent=default_agent,
        init=default_cfg.init
        if not init_command
        else default_cfg.init.__class__(init_command=init_command, auto_init=True, post_init=[]),
    )

    writeConfig(repo_root, config)
    printSuccess("Created .lumberjack.toml")

    # update .gitignore
    gitignore = repo_root / ".gitignore"
    wt_dir = config.worktree_dir + "/"
    if gitignore.exists():
        content = gitignore.read_text()
        if wt_dir not in content:
            gitignore.write_text(content.rstrip() + f"\n{wt_dir}\n")
            printSuccess("Updated .gitignore")
    else:
        gitignore.write_text(f"{wt_dir}\n")
        printSuccess("Created .gitignore")

    printSuccess("Ready — run `lj new` to create your first worktree")


# ─── new / create ─────────────────────────────────────────────────────────────


@app.command("new")
def new_cmd(
    name: Annotated[str | None, typer.Argument(help="Worktree name")] = None,
    type_: Annotated[str | None, typer.Option("--type", "-t", help="Branch type")] = None,
    branch: Annotated[str | None, typer.Option("--branch", "-b", help="Explicit branch")] = None,
    base: Annotated[str | None, typer.Option("--from", help="Base branch")] = None,
    no_init: Annotated[bool, typer.Option("--no-init", help="Skip dependency install")] = False,
    no_env: Annotated[bool, typer.Option("--no-env", help="Skip .env copy")] = False,
    no_submodules: Annotated[
        bool, typer.Option("--no-submodules", help="Skip submodule init")
    ] = False,
    agent: Annotated[bool, typer.Option("--agent", help="Launch coding agent after")] = False,
) -> None:
    """Create a new worktree."""
    repo_root = _resolveRoot()
    config = _loadCfg(repo_root)
    steps: list[str] = []

    try:
        info = createWorktree(repo_root, config, name=name, branch=branch, base=base, type_=type_)
    except LumberjackError as e:
        printError(str(e))
        raise typer.Exit(1) from e

    wt_path = Path(info.path)

    # env files
    if not no_env and config.env.auto_copy:
        env_files = discoverEnvFiles(repo_root, config.env)
        if env_files:
            copied = copyEnvFiles(repo_root, wt_path, env_files)
            steps.append(f"Copied {copied} .env files")

    # submodules
    if not no_submodules and config.submodules.auto_init and hasSubmodules(repo_root):
        ok = initSubmodules(wt_path, config.submodules.recursive)
        if ok:
            steps.append("Initialized submodules")

    # dependency install
    if not no_init and config.init.auto_init:
        results = detectAndInstall(wt_path, config.init)
        for desc, ok in results:
            steps.append(f"{desc} ({'ok' if ok else 'failed'})")

    # inject agent context file
    if config.agent.inject_context:
        agent_def = getAgentDef(config.default_agent)
        all_wts = listWorktrees(repo_root, config)
        injectAgentContext(agent_def, wt_path, info, all_wts, repo_root)
        steps.append(f"Injected {agent_def.context_file} context")

    printCreateSummary(info, steps)

    # launch agent
    if agent or config.agent.auto_launch:
        agent_def = getAgentDef(config.default_agent)
        env_vars = buildEnvVars(info, repo_root)
        launchAgent(agent_def, wt_path, env_vars)


@app.command("create", hidden=True)
def create_cmd(
    name: Annotated[str | None, typer.Argument(help="Worktree name")] = None,
    type_: Annotated[str | None, typer.Option("--type", "-t")] = None,
    branch: Annotated[str | None, typer.Option("--branch", "-b")] = None,
    base: Annotated[str | None, typer.Option("--from")] = None,
    no_init: Annotated[bool, typer.Option("--no-init")] = False,
    no_env: Annotated[bool, typer.Option("--no-env")] = False,
    no_submodules: Annotated[bool, typer.Option("--no-submodules")] = False,
    agent: Annotated[bool, typer.Option("--agent")] = False,
) -> None:
    """Alias for `lj new`."""
    new_cmd(name, type_, branch, base, no_init, no_env, no_submodules, agent)


# ─── list / ls ─────────────────────────────────────────────────────────────────


@app.command("ls")
def ls_cmd(
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    paths: Annotated[bool, typer.Option("--paths", help="Paths only")] = False,
) -> None:
    """List worktrees."""
    repo_root = _resolveRoot()
    config = _loadCfg(repo_root)
    worktrees = listWorktrees(repo_root, config)

    if json_output:
        printWorktreeJson(worktrees)
    elif paths:
        printWorktreePaths(worktrees)
    else:
        printWorktreeTable(worktrees)


@app.command("list", hidden=True)
def list_cmd(
    json_output: Annotated[bool, typer.Option("--json")] = False,
    paths: Annotated[bool, typer.Option("--paths")] = False,
) -> None:
    """Alias for `lj ls`."""
    ls_cmd(json_output, paths)


# ─── rm / remove ───────────────────────────────────────────────────────────────


@app.command("rm")
def rm_cmd(
    name: Annotated[str | None, typer.Argument(help="Worktree name")] = None,
    force: Annotated[bool, typer.Option("--force", "-f", help="Force remove")] = False,
    keep_branch: Annotated[bool, typer.Option("--keep-branch", help="Keep git branch")] = False,
    all_: Annotated[bool, typer.Option("--all", help="Remove all worktrees")] = False,
) -> None:
    """Remove a worktree."""
    repo_root = _resolveRoot()
    config = _loadCfg(repo_root)

    if all_:
        worktrees = listWorktrees(repo_root, config)
        for wt in worktrees:
            try:
                removeWorktree(repo_root, config, wt.name, force=force, keep_branch=keep_branch)
                printSuccess(f"Removed {wt.name}")
            except LumberjackError as e:
                printError(str(e))
        return

    if not name:
        printError("Specify worktree name or use --all")
        raise typer.Exit(1)

    try:
        removeWorktree(repo_root, config, name, force=force, keep_branch=keep_branch)
        printSuccess(f"Removed {name}")
    except LumberjackError as e:
        printError(str(e))
        raise typer.Exit(1) from e


@app.command("remove", hidden=True)
def remove_cmd(
    name: Annotated[str | None, typer.Argument()] = None,
    force: Annotated[bool, typer.Option("--force", "-f")] = False,
    keep_branch: Annotated[bool, typer.Option("--keep-branch")] = False,
    all_: Annotated[bool, typer.Option("--all")] = False,
) -> None:
    """Alias for `lj rm`."""
    rm_cmd(name, force, keep_branch, all_)


# ─── cd ────────────────────────────────────────────────────────────────────────


@app.command("cd")
def cd_cmd(
    name: Annotated[str, typer.Argument(help="Worktree name")],
    shell: Annotated[bool, typer.Option("--shell", help="Spawn subshell")] = False,
) -> None:
    """Print worktree path (use with cd $(...))."""
    repo_root = _resolveRoot()
    config = _loadCfg(repo_root)

    wt = getWorktree(repo_root, config, name)
    if not wt:
        printError(f"Worktree '{name}' not found")
        raise typer.Exit(1)

    if shell:
        env = {**os.environ, "LJ_WORKTREE": wt.name, "LJ_BRANCH": wt.branch}
        user_shell = os.environ.get("SHELL", "/bin/bash")
        os.execve(user_shell, [user_shell], {**env, "PWD": wt.path})
    else:
        print(wt.path)


# ─── status ────────────────────────────────────────────────────────────────────


@app.command()
def status() -> None:
    """Show git status across all worktrees."""
    repo_root = _resolveRoot()
    config = _loadCfg(repo_root)
    worktrees = listWorktrees(repo_root, config)

    for wt in worktrees:
        try:
            ahead, behind = getAheadBehind(wt.branch, wt.base_branch, Path(wt.path))
            wt.ahead = ahead
            wt.behind = behind
        except LumberjackError:
            pass

    printStatusList(worktrees)


# ─── sync ──────────────────────────────────────────────────────────────────────


@app.command()
def sync(
    name: Annotated[str | None, typer.Argument(help="Worktree name")] = None,
    all_: Annotated[bool, typer.Option("--all", help="Sync all worktrees")] = False,
    merge: Annotated[bool, typer.Option("--merge", help="Merge instead of rebase")] = False,
) -> None:
    """Rebase/merge worktree onto latest base branch."""
    repo_root = _resolveRoot()
    config = _loadCfg(repo_root)

    # fetch first
    with contextlib.suppress(LumberjackError):
        runGit("fetch", "--all", "--prune", cwd=repo_root)

    targets: list[WorktreeInfo] = []
    if all_:
        targets = listWorktrees(repo_root, config)
    elif name:
        wt = getWorktree(repo_root, config, name)
        if not wt:
            printError(f"Worktree '{name}' not found")
            raise typer.Exit(1)
        targets = [wt]
    else:
        # try current directory
        try:
            branch = getCurrentBranch()
            worktrees = listWorktrees(repo_root, config)
            for wt in worktrees:
                if wt.branch == branch:
                    targets = [wt]
                    break
        except LumberjackError:
            pass

    if not targets:
        printError("No worktree to sync. Specify a name or use --all.")
        raise typer.Exit(1)

    for wt in targets:
        wt_path = Path(wt.path)
        base = wt.base_branch or config.base_branch
        cmd = "merge" if merge else "rebase"
        try:
            runGit(cmd, f"origin/{base}", cwd=wt_path)
            printSuccess(f"Synced {wt.name} ({cmd} on {base})")
        except LumberjackError as e:
            printError(f"Failed to sync {wt.name}: {e}")


# ─── agent ─────────────────────────────────────────────────────────────────────


@app.command("agent")
def agent_cmd(
    name: Annotated[str | None, typer.Argument(help="Worktree name")] = None,
    new: Annotated[str | None, typer.Option("--new", help="Create worktree + launch")] = None,
) -> None:
    """Launch coding agent in a worktree."""
    repo_root = _resolveRoot()
    config = _loadCfg(repo_root)

    if new:
        new_cmd(name=new, agent=True)
        return

    if name:
        wt = getWorktree(repo_root, config, name)
        if not wt:
            printError(f"Worktree '{name}' not found")
            raise typer.Exit(1)
    else:
        # try current worktree
        try:
            branch = getCurrentBranch()
            worktrees = listWorktrees(repo_root, config)
            wt = next((w for w in worktrees if w.branch == branch), None)
        except LumberjackError:
            wt = None

        if not wt:
            printError("Not in a worktree. Specify a name.")
            raise typer.Exit(1)

    agent_def = getAgentDef(config.default_agent)
    env_vars = buildEnvVars(wt, repo_root)
    launchAgent(agent_def, Path(wt.path), env_vars)


# ─── run-init ──────────────────────────────────────────────────────────────────


@app.command("run-init")
def run_init_cmd(
    name: Annotated[str | None, typer.Argument(help="Worktree name")] = None,
) -> None:
    """Re-run dependency install on a worktree."""
    repo_root = _resolveRoot()
    config = _loadCfg(repo_root)

    if name:
        wt = getWorktree(repo_root, config, name)
    else:
        try:
            branch = getCurrentBranch()
            worktrees = listWorktrees(repo_root, config)
            wt = next((w for w in worktrees if w.branch == branch), None)
        except LumberjackError:
            wt = None

    if not wt:
        printError("Worktree not found")
        raise typer.Exit(1)

    results = detectAndInstall(Path(wt.path), config.init)
    for desc, ok in results:
        if ok:
            printSuccess(desc)
        else:
            printError(f"{desc} failed")


# ─── env sync/ls/diff ─────────────────────────────────────────────────────────


@env_app.command("sync")
def env_sync_cmd(
    name: Annotated[str | None, typer.Argument(help="Worktree name")] = None,
) -> None:
    """Re-copy .env files from main repo."""
    repo_root = _resolveRoot()
    config = _loadCfg(repo_root)
    env_files = discoverEnvFiles(repo_root, config.env)

    if not env_files:
        printWarning("No .env files found")
        return

    targets: list[WorktreeInfo] = []
    if name:
        wt = getWorktree(repo_root, config, name)
        if not wt:
            printError(f"Worktree '{name}' not found")
            raise typer.Exit(1)
        targets = [wt]
    else:
        targets = listWorktrees(repo_root, config)

    for wt in targets:
        copied = copyEnvFiles(repo_root, Path(wt.path), env_files)
        printSuccess(f"{wt.name}: copied {copied} .env files")


@env_app.command("ls")
def env_ls_cmd() -> None:
    """List discovered .env files."""
    repo_root = _resolveRoot()
    config = _loadCfg(repo_root)
    files = listEnvFiles(repo_root, config.env)

    if not files:
        printWarning("No .env files found")
        return

    for f in files:
        print(f"  {f}")


@env_app.command("diff")
def env_diff_cmd(
    name: Annotated[str | None, typer.Argument(help="Worktree name")] = None,
) -> None:
    """Show .env differences between main repo and worktrees."""
    repo_root = _resolveRoot()
    config = _loadCfg(repo_root)
    env_files = discoverEnvFiles(repo_root, config.env)

    targets = []
    if name:
        wt = getWorktree(repo_root, config, name)
        if wt:
            targets = [wt]
    else:
        targets = listWorktrees(repo_root, config)

    for wt in targets:
        diff = diffEnvFiles(repo_root, Path(wt.path), env_files)
        has_diff = any(v != "same" for v in diff.values())
        if has_diff:
            printWarning(f"{wt.name}:")
            for path, status in diff.items():
                if status != "same":
                    print(f"    {path}: {status}")
        else:
            printSuccess(f"{wt.name}: all .env files in sync")


# ─── pr ────────────────────────────────────────────────────────────────────────


@app.command("pr")
def pr_cmd(
    name: Annotated[str | None, typer.Argument(help="Worktree name")] = None,
    draft: Annotated[bool, typer.Option("--draft", help="Create as draft")] = False,
) -> None:
    """Create a PR from a worktree branch."""
    repo_root = _resolveRoot()
    config = _loadCfg(repo_root)

    if name:
        wt = getWorktree(repo_root, config, name)
    else:
        try:
            branch = getCurrentBranch()
            worktrees = listWorktrees(repo_root, config)
            wt = next((w for w in worktrees if w.branch == branch), None)
        except LumberjackError:
            wt = None

    if not wt:
        printError("Worktree not found")
        raise typer.Exit(1)

    wt_path = Path(wt.path)

    # push branch
    try:
        runGit("push", "-u", "origin", wt.branch, cwd=wt_path)
    except LumberjackError as e:
        printError(f"Push failed: {e}")
        raise typer.Exit(1) from e

    # create PR
    cmd = [
        "gh",
        "pr",
        "create",
        "--head",
        wt.branch,
        "--base",
        wt.base_branch or config.base_branch,
    ]
    if draft:
        cmd.append("--draft")
    cmd.extend(["--fill"])

    try:
        result = subprocess.run(cmd, cwd=wt_path, capture_output=True, text=True, check=True)
        printSuccess(f"PR created: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        printError("PR creation failed (is gh CLI installed?)")
        raise typer.Exit(1) from e


# ─── clean ─────────────────────────────────────────────────────────────────────


@app.command()
def clean(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be cleaned")] = False,
) -> None:
    """Prune stale worktrees and orphaned directories."""
    repo_root = _resolveRoot()
    config = _loadCfg(repo_root)

    # prune stale git worktrees
    if dry_run:
        printSuccess("Would run: git worktree prune")
    else:
        runGit("worktree", "prune", cwd=repo_root)
        printSuccess("Pruned stale worktrees")

    # reconcile state
    worktrees = listWorktrees(repo_root, config)
    printSuccess(f"{len(worktrees)} active worktrees remaining")


# ─── config show/edit/set ─────────────────────────────────────────────────────


@config_app.command("show")
def config_show_cmd() -> None:
    """Show resolved configuration."""
    repo_root = _resolveRoot()
    config = _loadCfg(repo_root)
    printConfig(config)


@config_app.command("edit")
def config_edit_cmd() -> None:
    """Open .lumberjack.toml in $EDITOR."""
    repo_root = _resolveRoot()
    config_path = repo_root / ".lumberjack.toml"

    if not config_path.exists():
        printError("No .lumberjack.toml found. Run `lj init` first.")
        raise typer.Exit(1)

    editor = os.environ.get("EDITOR", "vi")
    os.execvp(editor, [editor, str(config_path)])


@config_app.command("set")
def config_set_cmd(
    key: Annotated[str, typer.Argument(help="Config key")],
    value: Annotated[str, typer.Argument(help="Config value")],
) -> None:
    """Set a config value."""
    repo_root = _resolveRoot()
    try:
        updateConfigField(repo_root, key, value)
        printSuccess(f"Set {key} = {value}")
    except Exception as e:
        printError(str(e))
        raise typer.Exit(1) from e


# ─── shell-init ────────────────────────────────────────────────────────────────


@app.command("shell-init")
def shell_init_cmd(
    shell: Annotated[str | None, typer.Option(help="Shell type (bash/zsh/fish)")] = None,
) -> None:
    """Output shell integration script."""
    print(generateShellInit(shell))
