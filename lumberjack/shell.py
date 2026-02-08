from __future__ import annotations

import os

_BASH_INIT = """\
# Lumberjack shell integration
ljcd() { cd "$(lj cd "$1")" || return 1; }

lj-prompt() {
    if [ -n "$LJ_WORKTREE" ]; then
        echo "🪓 $LJ_WORKTREE"
    elif [ -f .git ] && grep -q ".lj" .git 2>/dev/null; then
        echo "🪓 $(basename "$PWD")"
    fi
}
"""

_ZSH_INIT = """\
# Lumberjack shell integration
ljcd() { cd "$(lj cd "$1")" || return 1; }

lj-prompt() {
    if [[ -n "$LJ_WORKTREE" ]]; then
        echo "🪓 $LJ_WORKTREE"
    elif [[ -f .git ]] && grep -q ".lj" .git 2>/dev/null; then
        echo "🪓 $(basename "$PWD")"
    fi
}
"""

_FISH_INIT = """\
# Lumberjack shell integration
function ljcd
    cd (lj cd $argv[1]); or return 1
end

function lj-prompt
    if test -n "$LJ_WORKTREE"
        echo "🪓 $LJ_WORKTREE"
    else if test -f .git; and grep -q ".lj" .git 2>/dev/null
        echo "🪓 "(basename $PWD)
    end
end
"""


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
