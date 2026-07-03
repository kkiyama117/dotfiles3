# Set up SSH config in the container (chezmoi-managed fragments + optional GPG auth)

**Date:** 2026-07-03
**Status:** open (deferred — future work)
**Related:** [immediate sibling (file keys only)](2026-07-03-ssh-container-setup.md), [GPG container management](../specifications/23-container-gnupg-management.md), [git config setup (closed)](2026-07-01-git-config-setup.md), [host config inventory §13](../references/host_config_list.md), [spec 20](../specifications/20-container-rules.md)

## Status update (2026-07-03)

Deferred in favor of
[`2026-07-03-ssh-container-setup.md`](2026-07-03-ssh-container-setup.md),
which delivers **file-based SSH keys** (named volume + manual import) without
GPG-agent SSH wiring or chezmoi-managed `~/.ssh/config`. Pick this issue up
after the sibling is closed and the operator wants chezmoi-managed Host blocks
and/or GPG `[A]` subkey auth for Git hosts.

## Context

- `openssh` is already declared in `dependencies/packages.toml` (`manager =
  "pacman"`, `layer = 1`, `has_configs = true`) but no SSH config files are
  managed by chezmoi yet.
- The container has **no** `~/.ssh` named volume today (unlike `dotfiles_gnupg`
  for GPG). The sibling issue adds `dotfiles_ssh`.
- GPG `[A]` authentication subkeys are already imported into `dotfiles_gnupg`
  (see [`2026-07-02-phase-gnupg-host-key-import.md`](2026-07-02-phase-gnupg-host-key-import.md)),
  so **GPG-over-SSH** (`gpg-agent` + `enable-ssh-support`) is feasible as an
  optional auth tier once config plumbing exists.
- `docs/references/host_config_list.md` §13 lists only
  `~/.ssh/authorized_keys` (inbound); the operator's `~/.ssh/config` is **not**
  yet inventoried in this repo.
- `host_config_list.md` §15/§18 mention aspirational
  `.chezmoiscripts/run_after_install-ssh-keys.sh.tmpl` — file-key materialization
  is tracked on the sibling / a future Bitwarden issue, not here.

## Problem

Bring `~/.ssh/config` under chezmoi management for host **and** container,
letting the operator choose **which Host blocks to manage** without a YAML
manifest (YAGNI — architect review 2026-07-03), while supporting:

1. **Tier 1 — GPG auth** for Git hosts (`IdentityAgent` → gpg-agent SSH socket).
2. **Tier 2 — file keys** for VPS / generic SSH (`IdentityFile` → volume-owned
   keys from the sibling issue).
3. **Local-only Host blocks** via an Include directory on the volume (never
   chezmoi-managed).

## Design decisions (frozen for this issue)

### Config layout — Include + fragment files (no YAML manifest)

```
~/.ssh/config                          # chezmoi: private_dot_ssh/config.tmpl
  Include ~/.ssh/config.d/chezmoi/*.conf
  Include ~/.ssh/config.d/local/*      # volume-only; optional

~/.ssh/config.d/chezmoi/               # chezmoi-managed fragments
  github.com.conf.tmpl                 # commit = managed; delete = unmanaged
  my-vps.conf                          # file-key Host (Tier 2)

~/.ssh/config.d/local/                 # volume-only hand edits
~/.ssh/id_*                            # volume-only secrets (chezmoiignore)
```

- **What is managed** = which fragment files are committed to git (same model as
  any other dotfile). No `.chezmoidata/ssh_hosts.yaml`, no inventory YAML loop.
- **Host/container divergence** = `{{ if eq .runtime "container" }}` inside a
  fragment (same pattern as `dot_config/git/config.tmpl`).
- **Catalog** = extend `host_config_list.md` when porting Host blocks; no
  separate machine-readable inventory in Phase A.

### Auth tiers (when this issue is implemented)

| Tier | Mechanism | Depends on |
|------|-----------|------------|
| GPG (Git) | `gpg-agent.conf` `enable-ssh-support`; `SSH_AUTH_SOCK` / `IdentityAgent` | `dotfiles_gnupg` (delivered) |
| File key | `IdentityFile ~/.ssh/<name>` | `dotfiles_ssh` (sibling) |

### Explicitly out of scope here

- Named-volume plumbing for `~/.ssh` → sibling issue.
- Bitwarden key import (`run_after_install-ssh-keys.sh.tmpl`) → separate deferred
  issue (mirror [`gnupg-bitwarden-import`](2026-07-01-gnupg-bitwarden-import.md)).
- Host `~/.ssh` bind mount (agent socket / lock contention — same rationale as
  spec 23 §3 for GPG).
- `authorized_keys` (inbound SSH into the container is not required).
- ProxyCommand / Match blocks with embedded secrets — port only after redaction
  review.

## Acceptance criteria (deferred — refine at pickup)

1. `private_dot_ssh/config.tmpl` exists with `Include` lines for
   `config.d/chezmoi/` and `config.d/local/`.
2. At least one **Tier 1 (GPG)** fragment (e.g. `github.com.conf.tmpl`) is
   committed; after `chezmoi apply`, `ssh -T git@github.com` succeeds using
   the GPG `[A]` subkey (no file private key required for that Host).
3. Fragment files the operator **does not** commit remain absent from the
   container config (Include only pulls committed fragments).
4. `dot_local/share/gnupg/gpg-agent.conf.tmpl` adds `enable-ssh-support`
   (chezmoi-managed agent config; keyring stays volume-owned per spec 23).
5. `dot_zshenv.tmpl` exports `SSH_AUTH_SOCK` to the gpg-agent SSH socket when
   GPG tier is enabled (or documents `IdentityAgent`-only approach if
   preferred at design time).
6. `.chezmoiignore` excludes secret key material under `.ssh/` (`id_*`, `*_ed25519`,
   etc.) but **does not** ignore the whole `.ssh` tree (config is chezmoi-managed).
7. New normative spec **25 — Container SSH management** §4+ documents config layout,
   auth tiers, rollout safety (`make clean` wipes `dotfiles_ssh` **and**
   `dotfiles_gnupg`), and cross-refs spec 23 for GPG auth. (Plumbing baseline
   spec 25 §1–3 is delivered by the sibling plumbing issue.)
8. Specs 20 / 21 / 02 updated (I-SSH* invariants, Layer rows, `openssh`
   `has_configs` realized).

## Implementation phases (sketch)

| Phase | Content |
|-------|---------|
| 0 | Port selected Host blocks from host `~/.ssh/config` into fragments (operator chooses commits) |
| 1 | issue pickup → design + review (security: A + B + D) |
| 2 | config.tmpl + fragments + gpg-agent SSH wiring |
| 3 | spec 25 + spec 20/21 updates |
| 4 | build / smoke / persistence / result-log |

## Notes

- Architect review (2026-07-03): a YAML manifest (`ssh_hosts.yaml`) duplicates
  git's commit model and was rejected as YAGNI; fragment Include is the minimal
  "choose what to manage" mechanism.
- Rollout: `make clean` removes **all** named volumes including `dotfiles_gnupg`;
  document targeted `podman volume rm` (cargo/GPG precedent in spec 21).
