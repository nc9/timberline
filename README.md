# Timberline

Git worktree manager for parallel coding agent development.

## Install

```bash
uv tool install .
# or
uv pip install -e .
```

## Quick Start

```bash
cd your-repo
tl init --defaults          # create .timberline.toml
tl new auth-refactor        # create worktree + branch
tl new --type fix           # auto-named fix worktree
tl ls                       # list all worktrees
cd $(tl cd auth-refactor)   # jump into worktree
tl rm auth-refactor         # clean up
```

## Commands

| Command | Description |
|---------|-------------|
| `tl init` | Interactive setup, write `.timberline.toml` |
| `tl new [name]` | Create worktree (aliases: `create`) |
| `tl ls` | List worktrees (aliases: `list`). `--json`, `--paths` |
| `tl rm <name>` | Remove worktree (aliases: `remove`). `--force`, `--keep-branch`, `--all` |
| `tl cd <name>` | Print worktree path. `--shell` for subshell |
| `tl status` | Git status across all worktrees |
| `tl sync [name]` | Rebase/merge on base branch. `--all`, `--merge` |
| `tl agent [name]` | Launch coding agent in worktree. `--new` |
| `tl run-init [name]` | Re-run dependency install |
| `tl env sync [name]` | Re-copy .env files from main repo |
| `tl env ls` | List discovered .env files |
| `tl env diff [name]` | Show .env differences |
| `tl pr [name]` | Create PR via gh CLI. `--draft` |
| `tl clean` | Prune stale worktrees. `--dry-run` |
| `tl config show` | Print resolved config |
| `tl config set <k> <v>` | Set config value |
| `tl config edit` | Open config in $EDITOR |
| `tl shell-init` | Output shell integration script |

## Config

`.timberline.toml` in repo root:

```toml
[timberline]
worktree_dir = ".tl"
branch_template = "{user}/{type}/{name}"
user = "nc9"
default_type = "feature"
base_branch = "main"
naming_scheme = "minerals"  # minerals | cities | compound
default_agent = "claude"   # claude | codex | opencode | aider

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
```

## Shell Integration

```bash
# Add to .zshrc / .bashrc:
eval "$(tl shell-init)"

# Then use:
tlcd obsidian       # cd into worktree
tl-prompt           # worktree name for PS1
```

## Development

```bash
uv sync
make test     # pytest
make lint     # ruff + basedpyright
make fmt      # ruff format
make check    # all of the above
```
