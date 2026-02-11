# Timberline

Git worktree manager for parallel coding agent development.

## Features

- **Agent session linking** — symlinks worktree's agent session data to the main repo, so coding agents inherit full conversation history and memory across worktrees
- **Auto-launch coding agents** — spawn Claude, Codex, OpenCode, or Aider directly into a worktree (`tl new --agent`)
- **Agent context injection** — auto-injects worktree metadata (branch, base, sibling worktrees) into agent config files (CLAUDE.md, AGENTS.md)
- **Auto-init dependencies** — detects & installs via bun/npm/pnpm/yarn/uv/pip/cargo/go/composer/bundle on worktree creation
- **Auto-copy .env files** — glob-based discovery with include/exclude patterns, sync & diff commands
- **Auto-init submodules** — recursive submodule setup on worktree creation
- **Archive & restore** — `tl done` soft-removes a worktree (keeps directory, marks archived), warns about uncommitted/unpushed work; `tl unarchive` restores it
- **Shell integration** — `tlcd`, `tln`, `tldone`, `tlunarchive` shell aliases, `tl-prompt` for PS1, auto-install for bash/zsh/fish
- **Creative naming schemes** — minerals, cities, or compound names for auto-named worktrees
- **Branch templates** — configurable `{user}/{type}/{name}` patterns for consistent naming
- **Land workflow** — pre-land checks → push → PR creation in one command
- **Multi-worktree status** — git status, ahead/behind tracking across all worktrees
- **Sync all worktrees** — rebase or merge all worktrees on latest base branch

## Install

```bash
# global CLI (recommended)
uv tool install timberline

# or with pip
pip install timberline
```

## Upgrade

```bash
uv tool upgrade timberline
```

## Setup

Setup shell aliases

```bash
tl setup
```

## Quick Start

```bash
cd your-repo
tl init                     # create .timberline.toml
tl new auth-refactor        # create worktree + branch
tl new --type fix           # auto-named fix worktree
tl ls                       # list all worktrees
tlcd auth-refactor          # jump into worktree
tl land                     # run checks, push, and create PR
tldone                      # archive worktree + cd back to main repo
tl rm auth-refactor         # full removal (or skip if archived)
```

## Getting Started

Run `tl init` inside any git repo to create `.timberline.toml`. The wizard auto-detects:

- **Project name** — defaults to the repo directory name, used for global worktree storage at `~/.timberline/projects/<name>/`
- **Branch prefix** from your git user
- **Base branch** (main/master/develop)
- **Package manager** (bun, npm, pnpm, yarn, uv, pip, cargo, go, composer, bundle) for dependency install
- **Pre-land checks** (Makefile targets, npm scripts like `lint`, `test`, `check`)
- **Default agent** (claude, codex, opencode, aider) if installed

Worktrees are stored globally at `~/.timberline/projects/<project>/worktrees/` — fully outside the repo tree. This prevents agents from accidentally writing files into the parent repo.

Use `--defaults` to skip prompts and accept detected values.

## Create & Enter a Worktree

```bash
tl new auth-refactor            # named worktree
tl new --type fix               # auto-named (minerals, cities, or compound)
tl new --agent                  # create + launch coding agent
```

Enter a worktree:

```bash
cd $(tl cd auth-refactor)       # subshell-friendly
```

Or with shell integration (`tl setup`):

```bash
tlcd auth-refactor              # cd directly
```

Each worktree gets its own branch (from `branch_template`), dependencies installed via `auto_init`, and `.env` files copied from the main repo.

## Agent Session Linking

When using Claude Code, each worktree normally gets a fresh session with no history. Enable session linking to share conversation history, memory, and project context across all worktrees:

```bash
tl config set agent.link_project_session true
```

This symlinks each worktree's Claude project data directory (`~/.claude/projects/<encoded-worktree-path>`) to the main repo's project directory. Your agent sees the same session history, CLAUDE.md memory, and project context regardless of which worktree you're in.

- Created automatically on `tl new`
- Cleaned up on `tl rm`
- Skip for a single worktree with `tl new --no-link`

## Sync with Base Branch

```bash
tl sync                     # rebase current worktree onto base
tl sync auth-refactor       # rebase specific worktree
tl sync --all               # rebase all worktrees
tl sync --merge             # merge instead of rebase
```

Fetches all remotes, then rebases (default) or merges onto `origin/{base_branch}`. Each worktree tracks its own base branch from creation — no hardcoded "main".

