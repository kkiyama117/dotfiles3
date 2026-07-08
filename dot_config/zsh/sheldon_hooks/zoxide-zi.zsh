# skim-based override of zoxide's interactive `zi`.
#
# Sourced (via `zsh-defer`) from the sheldon `[plugins.zoxide.hooks].post` hook.

function __zoxide_zi() {
    \builtin local result
    result="$( \
        ( \
            [[ "$#" -eq 0 ]] && print -r -- "$HOME"; \
            zoxide query -l -- "$@" \
        ) \
        | sk \
            --no-sort \
            --keep-right \
            --height='40%' \
            --layout='reverse' \
            --exit-0 \
            --select-1 \
            --bind='ctrl-z:ignore' \
            --preview='\command -p ls -F --color=always {}' \
        ;
    )" \
        && __zoxide_cd "$result"
}
# zle -N __zoxide_zi
# setopt noflowcontrol
# bindkey '^z' __zoxide_zi

