from __future__ import annotations

import os
from pathlib import Path

_BASH_INIT = """\
# Timberline shell integration
tlcd() { cd "$(tl cd "$1")" || return 1; }
tln() { local d; d="$(tl new "$@")" && cd "$d" || return 1; }
tldone() { local d; d="$(tl done "$@")" && cd "$d" || return 1; }
tlunarchive() { local d; d="$(tl unarchive "$@")" && cd "$d" || return 1; }

tl-prompt() {
    if [ -n "$TL_WORKTREE" ]; then
        echo "🪓 $TL_WORKTREE"
    elif [ -f .git ] && grep -q ".timberline/projects/" .git 2>/dev/null; then
        echo "🪓 $(basename "$PWD")"
    fi
}
"""

_ZSH_INIT = """\
# Timberline shell integration
tlcd() { cd "$(tl cd "$1")" || return 1; }
tln() { local d; d="$(tl new "$@")" && cd "$d" || return 1; }
tldone() { local d; d="$(tl done "$@")" && cd "$d" || return 1; }
tlunarchive() { local d; d="$(tl unarchive "$@")" && cd "$d" || return 1; }

tl-prompt() {
    if [[ -n "$TL_WORKTREE" ]]; then
        echo "🪓 $TL_WORKTREE"
    elif [[ -f .git ]] && grep -q ".timberline/projects/" .git 2>/dev/null; then
        echo "🪓 $(basename "$PWD")"
    fi
}
"""

_FISH_INIT = """\
# Timberline shell integration
function tlcd
    cd (tl cd $argv[1]); or return 1
end

function tln
    set -l d (tl new $argv); and cd $d; or return 1
end

function tldone
    set -l d (tl done $argv); and cd $d; or return 1
end

function tlunarchive
    set -l d (tl unarchive $argv); and cd $d; or return 1
end

function tl-prompt
    if test -n "$TL_WORKTREE"
        echo "🪓 $TL_WORKTREE"
    else if test -f .git; and grep -q ".timberline/projects/" .git 2>/dev/null
        echo "🪓 "(basename $PWD)
    end
end
"""

_START_MARKER = "# timberline:start"
_END_MARKER = "# timberline:end"


def detectShell() -> str:
    shell = os.environ.get("SHELL", "/bin/bash")
    name = os.path.basename(shell)
    if name in ("bash", "zsh", "fish"):
        return name
    return "bash"


def generateShellInit(shell: str | None = None) -> str:
    s = shell or detectShell()
    match s:
        case "zsh":
            return _ZSH_INIT
        case "fish":
            return _FISH_INIT
        case _:
            return _BASH_INIT


def rcFilePath(shell: str) -> Path:
    if shell == "fish":
        return Path.home() / ".config" / "fish" / "config.fish"
    if shell == "zsh":
        return Path.home() / ".zshrc"
    return Path.home() / ".bashrc"


def installShellInit(shell: str) -> tuple[Path, bool]:
    """Append/replace shell init block between markers. Returns (path, changed)."""
    rc = rcFilePath(shell)
    block = f"{_START_MARKER}\n{generateShellInit(shell)}{_END_MARKER}\n"

    if rc.exists():
        content = rc.read_text()
    else:
        rc.parent.mkdir(parents=True, exist_ok=True)
        content = ""

    # replace existing block
    start_idx = content.find(_START_MARKER)
    end_idx = content.find(_END_MARKER)
    if start_idx != -1 and end_idx != -1:
        old_block = content[start_idx : end_idx + len(_END_MARKER)]
        if content[end_idx + len(_END_MARKER) : end_idx + len(_END_MARKER) + 1] == "\n":
            old_block += "\n"
        new_content = content[:start_idx] + block + content[start_idx + len(old_block) :]
        if new_content == content:
            return rc, False
        rc.write_text(new_content)
        return rc, True

    # append
    if content and not content.endswith("\n"):
        content += "\n"
    content += "\n" + block
    rc.write_text(content)
    return rc, True


def uninstallShellInit(shell: str) -> tuple[Path, bool]:
    """Remove shell init block between markers. Returns (path, changed)."""
    rc = rcFilePath(shell)
    if not rc.exists():
        return rc, False

    content = rc.read_text()
    start_idx = content.find(_START_MARKER)
    end_idx = content.find(_END_MARKER)
    if start_idx == -1 or end_idx == -1:
        return rc, False

    end_pos = end_idx + len(_END_MARKER)
    if end_pos < len(content) and content[end_pos] == "\n":
        end_pos += 1

    # remove leading blank line if present
    if start_idx > 0 and content[start_idx - 1] == "\n":
        start_idx -= 1

    new_content = content[:start_idx] + content[end_pos:]
    rc.write_text(new_content)
    return rc, True
