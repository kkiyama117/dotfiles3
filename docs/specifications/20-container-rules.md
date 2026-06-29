# 20 — Container rules

> Spec status: **DRAFT (stub)**. Normative spec for the container's runtime
> contract. Build-flow specifics are split into
> [`21-container-build-flow.md`](21-container-build-flow.md); build-time envs
> live in [`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md).

## Invariants

- I1: **Rootless Podman only.** The container is never built or run as root on the host.
- I2: **`--userns=keep-id` is required** for any run that bind-mounts host files. The host UID/GID survive the user namespace remap so chezmoi-source ownership is preserved.
- I3: **No `:U` volume flag.** It recursively `chown`s the host directory, which is destructive.
- I4: **Secrets via BuildKit `--mount=type=secret` and Podman secrets only.** Never `ARG`, never `ENV`, never committed.
- I5: **All packages must originate from `dependencies/packages.toml`.** Ad-hoc `pacman -S` / `paru -S` calls in the Containerfile are forbidden once `gen-deps` is wired.

> NOTE on `git safe.directory`: an earlier draft mandated registering
> `/var/lib/chezmoi-source` via `git config --global --add safe.directory`.
> That invariant was dropped because I2 (`--userns=keep-id`) already keeps
> the host UID inside the container, so the "dubious ownership" condition
> never triggers in the supported run mode. The
> [`../references/2026-06-25-chezmoi-in-containers.md`](../references/2026-06-25-chezmoi-in-containers.md)
> reference doc is kept for context only.

## Delegated rules

| Topic | File |
|---|---|
| Containerfile stage breakdown, layer ordering, build invariants | [`21-container-build-flow.md`](21-container-build-flow.md) |
| Build-time env vars (`HOST_UID`, `HOST_GID`, `JOBS`, `BW_ID`) | [`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md) |
| Host pre-requirements (Bitwarden, rbw, chezmoi) | [`11-pre-required-env-values.md`](11-pre-required-env-values.md) |
| Make target contract | [`03-makefile.md`](03-makefile.md) |
| Chezmoi-in-container gotchas (safe.directory, UID remap) | [`../references/2026-06-25-chezmoi-in-containers.md`](../references/2026-06-25-chezmoi-in-containers.md) |
| Podman conventions used in this repo | [`../references/podman_defact_standard.md`](../references/podman_defact_standard.md) |

## Open questions

- Q1: Is the container intended to be **disposable** (apply at every `up`) or **persistent** (apply once, bind home from host)? Closing this determines whether `chezmoi apply` lives in the build stage or the entrypoint.
- Q2: What is the policy for `paru` / AUR builds inside a non-root user namespace?
