# zsh: kitty keyboard protocol left enabled, wedges the `execute:` minibuffer (herdr + podman)

**Date:** 2026-07-14
**Status:** in-progress
**Related:** — (design / plan to be created from this issue; implementation applied directly given small scope — see "Implementation applied")

## Context

- Shell chain: outer terminal → `herdr` (libghostty-based multiplexer) → podman PTY → container zsh 5.9.2.
- While inside zsh's `execute:` minibuffer (`execute-named-command`), it could not be aborted. Modified keys were emitted as literal text instead of being interpreted by zle:

  | Key pressed | Bytes echoed | Decoding |
  | --- | --- | --- |
  | `Esc`    | `[27u`   | `CSI 27 u` — ESC (code 27), CSI-u form |
  | `Ctrl+G` | `[103;`  | start of `CSI 103 ; 5 u` — `g` (103) + Ctrl modifier |
  | `Ctrl+C` | `[99;`   | start of `CSI 99 ; 5 u` — `c` (99) + Ctrl modifier |

  Plain letters and `Enter` kept working (only modified keys are encoded in kitty modes 1/2).
- `herdr` tracks the kitty keyboard protocol state **per pane** and re-encodes incoming key events against that state. When an inner program pushes the protocol with `CSI > <flags> u` and exits/crashes without popping (`CSI < u`), herdr keeps the pane in "kitty on" and keeps re-encoding every modified key as `CSI <code> ; <mods> u`. zsh has no matching key capability, so the sequences are inserted as literal text. The PTY chain is transparent to the escape bytes, so the state lives in herdr regardless of the podman layer.
- Investigation inside the container (the workspace IS the container):
  - `sk 5.1.0` is installed (`/usr/sbin/sk`); `fzf` is NOT installed. skim supports the kitty keyboard protocol for its TUI.
  - `~/.config/zsh/sheldon_hooks/zoxide-zi.zsh` (chezmoi source: `dot_config/zsh/sheldon_hooks/zoxide-zi.zsh`) overrides `__zoxide_zi` to pipe `zoxide query -l` through `sk` with `--height='40%' --layout='reverse' --exit-0 --select-1` and a `--preview` window. This is the only picker/TUI invoked from the zsh config and the prime suspect for pushing the kitty protocol.
  - `~/.config/zsh/rc/functions/osc_133.zsh` (`dot_config/zsh/rc/functions/osc_133.zsh`) emits only **OSC 133** (`\e]133;...`) semantic prompt markers via `precmd_functions`/`preexec_functions`. OSC sequences are NOT the kitty keyboard protocol (CSI `> <flags> u` / CSI `< u`); this file is **not** the culprit.
  - `grep` for `\e[>`, `\e[<`, `KBD_PROTOCOL`, `kitty.*keyboard`, `key-.*-kitty`, `disambiguate`, `REPORT_ALL_KEYS`, `REPORT_EVENT_TYPES`, `push-keyboard`, `pop-keyboard` across `~/.zshenv`, `~/.config/zsh/.zshrc`, `options.zsh`, `rc/functions/*.zsh`, `sheldon_hooks/*.zsh`, and the sheldon `plugins.toml` returned **no direct kitty-protocol push** in zsh config itself — the push is coming from the `sk` binary at runtime, not from an explicit zsh-side enable.
  - Sheldon plugins in `~/.config/sheldon/plugins.toml`: `zsh-defer`, `compinit`, `zsh-abbr`, `zoxide` (with the `__zoxide_zi`/sk override), `starship`, `fast-syntax-highlighting`, plus `options.zsh`, `secrets.zsh`, `rc/functions/*.zsh`. None of the plugin evals explicitly push kitty flags.
  - No `precmd`/`preexec` hook currently resets the kitty protocol state, so once `sk` leaves it on (abnormal exit, signal, or a herdr state-sync bug), the pane stays wedged until manual reset or pane kill.