## Land a PR

```bash
tl land auth-refactor           # checks → push → PR
tl land --draft                 # create as draft PR
tl land --skip-checks           # bypass pre-land checks
```

`tl land` runs your configured `pre_land` command (e.g. `make check`), pushes the branch, then creates a PR via `gh`. Configure it in `.timberline.toml`:

```toml
[timberline]
pre_land = "make check"  # or "bun run lint && bun run test", etc.
```

## Archive a Worktree

When you're done with a worktree but want to keep it around (e.g. waiting for PR review), use `tl done` to archive it:

```bash
tldone                          # archive current worktree + cd back to repo root
tl done --name auth-refactor    # archive by name
tl done --force                 # skip uncommitted/unpushed warnings
```

`tl done` warns if you have uncommitted changes or unpushed commits before archiving. Archived worktrees are hidden from `tl ls` but the directory stays on disk. To see them:

```bash
tl ls --archived                # list only archived worktrees
```

Restore an archived worktree:

```bash
tl unarchive auth-refactor      # restore to active
tlunarchive auth-refactor       # restore + cd into it
```

`tl rm` still works on archived worktrees for full removal.

## Commands

| Command | Description |
|---------|-------------|
| `tl init` | Interactive setup, write `.timberline.toml` |
| `tl new [name]` | Create worktree (aliases: `create`) |
| `tl ls` | List worktrees (aliases: `list`). `--json`, `--paths`, `--archived` |
| `tl done [--name]` | Archive worktree, print repo root. `--force` |
| `tl unarchive <name>` | Restore archived worktree |
| `tl rm <name>` | Remove worktree (aliases: `remove`). `--force`, `--keep-branch`, `--all` |
| `tl cd <name>` | Print worktree path. `--shell` for subshell |
| `tl status` | Git status across all worktrees |
| `tl sync [name]` | Rebase/merge on base branch. `--all`, `--merge` |
| `tl land [name]` | Run checks, push, and create PR. `--draft`, `--skip-checks` |
| `tl rename <branch>` | Rename worktree's git branch. `-n <name>` |
| `tl agent [name]` | Launch coding agent in worktree. `--new` |
| `tl run-init [name]` | Re-run dependency install |
| `tl pr [name]` | Create PR via gh CLI. `--draft` |
| `tl env sync [name]` | Re-copy .env files from main repo |
| `tl env ls` | List discovered .env files |
| `tl env diff [name]` | Show .env differences |
| `tl clean` | Prune stale worktrees. `--dry-run` |
| `tl setup` | Install shell integration into rc file. `--uninstall` |
| `tl shell-init` | Output shell integration script |
| `tl config show` | Print resolved config |
| `tl config set <k> <v>` | Set config value |
| `tl config edit` | Open config in $EDITOR |

## Config

`.timberline.toml` in repo root:

```toml
[timberline]
project_name = "my-project"  # global storage name (~/.timberline/projects/<name>/)
branch_template = "{user}/{type}/{name}"
user = "nc9"
default_type = "feature"
base_branch = "main"
naming_scheme = "minerals"  # minerals | cities | compound
default_agent = "claude"   # claude | codex | opencode | aider
pre_land = "make check"    # command to run before pushing

[timberline.init]
auto_init = true
# init_command = "bun run init"
# post_init = ["echo done"]

[timberline.env]
auto_copy = true
patterns = [".env", ".env.*", "!.env.example", "!.env.template"]
scan_depth = 3

[timberline.submodules]
auto_init = true
recursive = true

[timberline.agent]
auto_launch = false
inject_context = true
link_project_session = false  # symlink worktree agent session to main repo
```

## Shell Integration

```bash
# Automatic install:
tl setup

# Or manually add to .zshrc / .bashrc:
eval "$(tl shell-init)"
```

### Shell Aliases

Installed by `tl setup` (bash/zsh/fish):

| Alias | Description |
|-------|-------------|
| `tln [args]` | Create worktree + cd into it (`tl new` wrapper) |
| `tlcd <name>` | cd into a worktree |
| `tldone [args]` | Archive current worktree + cd back to repo root |
| `tlunarchive <name>` | Restore archived worktree + cd into it |
| `tl-prompt` | Print worktree name for PS1 prompt integration |

## Development

```bash
uv sync
make test     # pytest
make lint     # ruff + basedpyright
make fmt      # ruff format
make check    # all of the above
```
