# Set up `gnupg` in the container (named volume at `GNUPGHOME`) — Design

**Status:** DRAFT
**Date opened:** 2026-07-01
**Issue:** [`../../issues/2026-07-01-gnupg-container-setup.md`](../../issues/2026-07-01-gnupg-container-setup.md)
**Author:** kiyama

## §1 Context & success criteria

`dot_zshenv.tmpl` already exports
`GNUPGHOME="${GNUPGHOME:-$XDG_DATA_HOME/gnupg}"` (i.e. `~/.local/share/gnupg`,
XDG-compliant), so every zsh invocation in the container resolves
`GNUPGHOME` to that path. The container already persists toolchain state
via three Podman named volumes (`dotfiles_cargo` / `dotfiles_rustup` /
`dotfiles_mise`) mounted at the XDG `~/.local/share/<tool>` paths, and
pre-creates each mountpoint owner-correct in Containerfile Layer 1-5 so
Podman never root-creates an absent mountpoint (the `/home` re-own
problem documented in Layer 5-2). `.chezmoiignore` excludes those
`.local/share/<tool>` paths so chezmoi never manages toolchain state.

The gap: `gnupg` is not installed, `~/.local/share/gnupg` is not
provisioned, and there is no persistence — a generated key dies on
`make down`. `--userns=keep-id` (spec 20 I2) keeps the host UID/GID
inside the container, so a `HOST_UID:HOST_GID`-owned mountpoint is
writable by `${USERNAME}` at runtime.

Success criteria (mirror the issue's acceptance, labeled for review
cross-reference):

- **S1** `gnupg` + `pinentry` declared in `dependencies/packages.toml`
  (`manager = "pacman"`, `layer = 1`); `make gen-deps` regenerates
  `dependencies/layer_1/pacman.txt` and the spec 02 AUTO-GEN block
  (spec 20 I5 / I8 hold).
- **S2** Containerfile Layer 1-5 creates
  `/home/${USERNAME}/.local/share/gnupg` with mode `0700`, owner
  `HOST_UID:HOST_GID`.
- **S3** `Makefile` defines `GNUPG_VOLUME := dotfiles_gnupg`; `make up`
  mounts it at `~/.local/share/gnupg`; `make clean` removes it.
- **S4** After `make up`, `${USERNAME}` can run `gpg --version` /
  `gpg-agent --version`; `echo $GNUPGHOME` = `~/.local/share/gnupg`.
