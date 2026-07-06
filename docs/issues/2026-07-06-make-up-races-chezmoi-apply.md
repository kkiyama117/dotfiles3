# `make up` returns before the entrypoint finishes `chezmoi apply` (starship missing on first `make exec`)

**Date:** 2026-07-06
**Status:** open
**Related:** [spec 03](../specifications/03-makefile.md), [spec 20](../specifications/20-container-rules.md) (I10, I-RUN1)

## Context

- `make up` is `podman run -d ... sleep infinity` — **detached**, so it returns
  the moment the container is *started*, not when the entrypoint is *done*.
- The image's `ENTRYPOINT` is `container/bind/layer_5_files/entrypoint.sh`;
  `make up` passes `sleep infinity` as the CMD, which the entrypoint ultimately
  `exec`s. Before that, the entrypoint renders `~/.config/chezmoi/chezmoi.toml`,
  optionally authenticates Bitwarden, and runs
  `run_interruptible chezmoi apply --no-tty --force` (foreground, waited on).
- Per spec 20 **I10**, the final image bakes **only `~/.zshenv`** into `$HOME`
  (explicitly NOT `~/.zshrc` or anything under `~/.config`). I10's stated intent
  is to make the shell *usable* without the entrypoint (PATH/mise/XDG env, no
  `zsh/newuser` wizard), while `chezmoi apply` — which produces `~/.zshrc`,
  `~/.config/sheldon/plugins.toml`, `~/.config/starship.toml`, etc. — still
  requires the entrypoint.

## Problem

`make exec` (= `podman exec -it $(CONTAINER) zsh`) spawns a brand-new zsh
inside the already-running container, independent of where the entrypoint is
in its lifecycle. When `make exec` is run immediately after `make up`, the
exec'd zsh starts **before `chezmoi apply` has written `~/.zshrc` and
`~/.config/sheldon/plugins.toml`**. That zsh sources the baked `~/.zshenv`
(env/PATH work — the shell looks fine) but finds no `~/.zshrc`, so the
sheldon block never runs: no `zsh-defer`, no `eval "$(starship init zsh)"`,
no starship prompt for the entire session. Exiting and re-running `make exec`
works because by then the entrypoint has finished apply and the files exist.

This is the exact race I10 anticipates ("`make exec` racing the entrypoint's
`chezmoi apply`") — I10 mitigates the *wizard* failure mode but not the
*missing-sheldon/starship* failure mode.

## Acceptance criteria

1. `make up` does not return until the entrypoint's `chezmoi apply` has
   completed (success), so a `make exec` immediately after sees a fully
   applied `$HOME` (sheldon + starship load on the first interactive shell).
2. If `chezmoi apply` fails, `make up` exits non-zero with the container's
   logs surfaced (so the operator sees the apply error instead of a silently
   broken container).
3. If apply takes longer than a configurable timeout (default 120 s, covering
   Bitwarden auth + apply), `make up` exits non-zero with logs rather than
   hanging indefinitely.
4. The image still bakes only `~/.zshenv` (I10 unchanged) — the fix is a
   runtime readiness signal, not baking more files.
5. The existing `container/tests/test_entrypoint.py` signal-forwarding tests
   still pass, and new tests cover the sentinel + the `make up` wait loop.

## Planned fix

- **Entrypoint:** write a readiness sentinel (`/tmp/chezmoi-applied`) right
  after `chezmoi apply` succeeds; `rm -f` it at start so a container restart
  cannot satisfy the wait with a stale flag. Lives in `/tmp` (ephemeral per
  container; fresh on each `make up --replace`; not the bind mount, not a
  named volume).
- **Makefile `up`:** after `podman run -d`, poll `podman exec $(CONTAINER)
  test -f /tmp/chezmoi-applied` once per second up to `UP_WAIT_TIMEOUT`
  (default 120 s). Abort early if the container exits before the sentinel
  appears (apply failed); tail `podman logs` on abort.
- **Specs:** add invariant I-RUN2 to spec 20 (readiness sentinel + `make up`
  wait); update the `up` row in spec 03 and its Contract section.

## Notes

- The sentinel approach is preferred over polling `~/.zshrc` because
  `chezmoi apply` may write `~/.zshrc` mid-apply before all other files are
  down; a dedicated sentinel written as the last successful action is a
  stronger readiness guarantee.
- Baking more files into the image to avoid the wait is rejected: it would
  duplicate apply output, break the single-source-of-truth model (the baked
  `~/.zshrc` would drift from the runtime template render whenever a chezmoi
  template references runtime-only data like `bitwarden*` or `.runtime`), and
  contradicts I10's explicit "`.zshenv` only" policy.
