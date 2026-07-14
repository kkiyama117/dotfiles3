# Kitty keyboard protocol hygiene + always-abort minibuffer bindings.
#
# herdr tracks the kitty keyboard protocol per pane. An inner TUI that pushes
# the protocol (`CSI > <flags> u`) and exits/crashes without popping leaves
# the pane in "kitty on", so herdr keeps re-encoding modified keys as
# `CSI <code> ; <mods> u`; zsh inserts them as literal text and the line
# editor wedges (`Esc` -> `[27u`, `^C` -> `[99;`, `^G` -> `[103;`, etc.).
#
# `sk` (skim), invoked by `__zoxide_zi` (the `zi` command), is the known
# offender in this config; `__zoxide_zi` also pops on its own exit path. This
# file is the layer-local safety net so ANY inner TUI that leaks the protocol
# is cleaned up before the next prompt is drawn. It does not interfere with
# TUIs that legitimately push the protocol while they run — they push while
# active and the next prompt drains whatever they left.
#
# Sourced synchronously via the sheldon `my_functions` plugin (apply=['source']),
# so the precmd is registered before the first prompt. File name sorts before
# `osc_133.zsh`, so this precmd runs before the OSC 133 prompt markers.

# Drain any leftover kitty keyboard-protocol stack and force flags to 0.
# `CSI < u` pops; popping an empty stack sets flags to the default (0).
# `CSI > 0 u` explicitly disables all flags. The stack stays bounded: each
# prompt's pops drain the previous prompt's push plus any TUI leftovers, so
# the depth oscillates near 0/1 rather than growing.
kitty_reset_precmd() {
    printf '\e[<u\e[<u\e[<u\e[<u\e[<u\e[<u\e[>0u'
}
precmd_functions+=(kitty_reset_precmd)

# Always-abort bindings for the zle line editor / minibuffer (e.g. the
# `execute:` prompt from `execute-named-command`). `^G` is intentionally NOT
# bound here.
#
# `^C` -> send-break: clean zle-level abort on top of the default SIGINT path.
# `\e` -> send-break: make bare Esc abort the line / minibuffer. Without this,
#         bare Esc is just the meta-prefix and does nothing on its own, so the
#         `execute:` minibuffer cannot be Esc-aborted. NOTE: this also makes
#         Esc cancel the current line at the normal prompt (after KEYTIMEOUT);
#         tune `KEYTIMEOUT` down (e.g. `KEYTIMEOUT=10`) if Esc-meta sequences
#         feel sluggish. In vi mode this would clash with Esc-to-command-mode,
#         but this config runs emacs mode (no `bindkey -v`).
bindkey '^C' send-break
bindkey '\e'  send-break
