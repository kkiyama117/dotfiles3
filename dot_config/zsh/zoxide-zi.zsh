# skim-based override of zoxide's interactive `zi`.
#
# Sourced (via `zsh-defer`) from the sheldon `[plugins.zoxide.hooks].post`
# hook, *after* `zoxide init zsh` has been deferred-evaluated — so `__zoxide_cd`
# (defined by `zoxide init`) is guaranteed to exist when this runs. Defining
# `__zoxide_zi` here overrides the one from `zoxide init` (which uses
# `zoxide query --interactive` / fzf); since `zoxide init` defines `zi()` as
# `__zoxide_zi "$@"`, the `zi` command automatically picks up this skim-based
# version. No keybinding is set here.
#
# NOTE: the Ctrl-Z widget binding below is kept commented out for now (it
# would override any `fancy-ctrl-z`/suspend-resume binding). Uncomment to bind
# `zi` to Ctrl-Z at the zle prompt.

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