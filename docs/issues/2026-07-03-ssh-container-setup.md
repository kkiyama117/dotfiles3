# Set up SSH file keys in the container (named volume at `~/.ssh`)

**Date:** 2026-07-03
**Status:** closed (see [result-log](2026-07-03-phase-ssh-container-setup.md))
**Related:** [deferred: chezmoi SSH config + GPG auth](2026-07-03-ssh-container-config-setup.md), [deferred: Bitwarden key import](2026-07-03-ssh-bitwarden-import.md), [GPG plumbing (closed)](2026-07-01-gnupg-container-setup.md), [GPG manual import (closed)](2026-07-02-gnupg-host-key-import.md), [spec 20](../specifications/20-container-rules.md), [spec 21](../specifications/21-container-build-flow.md), [spec 22](../specifications/22-container-build-pre-required-envs.md), [spec 02](../specifications/02-installed-programs.md), [host config inventory §13](../references/host_config_list.md)

## Context

- `openssh` is already declared in `dependencies/packages.toml` (`manager =
  "pacman"`, `layer = 1`, `has_configs = true`). After `make up`, `ssh -V`
  works, but there is **no** persisted `~/.ssh` directory and **no** private
  keys inside the container.
- The established persistence pattern uses Podman named volumes at XDG paths
  (`dotfiles_cargo`, `dotfiles_rustup`, `dotfiles_mise`, `dotfiles_gnupg`).
  SSH client keys belong in `~/.ssh` with mode `0700` and must survive
  `make down && make up`.
- GPG signing for git is already handled via `dotfiles_gnupg` (spec 23). **This
  issue is file-key SSH only** — no `gpg-agent` SSH support, no chezmoi-managed
  `~/.ssh/config`. Git-over-SSH via GPG auth is deferred to
  [`2026-07-03-ssh-container-config-setup.md`](2026-07-03-ssh-container-config-setup.md).
- The image must stay secret-free (spec 13 I-S3 / I-S4 / spec 20 I4). Private
  keys live only in the runtime named volume (or are imported at runtime), never
  in image layers.
- `docs/references/host_config_list.md` §13 notes `run_after_install-ssh-keys.sh.tmpl`
  as aspirational; automated Bitwarden import is a **separate deferred issue**
  ([`2026-07-03-ssh-bitwarden-import.md`](2026-07-03-ssh-bitwarden-import.md)).

## Problem

Give the container a working, persisted **file-based SSH client keyring** at
`~/.ssh` that matches the named-volume pattern used for GPG and toolchain
state, without (a) baking key material into image layers, (b) bind-mounting the
host's `~/.ssh` (agent socket / lock / permission coupling), or (c) pulling in
GPG-agent SSH wiring or chezmoi-managed Host config (deferred siblings).

## Acceptance criteria

1. Containerfile Layer **1-7** creates `/home/${USERNAME}/.ssh` with mode
   `0700`, owner `HOST_UID:HOST_GID` (named-volume mountpoint; owner-correct so
   Podman does not root-create it — mirror Layer 1-6 / I-GPG2).
2. `Makefile` defines `SSH_VOLUME := dotfiles_ssh` and `make up` mounts it at
   `/home/${USERNAME}/.ssh`; `make clean` removes it alongside the other named
   volumes.
3. After `make up`, `${USERNAME}` can run `ssh -V`; `stat ~/.ssh` shows `0700`
   and `${USERNAME}` ownership inside the running container.
