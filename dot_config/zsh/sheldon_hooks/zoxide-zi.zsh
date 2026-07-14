# skim-based override of zoxide's interactive `zi`.
#
# Sourced (via `zsh-defer`) from the sheldon `[plugins.zoxide.hooks].post` hook.

function __zoxide_zi() {
    \builtin local result
    {
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
    } always {
        # Pop any kitty keyboard-protocol state `sk` may have left pushed
        # (abnormal exit / signal / --exit-0 / --select-1 / pipefail) so herdr
        # does not keep re-encoding modified keys as CSI-u. The precmd in
        # kitty_reset.zsh is the safety net; this runs immediately on `sk`
        # exit so we don't depend on the next prompt firing. Idempotent:
        # popping an empty stack is a no-op, so a clean `sk` exit is unaffected.
        printf '\e[<u\e[<u\e[>0u'
    }
}
# zle -N __zoxide_zi
# setopt noflowcontrol
# bindkey '^z' __zoxide_zi

