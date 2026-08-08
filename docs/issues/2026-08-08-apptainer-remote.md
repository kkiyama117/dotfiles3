# Apptainer remote support (HPC login node)

**Date:** 2026-08-08
**Status:** open
**GitHub issue:** https://github.com/kkiyama117/dotfiles3/issues/13
**Related:** [design](../specifications/implementations/2026-08-08-apptainer-remote-design.md)

## Context

The dotfiles container is built and run with Podman (spec 20/21). A remote
environment — the login node of an HPC cluster, accessed via `ssh sp` — has
only Apptainer (formerly Singularity) available. Apptainer can run OCI
images (docker/podman images) directly, so the existing image can be reused
without rewriting the Containerfile.

## Problem

The runtime contract (spec 20) depends on Podman-specific features:
`--userns=keep-id`, `--secret` (Bitwarden), named volumes, `--init`. None of
these exist in Apptainer. There is also no CI pipeline today: the image is
built locally with `make build` (podman), so the remote has no way to obtain
the image.

## Decisions (from brainstorming, 2026-08-08)

- Build the OCI image in GitHub Actions (BuildKit) and push to GHCR as a
  public package; the remote pulls with `apptainer pull docker://...`.
- Runtime model: ephemeral `apptainer run` per shell (entrypoint runs
  `chezmoi apply` + Bitwarden auth, then `exec zsh -l`).
- Use the remote home directly as `$HOME` (Apptainer default); named
  volumes are replaced by binds of the remote home's XDG directories.
- Bitwarden is used on the remote: secret files are bound to `/run/secrets`.
- All three managed repositories (dotfiles3, pi-config, nvim_config) are
  public, so the first clone/apply needs no credentials.

## Job state memo (2026-08-08)

**Status:** paused — implementation deferred by the user; resume later.

**Where we are:**

- Brainstorming complete; design approved in conversation (2026-08-08).
- Design doc: `docs/specifications/implementations/2026-08-08-apptainer-remote-design.md` — still **DRAFT** (plan Task 4 reviews it and marks Approved).
- Implementation plan: `docs/plans/2026-08-08-apptainer-remote-impl.md` — committed, **not executed**.
- GitHub issue #13 open.

**Key decisions (do not re-brainsstorm):**

- Build the OCI image in GitHub Actions (BuildKit) → public GHCR package; the remote pulls with `apptainer pull docker://...`.
- Runtime: ephemeral `apptainer run` per shell; the existing entrypoint is unchanged (chezmoi apply + Bitwarden auth → `exec zsh -l`).
- Remote home used directly as `$HOME`; the five named volumes → binds of remote-home XDG dirs.
- Bitwarden used on the remote: files in `~/.config/dotfiles-secrets/` bound to `/run/secrets` (required — apply fails without them).
- CI build args fixed: `HOST_UID=1000`, `HOST_GID=1000`, `USERNAME=kiyama`.
- `XDG_RUNTIME_DIR` overridden to `$HOME/.run`; kakehashi copied out of the image once.
- All three repos (dotfiles3, pi-config, nvim_config) are public → no auth needed for the first clone/apply.

**Remaining work (per plan):**

1. Task 1: `.github/workflows/build-image.yml`
2. Task 2: `scripts/apptainer-run.sh` (+ shellcheck, dry-run tests)
3. Task 3: `docs/specifications/26-apptainer-remote.md`
4. Task 4: letter-A review (spec 09) → design Approved
5. Task 5: push → CI build → GHCR public → remote verify via `ssh sp` → result-log → close #13

**Pending decision:** execution mode — subagent-driven vs inline (user chooses on resume).

**Operator actions needed (Task 5):**

- Set GHCR package visibility to public (after the first push).
- On the remote: place `bw_clientid` / `bw_clientsecret` / `bw_password` in `~/.config/dotfiles-secrets/` (chmod 600).
- Remote access: `ssh sp`.

## Acceptance criteria

1. GitHub Actions builds the existing Containerfile unchanged (named build
   contexts `deps` / `srcroot`, BuildKit cache mounts) and pushes
   `ghcr.io/kkiyama117/dotfiles-manjaro:latest` (+ `:<sha>`) as a public
   package.
2. A wrapper script in the repo (`scripts/apptainer-run.sh`) starts an
   interactive zsh on the remote: pull-if-missing, clone-if-missing,
   secrets check, binds, `apptainer run ... zsh -l`.
3. The entrypoint runs unchanged: `chezmoi apply` with Bitwarden auth from
   `/run/secrets`, then `exec zsh -l`.
4. The remote home receives the dotfiles (choice A: remote home as
   `$HOME`); XDG dirs (`cargo`, `rustup`, `mise`, `gnupg`, `.ssh`) persist
   in the remote home.
5. Local Makefile / Containerfile / entrypoint are unchanged.
6. A new spec (`26-apptainer-remote.md`) documents the remote contract.
