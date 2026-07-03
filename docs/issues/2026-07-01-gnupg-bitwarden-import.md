# Import GPG keys into the container from Bitwarden at startup

**Date:** 2026-07-01
**Status:** open (deferred)
**Related:** [parent issue](2026-07-01-gnupg-container-setup.md), [design (parent)](../specifications/implementations/2026-07-01-gnupg-container-setup-design.md), [spec 13](../specifications/13-secret-management.md), [spec 20](../specifications/20-container-rules.md), [manual host-key import (closed)](2026-07-02-gnupg-host-key-import.md)

## Status update (2026-07-02)

The `dotfiles_gnupg` volume was seeded **manually** (host export →
`podman cp` → container import) on 2026-07-02 — see
[`2026-07-02-gnupg-host-key-import.md`](2026-07-02-gnupg-host-key-import.md)
(+ [result-log](2026-07-02-phase-gnupg-host-key-import.md)). The
container now holds the operator's real `[E]` / `[S]` / `[A]` subkeys
but the **primary as a stub** (`sec#`), because the export carried the
primary as a GNU-dummy stub. Per operator decision 2026-07-02, this
issue's scope is widened to also cover:

- **importing the real primary key** (resolving open sub-question (b)
  in favor of a full secret key, or deliberately keeping the
  primary-offline posture and documenting it as such); and
- **gpgsign configuration** — setting `user.signingkey` (the `[S]`
  subkey `A1E4E20240EA5BAA`) and `commit.gpgsign` via the chezmoi-
  managed `dot_config/git` (per the `git_config` work), alongside the
  key-import automation.

The title's "from Bitwarden" should be read as "from Bitwarden **or an
alternative** secret store" — the operator left the transport open; the
chosen transport will be settled in this issue's design. This issue
remains `open (deferred)`.

## Context

- The parent issue
  ([`2026-07-01-gnupg-container-setup.md`](2026-07-01-gnupg-container-setup.md))
  delivers the `gnupg` plumbing: installs `gnupg` + `pinentry` (Layer 1),
  bakes `~/.local/share/gnupg` (`0700`, owner-correct) as a named-volume
  mountpoint, and mounts the `dotfiles_gnupg` Podman named volume there.
  The result is a persisted but **empty** keyring — the operator must
  `gpg --generate-key` or `gpg --import` by hand.
- The project's sole secret source is Bitwarden (`bw`), transported as
  podman secrets and consumed by chezmoi's `bitwarden` /
  `bitwardenAttachment` template functions at runtime (spec 13 §3/§4).
  The runtime entrypoint already authenticates `bw` (login → unlock →
  `BW_SESSION`), runs `chezmoi apply`, and scrubs `BW_*` before `exec`
  (spec 13 §4 / spec 20 I4).
- GnuPG private keys are secret material: an exported secret key (or its
  passphrase) is exactly the kind of vault item the Bitwarden integration
  exists to source. The image must stay secret-free (spec 13 I-S3 / I-S4),
  so any import must happen at **runtime** (entrypoint), never at build
  time.

## Problem

Automate seeding the `dotfiles_gnupg` named volume from Bitwarden so a
fresh `make up` boots into a usable keyring without a manual
`gpg --import`, while keeping the image secret-free and the master
password out of every environment variable (consistent with the existing
`bw_password` podman-secret flow).

## Acceptance criteria (deferred — to be refined when this issue is picked up)

1. A GPG secret key (and, if needed, its passphrase) is stored as a
   Bitwarden item/attachment and referenced from the chezmoi source tree
   (e.g. a `bitwardenAttachment` template call), gated by
   `{{ if not .build_mode }}` so the Stage 2 build-prepass never consults
   `bw` (spec 13 I-S6 / I-S4).
2. The runtime entrypoint, after `bw unlock` and before `chezmoi apply`
   (or as a dedicated post-apply step), imports the secret key into
   `$GNUPGHOME` **iff the named volume is empty** (idempotent; never
   overwrites an operator-generated key).
3. The import reads the key material from the vault via `bw` / chezmoi
   `bitwarden*` templates only — no key material is baked into image
   layers or `.env` (spec 20 I4 / spec 13 I-S3 hold).
4. If the key's passphrase is needed, it is sourced from Bitwarden and
   piped to `gpg --batch --pinentry-mode loopback --passphrase-fd` (or
   equivalent) inside the entrypoint process; it is never placed in an
   environment variable and is scrubbed before `exec "$@"` (mirrors the
   `BW_*` scrub in spec 13 §4 step 6).
5. `make up` **without** the `bw_*` podman secrets still starts the
   container and leaves the keyring empty (no-secret startup; the operator
   can import manually), preserving the existing no-secret behavior
   (spec 13 §4 last paragraph).
6. `make down && make up` does **not** re-import when the volume already
   holds the key (idempotency across restarts).
7. The parent issue's invariants (I-GPG1..I-GPG5) still hold; this issue
   adds no new baked image content and no secret-store daemon.

## Notes

- This issue is **deliberately deferred**. The parent issue delivers the
  named-volume plumbing (Approach A) so a manually-generated/imported key
  persists today; this issue (Approach D from the design dialogue) adds
  the Bitwarden automation on top.
- Picking this up will require a design doc (`docs/specifications/
  implementation/2026-07-01-gnupg-bitwarden-import-design.md`) following
  the spec 13 §5a phase-placement convention (`{{ if not .build_mode }}`
  guard around every `bitwarden*` call) and a review pass (security
  touch: secrets + image — at least letters A/B/D per spec 09 §2.2).
- Open sub-questions to resolve in that design: (a) whether the key
  passphrase lives as a Bitwarden item password field, a custom field, or
  a separate attachment; (b) whether to support importing **only** a
  public-key ring + signing subkey vs. a full secret key (the 2026-07-02
  manual import left the primary as a stub — `sec#` — with real
  subkeys; see the [host-key-import result-log]
  (2026-07-02-phase-gnupg-host-key-import.md); this issue decides
  whether the automated import brings the real primary or deliberately
  keeps the primary-offline posture); (c) whether `loopback` pinentry
  needs a `gpg-agent.conf` baked by chezmoi (which would flip `gnupg`
  to `has_configs = true` in spec 02); (d) **gpgsign** — whether/how to
  set `user.signingkey` (= the `[S]` subkey `A1E4E20240EA5BAA`) and
  `commit.gpgsign` in the chezmoi-managed `dot_config/git` as part of
  this setup; (e) whether the secret transport is Bitwarden or an
  alternative (operator left this open 2026-07-02).