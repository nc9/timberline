# Lumberjack

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
lj init --defaults          # create .lumberjack.toml
lj new auth-refactor        # create worktree + branch
lj new --type fix           # auto-named fix worktree
lj ls                       # list all worktrees
cd $(lj cd auth-refactor)   # jump into worktree
lj rm auth-refactor         # clean up
```

## Commands

| Command | Description |
|---------|-------------|
| `lj init` | Interactive setup, write `.lumberjack.toml` |
| `lj new [name]` | Create worktree (aliases: `create`) |
| `lj ls` | List worktrees (aliases: `list`). `--json`, `--paths` |
| `lj rm <name>` | Remove worktree (aliases: `remove`). `--force`, `--keep-branch`, `--all` |
| `lj cd <name>` | Print worktree path. `--shell` for subshell |
| `lj status` | Git status across all worktrees |
| `lj sync [name]` | Rebase/merge on base branch. `--all`, `--merge` |
| `lj agent [name]` | Launch coding agent in worktree. `--new` |
| `lj run-init [name]` | Re-run dependency install |
| `lj env sync [name]` | Re-copy .env files from main repo |
| `lj env ls` | List discovered .env files |
| `lj env diff [name]` | Show .env differences |
| `lj pr [name]` | Create PR via gh CLI. `--draft` |
| `lj clean` | Prune stale worktrees. `--dry-run` |
| `lj config show` | Print resolved config |
| `lj config set <k> <v>` | Set config value |
| `lj config edit` | Open config in $EDITOR |
| `lj shell-init` | Output shell integration script |

## Config

`.lumberjack.toml` in repo root:

```toml
[lumberjack]
worktree_dir = ".lj"
branch_template = "{user}/{type}/{name}"
user = "nc9"
default_type = "feature"
base_branch = "main"
naming_scheme = "minerals"  # minerals | cities | compound
default_agent = "claude"   # claude | codex | opencode | aider

[lumberjack.init]
auto_init = true
# init_command = "bun run init"
# post_init = ["echo done"]

[lumberjack.env]
auto_copy = true
patterns = [".env", ".env.*", "!.env.example", "!.env.template"]
scan_depth = 3

[lumberjack.submodules]
auto_init = true
recursive = true

[lumberjack.agent]
auto_launch = false
inject_context = true
```

## Shell Integration

```bash
# Add to .zshrc / .bashrc:
eval "$(lj shell-init)"

# Then use:
ljcd obsidian       # cd into worktree
lj-prompt           # worktree name for PS1
```

## Development

```bash
uv sync
make test     # pytest
make lint     # ruff + basedpyright
make fmt      # ruff format
make check    # all of the above
```