4. `make down && make up` preserves key material written into the volume
   (named-volume persistence verified with a test key pair — spec 21 acceptance
   #8 analog).
5. `.chezmoiignore` excludes **secret key material** under `.ssh/` (patterns
   such as `.ssh/id_*`, `.ssh/*_ed25519`, `.ssh/*_rsa`, `.ssh/*_ecdsa`, and
   sk variants). Chezmoi must not manage private keys. The entire `.ssh` tree
   is **not** ignored (unlike `.local/share/gnupg`) so a future config issue can
   manage non-secret files under `.ssh/`.
6. No SSH private key material is baked into any image layer (spec 20 I4 / spec
   13 I-S4 hold); image inspection uses an entrypoint override and confirms
   `~/.ssh` is empty before first volume seed.
7. Specs **20 / 21 / 22** record the new volume, Layer 1-7 directory, and
   invariants `I-SSH1..I-SSH6` (draft below). Spec 02 verified (openssh entry
   already present; no generator change required).
8. **Manual import path documented** (issue result-log or lightweight spec 25
   §manual — full spec 25 deferred to config issue): operator can seed the
   volume from the host via `podman cp` (mirror spec 23 §3 Approach B for GPG).
   After import, file presence and permissions are verified, and a smoke SSH
   command using `ssh -i ~/.ssh/<key>` to a known host succeeds when the
   operator supplies Host/config on the command line or via a **volume-local**
   `~/.ssh/config` hand edit (not chezmoi-managed in this issue). No
   `ssh-add` / agent requirement belongs to this plumbing issue.

### Draft invariants (to land in spec 20)

- **I-SSH1:** `dotfiles_ssh` named volume at `~/.ssh`; no host bind mount.
- **I-SSH2:** Layer 1-7 pre-creates `0700` owner-correct mountpoint.
- **I-SSH3:** No private key material in image layers.
- **I-SSH4:** `.chezmoiignore` excludes secret key filename patterns under
  `.ssh/`; chezmoi never manages private keys.
- **I-SSH5:** `make clean` removes `dotfiles_ssh`; rollout docs warn that
  targeted `podman volume rm dotfiles_ssh` resets keys only (preserves
  `dotfiles_gnupg` — do **not** recommend `make clean` for SSH-only reset; cargo
  / GPG precedent).
- **I-SSH6:** The plumbing phase does not wire `ssh-agent`, `SSH_AUTH_SOCK`, or
  GPG-agent SSH support; those belong to the deferred config/GPG issue.

## Out of scope (explicit)

- Chezmoi-managed `~/.ssh/config` or Host fragments →
  [`2026-07-03-ssh-container-config-setup.md`](2026-07-03-ssh-container-config-setup.md).
- GPG `[A]` subkey SSH auth (`enable-ssh-support`, `SSH_AUTH_SOCK`) → same
  deferred config issue.
- Bitwarden / `run_after_install-ssh-keys.sh.tmpl` automation →
  [`2026-07-03-ssh-bitwarden-import.md`](2026-07-03-ssh-bitwarden-import.md).
- Inbound `authorized_keys` / `sshd` in the container.
- Generator / `packages.toml` schema changes (`openssh` already at layer 1).

## Notes

- **YAGNI:** No YAML manifest for Host selection; no chezmoi SSH config in this
  phase. The operator may hand-edit `~/.ssh/config` on the volume until the
  config issue lands.
- **Rollout safety:** An existing container without the volume gets an empty
  `~/.ssh` on first `make up`. To reset keys only:
  `podman volume rm dotfiles_ssh` (NOT `make clean`, which also wipes GPG).
- **Verification sketch:** generate or copy a test ed25519 key into the volume;
  `make down && make up`; confirm `stat` perms and key still present.

## Status update (2026-07-03 — complete)

Complete. Plumbing + spec sync implemented (2 commits 9b9362a / 9f3d2f8) +
task-review Minor 1-2 fix (e0d38e5); implementation task review Approved (no
Critical/Important). Phase 3 build green: `make build` (Layer 1-7 new); image
inspect `~/.ssh` = `0700 kiyama:kiyama`, empty; `ssh -V` = `OpenSSH_10.3p1`;
manual `podman cp` import + `make down && make up` persistence verified (test
ed25519 key survives, same fingerprint); GPG key in `dotfiles_gnupg`
preserved (no regression). Spec 25 §1-3 normative; §4+ deferred to config
issue. See the
[result-log](2026-07-03-phase-ssh-container-setup.md).

## Status update (2026-07-03)

Issue filed. Scope narrowed from an earlier dialogue that combined GPG SSH auth,
chezmoi config fragments, and file keys. Implementation follows the GPG
plumbing precedent (`gnupg-container-setup` → manual import → deferred Bitwarden).

Design drafted at
[`docs/specifications/implementations/2026-07-03-ssh-container-setup-design.md`](../specifications/implementations/2026-07-03-ssh-container-setup-design.md).
Review pass-1 complete (aggregate:
[`docs/reviews/2026-07-03-ssh-container-setup-review-pass1.md`](../reviews/2026-07-03-ssh-container-setup-review-pass1.md))
— **Approved (ready for implementation plan)**.

Implementation plan:
[`docs/plans/2026-07-03-ssh-container-setup-impl.md`](../plans/2026-07-03-ssh-container-setup-impl.md).
Implementation not started.