- Relevant upstream herdr issues (state-tracking / re-encoding behavior, same class of symptom):
  - `ogulcancelik/herdr#81` — Shift+Enter LF re-encoded as CSI-u inside herdr panes
  - `ogulcancelik/herdr#106` — inner TUI pushes kitty kbd protocol under Ghostty
  - `ogulcancelik/herdr#1116` — Enter/Backspace double under kitty protocol

## Problem

What is leaving herdr's per-pane kitty keyboard protocol state "on" after a container-zsh interaction, and how do we prevent a crashed/abnormal `sk` (or any future inner TUI) from wedging the shell so that `Esc`/`Ctrl+G`/`Ctrl+C` are reliably interpreted by zle at every prompt?

The symptom is consistent with `sk` (invoked by `__zoxide_zi` via `zi`) pushing the kitty protocol and not popping it on some exit path, combined with herdr's pane-state tracking keeping the pushed state after `sk` is gone — but the exact exit path (skim bug vs. herdr sync bug vs. signal kill) is not yet confirmed.

## Acceptance criteria

1. After any `zi` / `__zoxide_zi` invocation (including `Ctrl-C` mid-picker, `Esc`-abort, signal kill, and `--exit-0`/`--select-1` short-circuits), `Esc`, `Ctrl+G`, `Ctrl+C`, and arrow keys are interpreted correctly by zle at the next prompt — no `[27u` / `[103;` / `[99;` literal echoes.
2. A `precmd` hook (or equivalent) drains any leftover kitty protocol stack and explicitly sets flags to 0 before each prompt, so a crashed inner TUI cannot wedge the next prompt.
3. The `execute:` minibuffer can always be aborted with `Ctrl+C` and `Esc`, via explicit `bindkey` entries that do not depend on the terminal's default key encoding. (`Ctrl+G` intentionally not bound — per maintainer decision.)
4. The fix is applied to the **chezmoi source** (`dot_config/zsh/...`), not just the rendered copy, so it survives `chezmoi apply` / `make up` re-apply.
5. The fix does not break legitimate kitty-protocol use by `sk` while it is running (the reset must happen at prompt-draw time, not while a TUI is active).
6. Reproduction: running `zi` then immediately checking `showkey -a` (or pressing `Esc`) at the next prompt shows a clean Esc/Ctrl event, not a `CSI … u` sequence, both inside herdr+podman and (if feasible) outside herdr to confirm herdr's role.

## Planned fix (plan of record)

- **`dot_config/zsh/rc/functions/kitty_reset.zsh`** (new, sourced synchronously via the existing `my_functions` sheldon plugin): a `precmd` hook (`kitty_reset_precmd`) that emits `printf '\e[<u\e[<u\e[<u\e[<u\e[<u\e[<u\e[>0u'` to drain any stacked kitty states and force flags to 0. Runs only at prompt-draw, so it does not fight `sk`/other TUIs while they are active. File name sorts before `osc_133.zsh` so the reset runs before OSC 133 prompt markers.
- **`dot_config/zsh/sheldon_hooks/zoxide-zi.zsh`**: wrap the `sk` invocation in `{ … } always { … }` so that on **every** exit path (normal, `--exit-0`, `--select-1`, signal, pipefail) the kitty stack is popped with `printf '\e[<u\e[<u\e[>0u'` before returning. Idempotent: popping an empty stack is a no-op, so a clean `sk` exit is unaffected.
- **`dot_config/zsh/rc/functions/kitty_reset.zsh`** (same file): add `bindkey '^C' send-break` and `bindkey '\e' send-break` so the minibuffer is always abortable regardless of key encoding. `^G` is intentionally NOT bound (maintainer decision). No `bindkey -e` (config already runs emacs mode; adding it would clobber a future vi-mode choice).
- **Recovery note** (not part of the fix): from the wedged `execute:` minibuffer, type `send-break` + `Enter` to abort; then `printf '\e[<u\e[<u\e[<u\e[<u\e[<u\e[<u\e[>0u'; reset` to drain the stack. If plain letters are also garbled (kitty mode 3), paste that line with `Ctrl+Shift+V` (paste bypasses the keyboard protocol) or kill the herdr pane.