- **S5** `make down && make up` preserves a generated test key
  (named-volume persistence; spec 21 acceptance #8 analog).
- **S6** `~/.local/share/gnupg` is `0700` and `${USERNAME}`-owned at
  runtime (gpg strict-permission satisfied; not root-owned).
- **S7** `.chezmoiignore` lists `.local/share/gnupg` (chezmoi never
  manages the keyring).
- **S8** No GPG key material baked into any image layer (spec 20 I4 /
  spec 13 I-S4 hold); keyring lives only in the runtime named volume.
- **S9** No secret-store daemon installed/started; `libsecret` may arrive
  only as a hard dependency of `pinentry` (library, not the service).
- **S10** Specs 01 / 02 / 20 / 21 / 22 updated to record the new volume,
  Layer 1-5 directory, and package entries.

## §2 Alternatives considered

- **B — Host bind mount** of `~/.local/share/gnupg` into the container.
  Rejected: couples the container to the host `GNUPGHOME`'s existence and
  strict permissions (`0700` dir, `0600` files), risks leaking host
  identity keys into the container, and breaks the project invariant that
  the container is self-contained w.r.t. toolchain state. Also the host's
  real `GNUPGHOME` may not be `~/.local/share/gnupg` (the dotfiles sets it
  there, but a host not running these dotfiles would diverge).
- **C — Ephemeral** (no persistence; regenerate/import each run).
  Rejected for daily use: a signing/decryption key the operator uses
  regularly should survive `make down && make up`; re-importing every
  start is friction this issue does not need to solve.
- **D — Named volume + Bitwarden key import at startup.** The
  persistence base is exactly Approach A; the Bitwarden-import step is a
  separable concern (it touches the entrypoint, podman secrets, and
  chezmoi `bitwardenAttachment` templates) and is deferred to
  [`../../issues/2026-07-01-gnupg-bitwarden-import.md`](../../issues/2026-07-01-gnupg-bitwarden-import.md).
  Splitting it keeps this change small (packages + dir + volume + ignore +
  spec sync) and lets a manual `gpg --generate-key` / `gpg --import` work
  immediately with persistence.

## §3 Architecture / Invariants

- **I-GPG1** — GPG keyring persistence is a Podman named volume
  `dotfiles_gnupg` mounted at `~/.local/share/gnupg`, the same pattern as
  `dotfiles_cargo` / `dotfiles_rustup` / `dotfiles_mise`. The volume is
  the sole home of the keyring; the image carries none of it.
- **I-GPG2** — `~/.local/share/gnupg` is baked owner-correct at `0700`
  in Containerfile Layer 1-5 (extension of the existing XDG-directory
  provisioning). This prevents Podman from root-creating an absent
  mountpoint (the `/home` re-own failure mode) and satisfies gpg's strict
  `0700` requirement on `GNUPGHOME`.
- **I-GPG3** — `gpg-agent` / `pinentry` are runtime, on-demand only. No
  agent is baked into the image entrypoint; gpg auto-starts `gpg-agent` on
  first use, which uses the default `/usr/bin/pinentry` wrapper.
- **I-GPG4** — No GPG key material is baked into any image layer. This
  extends spec 20 I4 / spec 13 I-S4: the build-time pre-pass (Stage 2,
  `build_mode = true`) never touches `gnupg` (no keyring exists at build
  time; the Layer 1-5 directory is empty), and the runtime keyring lives
  only in the named volume, never in an image layer or `podman inspect`.
- **I-GPG5** — `.chezmoiignore` lists `.local/share/gnupg` so chezmoi
  never manages the keyring (consistent with the existing
  `cargo` / `rustup` / `mise` / `chezmoi` ignore entries; the keyring is
  secret-adjacent state, not a dotfile).

## §4 Scope / staging breakdown

Five mechanical change areas, each independently reviewable:

1. **`dependencies/packages.toml`** — add two `[[tool]]` entries:
   `gnupg` and `pinentry`, both `manager = "pacman"`, `layer = 1`,
   `has_configs = false` (no chezmoi-managed gpg config in this phase).
   Then `make gen-deps` regenerates `dependencies/layer_1/pacman.txt` and
   the spec 02 AUTO-GEN block.
2. **`container/Containerfile` Layer 1-5** — append a separate
   `install -d -m 0700 -o ${HOST_UID} -g ${HOST_GID}
   /home/${USERNAME}/.local/share/gnupg`. Kept as a distinct directive
   (not folded into the existing `0755` `install -d`) because the gnupg
   mountpoint requires `0700` while the toolchain mountpoints use `0755`.
   Runs as `root` (the surrounding block already switches `USER root` →
   `USER ${USERNAME}`); the directory is owner-correct before any runtime
   mount.
3. **`Makefile`** — add `GNUPG_VOLUME := dotfiles_gnupg`; add
   `-v $(GNUPG_VOLUME):/home/$(USERNAME)/.local/share/gnupg` to the
   `make up` `podman run`; add `$(GNUPG_VOLUME)` to the `make clean`
   `podman volume rm` list. No new target; no change to `make build` or
   `make exec`.
4. **`.chezmoiignore`** — add `.local/share/gnupg` alongside the existing
   toolchain-volume mountpoint ignores.
5. **Spec sync** —
   - spec 01: note `dotfiles_gnupg` in the named-volumes description and
     the Layer 1-5 directory list.
   - spec 02: AUTO-GEN block refreshed by `make gen-deps` (no hand-edit).
   - spec 20: add the I-GPG invariants (this design §3); note that
     `libsecret` arrives only as a `pinentry` hard dep (library, no
     daemon), preserving the Bitwarden-only secret model (spec 13 §2
     Tier 1).
   - spec 21: extend the Layer 1-5 table row to include the gnupg
     directory; add an acceptance criterion (gpg available + persistence
     + `0700` owner-correct).
   - spec 22: add `dotfiles_gnupg` to the runtime named-volumes note in
     the `.env` contract section.

## §5 Implementation detail

### §5.1 `packages.toml` entries

```toml
[[tool]]
name = "gnupg"
manager = "pacman"
layer = 1
has_configs = false
description = "GnuPG (`gpg` / `gpg-agent`); honors GNUPGHOME from .zshenv"

[[tool]]
name = "pinentry"
manager = "pacman"
layer = 1
has_configs = false
description = "pinentry frontends (tty/curses) + default wrapper; hard-deps libsecret (library only)"
```

`has_configs = false` for both: no `gpg.conf` / `gpg-agent.conf` is
chezmoi-managed in this phase (YAGNI; gpg runs on defaults). A future
opt-in can flip `gnupg` to `has_configs = true` and add templated config
under the chezmoi source root.

### §5.2 Containerfile Layer 1-5

The existing block (as `USER root`):

```dockerfile
RUN install -d -o ${HOST_UID} -g ${HOST_GID} -m 0755 \
    /home/${USERNAME}/.local \
    /home/${USERNAME}/.local/share \
    /home/${USERNAME}/.local/share/cargo \
    /home/${USERNAME}/.local/share/rustup \
    /home/${USERNAME}/.local/share/mise \
    /home/${USERNAME}/.local/share/chezmoi
```

Append (still as `USER root`, before the closing `USER ${USERNAME}`):

```dockerfile
RUN install -d -o ${HOST_UID} -g ${HOST_GID} -m 0700 \
    /home/${USERNAME}/.local/share/gnupg
```

`0700` is mandatory for `GNUPGHOME`; a separate `RUN` keeps the mode
distinct from the `0755` toolchain dirs and makes the intent obvious in
diffs / spec 21.

### §5.3 Makefile

```makefile
GNUPG_VOLUME := dotfiles_gnupg
```

In `make up`, alongside the existing toolchain `-v` lines:

```makefile
	-v $(GNUPG_VOLUME):/home/$(USERNAME)/.local/share/gnupg \
```

In `make clean`:

```makefile
	-podman volume rm $(CARGO_VOLUME) $(RUSTUP_VOLUME) $(MISE_VOLUME) $(GNUPG_VOLUME)
```

### §5.4 `.chezmoiignore`

Add under the existing "Toolchain volume mountpoints — never managed by
chezmoi" block:

```
.local/share/gnupg
```

### §5.5 Verification

- `make gen-deps` → `dependencies/layer_1/pacman.txt` contains `gnupg` and
  `pinentry`; spec 02 AUTO-GEN block lists both under Layer 1.
- `make build` green; image Layer 1-5 creates the `0700` gnupg dir.
- `make up` → `podman exec <c> zsh -ic 'gpg --version && gpg-agent --version && echo $GNUPGHOME'`
  prints versions and `~/.local/share/gnupg`.
- `podman exec <c> zsh -c 'stat -c "%a %U:%G" ~/.local/share/gnupg'`
  → `700 <USERNAME>:<group>`.
- Generate an ephemeral test key, `make down && make up`, then `gpg
  --list-secret-keys` still lists it (named-volume persistence).
- `podman image inspect <img>` carries no key data (no `~/.local/share/gnupg`
  content in any layer; the Layer 1-5 dir is empty at build time).

## §6 Open questions

- **Q1 (pinentry package)** — Resolved. Install the single Arch `core`
  package `pinentry`; it bundles `pinentry-tty`, `pinentry-curses`, and
  the default `/usr/bin/pinentry` wrapper. It hard-depends on `libsecret`
  (library only — no `gnome-keyring` daemon is pulled), which is
  acceptable under S9 (no secret-store daemon) and does not duplicate the
  Bitwarden secret model.
- **Q2 (gpg-agent config)** — Deferred (not required). `pinentry-program`
  selection and `default-cache-ttl` tuning can be added later as
  chezmoi-managed `gpg-agent.conf` (which would flip `gnupg` to
  `has_configs = true`). gpg-agent auto-detection is sufficient now.
- **Q3 (Bitwarden key import)** — Deferred to
  [`../../issues/2026-07-01-gnupg-bitwarden-import.md`](../../issues/2026-07-01-gnupg-bitwarden-import.md).
  This design delivers only the named-volume plumbing (Approach A); a
  real key can be `gpg --generate-key`'d or `gpg --import`'ed manually and
  then persists, and the follow-up automates the import.