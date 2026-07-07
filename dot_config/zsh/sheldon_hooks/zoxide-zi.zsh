# skim-based override of zoxide's interactive `zi`.
#
# Sourced (via `zsh-defer`) from the sheldon `[plugins.zoxide.hooks].post` hook.

function __zoxide_zi() {
    \builtin local result
    result="$( \
        zoxide query -ls -- "$@" \
        | sk \
            --delimiter='[^\t\n ][\t\n ]+' \
            -n2.. \
            --no-sort \
            --keep-right \
            --height='40%' \
            --layout='reverse' \
            --exit-0 \
            --select-1 \
            --bind='ctrl-z:ignore' \
            --preview='\command -p ls -F --color=always {2..}' \
        ;
    )" \
        && __zoxide_cd "${result:7}"
}
# zle -N __zoxide_zi
# setopt noflowcontrol
# bindkey '^z' __zoxide_zi

