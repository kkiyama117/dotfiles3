# Seed the container `dotfiles_gnupg` volume with the host's existing GPG key (manual export→import)

**Date:** 2026-07-02
**Status:** closed (see [result-log](2026-07-02-phase-gnupg-host-key-import.md))
**Related:** [plumbing issue (closed)](2026-07-01-gnupg-container-setup.md), [plumbing result-log](2026-07-01-phase-gnupg-container-setup.md), [deferred Bitwarden/alternative key-management + gpgsign issue (open)](2026-07-01-gnupg-bitwarden-import.md), [spec 20](../specifications/20-container-rules.md), [spec 13](../specifications/13-secret-management.md)

## Context

- The plumbing issue
  ([`2026-07-01-gnupg-container-setup.md`](2026-07-01-gnupg-container-setup.md))
  delivered a working, persisted, **empty** `gnupg` setup in the
  container: `gnupg` + `pinentry` installed (Layer 1),
  `~/.local/share/gnupg` baked `0700` owner-correct (Layer 1-6), the
  `dotfiles_gnupg` Podman named volume mounted there, `GNUPGHOME` set by
  `dot_zshenv.tmpl`, and `.local/share/gnupg` excluded from chezmoi.
  The operator was expected to `gpg --generate-key` or `gpg --import` by
  hand to fill it.
- The operator already has a real GPG key on the host
  (`~/.local/share/gnupg`, same `GNUPGHOME` path because the host also
  sources `dot_zshenv.tmpl`): primary `ed25519/D131EE0BBB05F21E` [SC]
  (`Kouhei Kiyama (Univ)` / `kkiyama117 (boiled)`) with subkeys
  `cv25519/041375FB28B3D9F0` [E], `ed25519/A1E4E20240EA5BAA` [S]
  (expires 2031-02-18), `ed25519/B5A785FC394EE442` [A].
- The container's `dotfiles_gnupg` named volume is a **separate** store
  from the host `~/.local/share/gnupg` (named volume, not a bind mount —
  by design; see spec 20 I-GPG1 and the plumbing issue's "without (b)
  coupling to the host's `~/.local/share/gnupg`" decision). So the host
  key is not visible inside the container until it is explicitly copied
  in.
- The Bitwarden auto-import automation
  ([`2026-07-01-gnupg-bitwarden-import.md`](2026-07-01-gnupg-bitwarden-import.md))
  is still **deferred**, so the operator must seed the volume by hand for
  now (Approach B: host export → `podman cp` → container import).

## Problem

Get the operator's existing host GPG key into the container's
`dotfiles_gnupg` named volume so the container boots into a usable
keyring, **without** (a) baking any key material into an image layer
(spec 20 I4 / spec 13 I-S4), (b) bind-mounting the host's live
`~/.local/share/gnupg` (which the design deliberately rejected — it
breaks on `gpg-agent` socket conflicts, host-specific
`pinentry-auto.sh` / `gpg-agent.conf`, and lock files), or (c) leaving
the secret key exported on disk after the transfer.

## Acceptance criteria

1. The container's `$GNUPGHOME` (`~/.local/share/gnupg`) holds the
   operator's key after a manual export→`podman cp`→import sequence,
   with `gpg --list-secret-keys` showing the primary
   `D131EE0BBB05F21E` and its subkeys.
2. The public keyring (`pubring.kbx`) inside the container lists the
   operator's public key + subkeys (derived from the secret-key import;
   no separate public-key file required).
3. The key persists across `make down && make up` (the `dotfiles_gnupg`
   named volume retains it).
4. No key material is baked into any image layer (the key lives only in
   the runtime named volume; spec 20 I4 / spec 13 I-S4 hold — unchanged
   from the plumbing issue).
5. All temporary export artifacts (`/tmp/pub.asc`, `/tmp/sec.asc`,
   `/tmp/otrust.txt`) are removed from **both** the host and the
   container after the transfer (no leftover secret material on disk).
6. No change to any image layer, `Makefile`, `Containerfile`,
   `packages.toml`, or chezmoi source — this is a pure runtime/volume
   operation (the plumbing issue already delivered all build-time
   wiring).

## Notes

- **Primary key is a stub in the container (`sec#`).** The exported
  secret-key file turned out to carry the primary as a GNU-dummy stub
  and only the subkeys as real secret material (effectively an
  `--export-secret-subkeys`-shaped export: primary secret-key packet
  `plen=59` = stub; subkey packets real). So the container has real
  `[E]` / `[S]` / `[A]` subkeys but **no real primary secret**. This is
  the recommended security posture (primary kept offline; daily
  signing/encryption/authentication done with subkeys) and is fully
  functional for git-commit signing, encryption, and SSH-via-gpg auth.
  The operator cannot, from the container, perform primary-only
  operations (add/revolve UIDs, revoke, re-certify) — those stay on the
  host.
- **Importing the real primary key is deferred.** Per operator decision
  2026-07-02, the real primary-key import will be done as part of the
  Bitwarden **or alternative** key-management + gpgsign setup tracked
  in
  [`2026-07-01-gnupg-bitwarden-import.md`](2026-07-01-gnupg-bitwarden-import.md)
  (whose open sub-question (b) already asks "only a public-key ring +
  signing subkey vs. a full secret key"). git-commit signing config
  (`user.signingkey` = the `[S]` subkey `A1E4E20240EA5BAA`, plus
  `commit.gpgsign`) is likewise deferred to that setup (it belongs in
  the chezmoi-managed `dot_config/git` per the `git_config` work, not
  baked into this runtime-only task).
- **Host `pubring.kbx` anomaly (out of scope).** The host's
  `~/.local/share/gnupg/pubring.kbx` does not contain the operator's
  own public-key record (so `gpg --export <fingerprint>` on the host
  falls back to deriving the public key from the secret key and prompts
  via pinentry). This is a host-side keyring-consistency cleanup,
  unrelated to the container; it can be fixed optionally with
  `gpg --armor --export D131EE0BBB05F21E | gpg --import` on the host.
  Not required for this task.

## Status update (2026-07-02)

Complete. The manual export→`podman cp`→import was performed and
verified; the key persists in the `dotfiles_gnupg` named volume across
`make down && make up`, and all temporary export artifacts were removed
from both host and container. The primary-key stub caveat (above) is
recorded as a deferred follow-up under the Bitwarden/alternative
key-management issue. See the
[result-log](2026-07-02-phase-gnupg-host-key-import.md) for evidence.