## Implementation applied (2026-07-14, pending verification)

Applied directly to chezmoi source (small scope; maintainer approved). All changes survive `chezmoi apply` / `make up`.

- New: `dot_config/zsh/rc/functions/kitty_reset.zsh` — `kitty_reset_precmd` precmd + `^C`/`\e` bindkeys. Rendered to `~/.config/zsh/rc/functions/kitty_reset.zsh`.
- Edited: `dot_config/zsh/sheldon_hooks/zoxide-zi.zsh` — `__zoxide_zi` body wrapped in `{ … } always { … }` with `printf '\e[<u\e[<u\e[>0u'` in the always block. Rendered to `~/.config/zsh/sheldon_hooks/zoxide-zi.zsh`.
- Rendered via `chezmoi apply --no-tty --force ~/.config/zsh/rc/functions/kitty_reset.zsh ~/.config/zsh/sheldon_hooks/zoxide-zi.zsh` (exit 0).
- sheldon lock + cache regenerated: `sheldon lock` then `sheldon source > ~/.cache/sheldon.zsh`. New cache sources `kitty_reset.zsh` at line 12, before `osc_133.zsh` (line 13) — so `kitty_reset_precmd` runs before the OSC 133 `__prompt_precmd`, as intended.
- `zsh -n` syntax check passes for both rendered files.
- `options.zsh` was NOT modified (bindkeys live in `kitty_reset.zsh` instead, to keep `options.zsh` setopt-only and to load the bindkeys synchronously rather than via `zsh-defer`).

### Pending verification (to close the issue)

- [ ] Start a fresh interactive zsh in the herdr pane and confirm `precmd_functions` contains `kitty_reset_precmd` (`print -l $precmd_functions`).
- [ ] Run `zi`, abort with `Ctrl-C` / `Esc` mid-picker, and confirm the next prompt interprets `Esc`/`Ctrl-C`/arrows correctly (no `[27u` / `[99;` echoes). Use `showkey -a` to capture the raw bytes.
- [ ] Enter `execute:` (e.g. `Alt-x` / `Esc x`) and confirm `Ctrl-C` and `Esc` abort it.
- [ ] Confirm `bindkey` entries are live: `bindkey '^C'` and `bindkey '\e'` report `send-break`.
- [ ] Capture `echo $TERM` and `infocmp -x | grep -i kitty` from the herdr pane for the record.
- [ ] After verification, write a result-log (`docs/issues/2026-07-14-phase-zsh-kitty-protocol-stuck.md`) per `00-document-management.md` §6.6 and set this issue to `closed`.

## Notes

- `TERM` inside the Cursor subshell reports `dumb` (no real TTY), so `infocmp` could not confirm the interactive `TERM` or kitty capability advertisement here. Confirm `echo $TERM` and `infocmp -x | grep -i kitty` from the actual herdr pane during reproduction.
- The `osc_133.zsh` file was a false-positive suspect because "OSC 133" sounds related; it is a different protocol (semantic prompt markers, OSC not CSI) and does not touch the kitty keyboard protocol.
- `~/.zshenv` (chezmoi source `dot_zshenv.tmpl`) sets `TERM="${TERM:-xterm-256color}"` as a fallback only — it does not force a TERM that would enable kitty, so it is not a contributor.
- Alternative considered: disabling the kitty protocol globally in herdr config. Rejected as a primary fix because herdr's protocol support is needed for distinct `Esc` vs `Alt-Meta` and for modified-key chords; the zsh-side `precmd` reset is layer-local and does not weaken herdr.
- File reference (rendered → chezmoi source):
  - `~/.config/zsh/sheldon_hooks/zoxide-zi.zsh` → `dot_config/zsh/sheldon_hooks/zoxide-zi.zsh`
  - `~/.config/zsh/rc/functions/osc_133.zsh` → `dot_config/zsh/rc/functions/osc_133.zsh`
  - `~/.config/zsh/options.zsh` → `dot_config/zsh/options.zsh`
  - `~/.config/sheldon/plugins.toml` → `dot_config/sheldon/plugins.toml`
