# Bitwarden auto-auth at container startup (podman secret)

**Date:** 2026-06-30
**Status:** open
**Related:** [design](../specifications/implementation/2026-06-30-bitwarden-auto-auth-design.md), [plan](../plans/2026-06-30-bitwarden-auto-auth-impl.md) (pending)

## Context

- `bitwarden-cli` (`bw`) is installed at Layer 1 (pacman). spec 13 §5 defines
  the intended auth flow: `BW_CLIENTID` / `BW_CLIENTSECRET` → `bw login
  --apikey` → `bw unlock --raw` → `BW_SESSION`, consumed by chezmoi
  `bitwarden*` template functions at runtime.
- Today this flow is **fully manual**: the operator must `export BW_SESSION`
  in the shell before `make up`, and `make up` only forwards
  `-e BW_SESSION=$BW_SESSION` into the container. There is no `make apply`
  / `make auth` target.
- The build-time `chezmoi apply` (Stage 2 `build-prepass`,
  `build_mode = true`) does **not** need `bw`: every Bitwarden-bound
  template is guarded by `{{ if not .build_mode }}` (spec 13 I-S4 / I-S6),
  so the build never consults `bw` and the image stays secret-free
  (spec 20 I4). This work therefore touches the **runtime entrypoint
  only**; Stage 2 is untouched.
- Podman 5.8.3 supports `podman secret create/exists/ls/rm` and
  `podman run --secret` (verified on the host). `bw unlock` supports
  `--passwordfile <path>` and `--raw`; `bw login --apikey` reads
  `BW_CLIENTID` / `BW_CLIENTSECRET` from the env (verified).

## Problem

Automate Bitwarden authentication at container startup so that:

1. the operator no longer manually runs `bw login --apikey` /
   `bw unlock` / `export BW_SESSION` before each `make up`;
2. the master password is **never** placed in an environment variable
   (env vars leak via `podman inspect` / `ps`); and
3. the image remains secret-free (spec 20 I4) — credentials live only
   in the running container's tmpfs `/run/secrets`, never in image
   layers.

A secondary need (raised during design): establish the **dotfiles
phase-placement convention** so future Bitwarden-bound dotfiles render
only at runtime, keeping the build secret-free by construction.

## Acceptance criteria

1. A `make up` with the three podman secrets mounted authenticates `bw`
   (login if needed → unlock) and runs `chezmoi apply` with `BW_SESSION`
   available — no manual `export` required.
2. The master password is read from `/run/secrets/bw_password` via
   `bw unlock --passwordfile` and **never** appears in any environment
   variable (verifiable: not in `podman inspect`, not in `/proc/*/environ`).
3. `BW_CLIENTID` / `BW_CLIENTSECRET` are read from `/run/secrets/*` and
   `export`-ed only inside the entrypoint process (not in image `Env`,
   not in `podman run -e` flags → absent from `podman inspect`).
4. The image is secret-free: no credential is written to any image layer
   (spec 20 I4 holds); `/run/secrets/*` are tmpfs, not layer-bound.
5. `make up` **without** the secrets still starts the container and runs
   `chezmoi apply` (skipping `bw` auth) — preserves the current
   "works without Bitwarden when no BW-bound template exists" behavior.
6. `bw login` is idempotent across restarts (login-state is ephemeral in
   the container's home; `bw login --check` gates re-login).
7. spec 13 §5 is rewritten: auth flow moves from "manual" to "entrypoint
   automatic via podman secret"; a new "phase-placement convention"
   section documents that `bitwarden*` calls MUST be wrapped in
   `{{ if not .build_mode }}`; I-S2 / I-S3 transport is updated from env
   to `/run/secrets`.
8. spec 20 I4, spec 22, spec 11, spec 21 are updated consistently.
9. The Stage 2 build-prepass is **not modified** and the build remains
   secret-free (a future unguarded `bitwarden*` call fails the build
   loudly rather than leaking).

## Notes

- Three podman secrets: `bw_clientid`, `bw_clientsecret`, `bw_password`,
  created once via `podman secret create` (podman store persists them
  across restarts, unlike per-shell `export`).
- A `make bw-secrets` setup helper is **out of scope** (YAGNI); the
  three `podman secret create` commands are documented in spec 11/13.
  A helper target/script is an explicit follow-up.
- `BW_SESSION` lives only in the entrypoint process for the duration of
  `chezmoi apply` (chosen "Shape A": entrypoint on `make up`); it is
  not propagated to later `podman exec` interactive shells. Interactive
  re-unlock, if ever needed, is `bw unlock --passwordfile
  /run/secrets/bw_password --raw` (the secret stays mounted for the
  container's lifetime).
- This design is **security-touching** → requires letter A + B + D review
  (09-review §2.2).