# Import SSH private keys into the container from Bitwarden at startup

**Date:** 2026-07-03
**Status:** open (deferred)
**Related:** [parent plumbing issue](2026-07-03-ssh-container-setup.md), [SSH config (deferred)](2026-07-03-ssh-container-config-setup.md), [spec 13](../specifications/13-secret-management.md), [spec 20](../specifications/20-container-rules.md), [GPG Bitwarden import (deferred sibling)](2026-07-01-gnupg-bitwarden-import.md), [git config setup (closed)](2026-07-01-git-config-setup.md)

## Context

- The parent issue
  ([`2026-07-03-ssh-container-setup.md`](2026-07-03-ssh-container-setup.md))
  delivers `openssh` + a persisted but **empty** `~/.ssh` named volume
  (`dotfiles_ssh`). The operator seeds keys manually (`podman cp`) until this
  issue automates import.
- The project's secret source is Bitwarden (`bw`), consumed by chezmoi's
  `bitwardenAttachment` template functions at runtime (spec 13). The entrypoint
  already unlocks `bw` before `chezmoi apply` (spec 13 §4 / spec 20 I4).
- SSH private keys are secret material and must never be baked into image layers
  (spec 13 I-S3 / I-S4). Import happens at **runtime** only.
- `host_config_list.md` §15 lists `run_after_install-ssh-keys.sh.tmpl` as the
  intended mechanism (mirrors the deferred `gpg-signing` / GPG import pattern).

## Problem

Automate seeding `dotfiles_ssh` from Bitwarden attachments at container startup
so a fresh `make up` has the operator's ed25519 (or other) client keys without
manual `podman cp`, while keeping the image secret-free.

## Acceptance criteria (deferred — refine at pickup)

1. `.chezmoiscripts/run_after_install-ssh-keys.sh.tmpl` exists, gated with
   `{{ if not .build_mode }}` and container runtime checks (spec 13 §5a).
2. Script is idempotent: skips keys that already exist in `~/.ssh` with correct
   permissions (`0600` private / `0644` public).
3. Keys are sourced via `bitwardenAttachment` (or documented alternative);
   nothing is written to image layers or chezmoi source plaintext.
4. After `make up` on a fresh volume (with vault item configured), `ssh-add -l`
   lists the imported key(s).
5. Spec 13 / 20 cross-refs updated; parent issue result-log links here.

## Notes

- Pick up after [`2026-07-03-ssh-container-setup.md`](2026-07-03-ssh-container-setup.md)
  closes (volume plumbing must exist first).
- GPG-over-SSH does **not** replace this issue: file keys remain needed for VPS /
  non-Git Hosts even after the config issue adds Tier 1 GPG auth.
