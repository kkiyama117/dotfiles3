# Set up `gnupg` in the container (named volume at `GNUPGHOME`)

**Date:** 2026-07-01
**Status:** open
**Related:** [design](../specifications/implementations/2026-07-01-gnupg-container-setup-design.md), [deferred follow-up](2026-07-01-gnupg-bitwarden-import.md), [spec 20](../specifications/20-container-rules.md), [spec 21](../specifications/21-container-build-flow.md), [spec 22](../specifications/22-container-build-pre-required-envs.md), [spec 02](../specifications/02-installed-programs.md)

## Context

- `dot_zshenv.tmpl` already exports
  `GNUPGHOME="${GNUPGHOME:-$XDG_DATA_HOME/gnupg}"` (= `~/.local/share/gnupg`,
  XDG-compliant), so every zsh in the container resolves `GNUPGHOME` to that
  path. But nothing in the image provisions it:
  - `gnupg` is **not** in `dependencies/packages.toml`, so `gpg` /
    `gpg-agent` are not installed (Layer 1 pacman set has no GnuPG entry).
  - `~/.local/share/gnupg` is **not** created by Containerfile Layer 1-5
    (which provisions `cargo` / `rustup` / `mise` / `chezmoi` only).
  - There is **no persistence**: a generated key would die on `make down`.
- The container already establishes the persistence pattern for toolchain
  state: three Podman named volumes (`dotfiles_cargo` / `dotfiles_rustup` /
  `dotfiles_mise`) mounted at the XDG `~/.local/share/<tool>` paths, plus a
  host bind for the chezmoi source root at `~/.local/share/chezmoi`. Layer
  1-5 pre-creates each mountpoint owner-correct so a Podman-absent
  mountpoint is never root-created (the `/home` re-own issue documented in
  Layer 5-2). `.chezmoiignore` excludes those `.local/share/<tool>` paths
  so chezmoi never manages toolchain state.
- `--userns=keep-id` (spec 20 I2) keeps the host UID/GID inside the
  container, so a named-volume mountpoint created as `HOST_UID:HOST_GID`
  is writable by `${USERNAME}` at runtime.
- The image is secret-free (spec 20 I4 / spec 13 I-S4). A GPG private key
  is a secret, so it must never be baked into an image layer — it may live
  only in a runtime volume (or, in a later phase, be imported from
  Bitwarden; see the deferred follow-up).

## Problem

Give the container a working, persisted `gnupg` setup that honors the
existing `GNUPGHOME` and matches the established named-volume pattern,
without (a) baking any key material into image layers, (b) coupling to the
host's `~/.local/share/gnupg` existence/strict permissions, or (c)
pulling a secret-store daemon (`gnome-keyring` / `libsecret` service) that
would duplicate the Bitwarden-only secret model (spec 13 §2 Tier 1).

## Acceptance criteria

1. `gnupg` and `pinentry` are declared in `dependencies/packages.toml`
   with `manager = "pacman"`, `layer = 1`; `make gen-deps` regenerates
   `dependencies/layer_1/pacman.txt` and the spec 02 AUTO-GEN block
   (spec 20 I5 / I8 hold).
2. Containerfile Layer 1-5 creates
   `/home/${USERNAME}/.local/share/gnupg` with mode `0700`, owner
   `HOST_UID:HOST_GID` (named-volume mountpoint; owner-correct so Podman
   does not root-create it).
3. `Makefile` defines `GNUPG_VOLUME := dotfiles_gnupg` and `make up`
   mounts it at `/home/${USERNAME}/.local/share/gnupg`; `make clean`
   removes it alongside the other toolchain volumes.
4. After `make up`, `${USERNAME}` can run `gpg --version` and
   `gpg-agent --version`; `echo $GNUPGHOME` resolves to
   `~/.local/share/gnupg` (sourced from `.zshenv`).
5. `make down && make up` preserves a generated test key across restarts
   (named-volume persistence verified; spec 21 acceptance #8 analog).
6. The `~/.local/share/gnupg` directory is `0700` and `${USERNAME}`-owned
   inside the running container (gpg's strict-permission requirement is
   satisfied; not root-owned).
7. `.chezmoiignore` lists `.local/share/gnupg` so chezmoi never manages
   the keyring (consistent with the `cargo` / `rustup` / `mise` /
   `chezmoi` ignore entries).
8. No GPG key material is baked into any image layer (spec 20 I4 / spec 13
   I-S4 hold); `podman image inspect` carries no key data. The keyring
   exists only in the runtime named volume.
9. No secret-store daemon (`gnome-keyring` / a `libsecret` service) is
   installed or started; `libsecret` may arrive only as a hard dependency
   of the `pinentry` package (library, not the service).
10. Specs 01 / 02 / 20 / 21 / 22 are updated to record the new volume,
    Layer 1-5 directory, and `gnupg` / `pinentry` package entries.

## Notes

- `pinentry` (Arch `core`) is a single package that bundles
  `pinentry-tty`, `pinentry-curses`, and the default `/usr/bin/pinentry`
  wrapper; it hard-depends on `libsecret` (library only — no daemon is
  pulled). `gpg-agent` auto-starts on demand and uses the default
  pinentry; no `gpg-agent.conf` / `pinentry-program` config is baked in
  this phase (YAGNI; future opt-in).
- The deferred follow-up
  ([`2026-07-01-gnupg-bitwarden-import.md`](2026-07-01-gnupg-bitwarden-import.md))
  covers importing a real key from Bitwarden into this named volume at
  startup (Approach D from the design dialogue). This issue delivers only
  the named-volume plumbing (Approach A) so a key can be generated or
  imported manually and then persists.