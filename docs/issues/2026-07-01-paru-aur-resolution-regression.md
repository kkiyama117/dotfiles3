# `paru -S` cannot resolve AUR targets in the build (regression)

**Date:** 2026-07-01
**Status:** closed (resolved in `develop` commit `a115677`; see [Resolution](#resolution-2026-07-01))
**Related:** [spec 20](../specifications/20-container-rules.md), [spec 21](../specifications/21-container-build-flow.md), [paru-aur-layer result-log](2026-06-30-phase-paru-aur-layer.md), [gnupg-container-setup (unblocked)](2026-07-01-gnupg-container-setup.md), [gnupg result-log](2026-07-01-phase-gnupg-container-setup.md)

## Context

- The `aur` stage (Containerfile Layer 4) bootstraps `paru` from the AUR
  via `makepkg -si`, then installs the Layer 4 AUR set from
  `dependencies/layer_4/paru.txt` via
  `paru -S --noconfirm --needed $pkgs` (currently `neovim-git starship tmux`).
- The `paru-aur-layer` phase result-log
  ([`2026-06-30-phase-paru-aur-layer.md`](2026-06-30-phase-paru-aur-layer.md))
  recorded a PASS on 2026-06-30 (`paru v2.1.0`, `paru --version` + `nvim --version`
  in the final image). That build reused the `aur`-stage BuildKit cache from
  the earlier successful run.
- On 2026-07-01, the gnupg-container-setup work
  ([`2026-07-01-gnupg-container-setup.md`](2026-07-01-gnupg-container-setup.md))
  added `gnupg` + `pinentry` to Layer 1 (pacman), which changed the Layer 1-2
  package list → a BuildKit cache miss → a full rebuild that **re-ran the
  `aur` stage from scratch today**, and the Layer 4-2 `paru -S` step now fails.

## Problem

`make build` fails at the `aur` stage Layer 4-2:

```
:: Resolving dependencies...
error: could not find all required packages:
    neovim-git starship tmux (target)
```

Reproduced inside the post-Layer-4-1 cached image (paru 2.1.0 installed,
the state right before the failing step), with the BuildKit cache mounts
present:

| Command | Result |
|---|---|
| `paru -Si neovim-git` | **PASS** — `Repository : aur`, full AUR info returned (AUR RPC reachable) |
| `pacman -Si starship` | **PASS** — `Repository : extra` (repo) |
| `pacman -Si tmux` | **PASS** — `Repository : extra` (repo) |
| `paru -S --print neovim-git starship tmux` | **FAIL** — `error: target not found: neovim-git` |
| `ls /var/lib/pacman/sync/` | `community.db core.db extra.db` present (Layer 4-1's `sudo pacman -Sy` ran) |
| host `curl https://aur.archlinux.org/rpc/?v=5&type=info&arg[]=neovim-git` | **PASS** — HTTP 200 |
| host `git ls-remote https://aur.archlinux.org/paru.git` | **PASS** |

So AUR RPC and the pacman sync DBs are both reachable/populated, and `paru -Si`
finds `neovim-git` on the AUR — but `paru -S` (install resolution) drops
`neovim-git` with `target not found`. This is a `paru 2.1.0` `-S`-path
classification failure for the AUR-only target, **not** a network/repo issue
and **not** caused by the gnupg/pinentry change (gnupg is in Layer 1, fully
isolated from the `aur` stage; the failure is in paru's combined AUR+repo
resolver).

The build log also emits a locale warning on every `RUN`:

```
/bin/sh: warning: setlocale: LC_ALL: cannot change locale (ja_JP.UTF-8): No such file or directory
```

`dot_zshenv.tmpl` exports `LANG/LC_ALL=ja_JP.UTF-8`, but the Manjaro base
image does not generate that locale. **Working hypothesis (not confirmed):**
`paru` identifies AUR packages by parsing `pacman`'s `target not found:`
stderr lines; if the locale breakage alters `pacman`'s message format or
`paru`'s regex matching, `paru` mis-classifies AUR-only targets as truly
absent and hands the whole set to `pacman`, which fails on the AUR-only
one.

## Acceptance criteria

1. `make build` (full, cache-bust) succeeds end-to-end through the `aur`
   stage on 2026-07-01+; `paru -S --noconfirm --needed neovim-git starship
   tmux` resolves and installs (or `--needed` no-ops the already-built ones).
2. The root cause is identified and fixed (e.g. locale generation,
   `LC_ALL=C`/`LANG=C` in the build `RUN`s, a `paru` config flag, or a
   `paru` upgrade) — with a recorded diagnosis, not just a workaround that
   happens to pass.
3. `podman build --target aur` succeeds in isolation and the resulting image
   has `paru`, `starship`, `tmux`, and `neovim-git` on PATH (spec 21
   acceptance #9/#10 restored).
4. A cache-bust rebuild (e.g. touching the Layer 1 package list) still
   passes — i.e. the fix is not dependent on stale cache.
5. The gnupg-container-setup runtime smoke gate (parent issue acceptance
   S3/S5: `make up` + `gpg --version` + named-volume persistence) becomes
   unblocked and runnable.

## Notes

- This regression is **orthogonal to the gnupg work**; the gnupg changes
  (Tasks 1–5 of the gnupg plan) are committed and verified at the
  `toolchain` stage (`gpg 2.4.9`, `pinentry` frontends present, `~/.local/share/gnupg`
  `700 kiyama:kiyama` and empty). Only the gnupg *runtime* acceptance
  (`make up`) is blocked, because `make up` requires the full `runtime`
  image which requires the `aur` stage to build.
- Out-of-scope for this issue: changing which AUR packages are in
  `layer_4/paru.txt`; that is a `packages.toml` concern. This issue is about
  `paru -S` resolution failing for *any* AUR-only target, regardless of the
  list contents.
- Suggested first diagnostic step: in the failing container, run
  `LANG=C LC_ALL=C paru -S --print neovim-git starship tmux` to test the
  locale hypothesis; if it resolves, the fix is locale-scoping the build
  `RUN`s (and/or generating `ja_JP.UTF-8` in the base image).

## Resolution (2026-07-01)

**Root cause (not the locale hypothesis):** the build `RUN`s use
`zsh -c '... paru -S --noconfirm --needed $pkgs ...'`. Unlike `sh`/`bash`, **zsh
does not word-split a bare unquoted parameter by default**, so `$pkgs` (the
space-joined package list `neovim-git starship tmux`) was passed to `paru -S`
as **one malformed target** (literally `"neovim-git starship tmux"`), which
paru reported as `could not find all required packages: neovim-git starship
tmux (target)`. The AUR-RPC and pacman-DB diagnostics all passed because
`paru -Si`/`pacman -Si` take single args and were unaffected.

**Fix (merged in `develop`, commit `a115677` "word-split $pkgs in zsh -c
RUN steps for paru/cargo installs"):** use zsh's explicit split operator
`${=pkgs}` instead of `$pkgs` in both the Layer 4-2 `paru -S` and the
Layer 3 `cargo install` RUNs.

**Verification:** after rebasing `gnupg_container` onto `develop`, a full
clean-slate `make build` succeeded through the `aur` stage (`starship`,
`tmux`, and `neovim-git` all resolved and installed), and the gnupg
runtime smoke gate completed green — see
[`2026-07-01-phase-gnupg-container-setup.md`](2026-07-01-phase-gnupg-container-setup.md).
All five acceptance criteria below are met (the locale hypothesis was a
red herring; no locale change is required).

This issue also retroactively re-confirms spec 21 acceptance #9/#10
(`paru`/AUR packages installable from `layer_4/paru.txt`).