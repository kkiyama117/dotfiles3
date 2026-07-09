# Bake `makepkg.conf` into the container image — Design

**Status:** DRAFT
**Date opened:** 2026-07-09
**Issue:** [`../../issues/2026-07-09-makepkg-conf-container.md`](../../issues/2026-07-09-makepkg-conf-container.md)
**Author:** kiyama

## §1 Context & success criteria

The container inherits `/etc/makepkg.conf` from `manjarolinux/base` with
`PKGEXT='.pkg.tar.zst'`. The host used `~/.config/pacman/makepkg.conf` with
`PKGEXT='.pkg.tar.xz'` and custom `COMPRESSZST`, `MAKEFLAGS`, and hardening
flags. That file is listed in `docs/references/host_config_list.md` §8 but
was not migrated to chezmoi.

Success criteria:

- **S1** `container/bind/layer_1_files/makepkg.conf` is a byte-stable copy
  of the host file; git-tracked via `container/.gitignore` allowlist.
- **S2** Containerfile Layer 1-2 `COPY`s it to `/etc/makepkg.conf` before
  the first `makepkg` / `paru` invocation (Layer 4-1).
- **S3** Image-owned, not chezmoi-managed; no runtime bind mount.
- **S4** Toggle compression by editing the bind file's `PKGEXT` line and
  re-running `make build` (no Containerfile change).
- **S5** Spec 20 `I-MAKEPKG1` and spec 21 acceptance #24 document behavior
  and rollout.

## §2 Decision: full-file COPY (not chezmoi, not minimal delta)

**Chosen:** Full byte copy of `~/.config/pacman/makepkg.conf` into
`container/bind/layer_1_files/makepkg.conf`, copied to `/etc/makepkg.conf`
in Layer 1-2 — parallel to `pacman_mirrorlist`.

**Rejected:**

- Chezmoi `dot_config/pacman/makepkg.conf` — user explicitly excluded user
  config migration; build-time image config is the goal.
- Runtime bind mount — rejected for reproducibility.
- Minimal ~10-line delta — YAGNI fallback only if review requires it; full
  copy preserves host `CFLAGS`/`MAKEFLAGS` without hand-rebuild drift.

## §3 Diff vs base image defaults

| Setting | Base image | Curated file |
|---|---|---|
| `PKGEXT` | `.pkg.tar.zst` | `.pkg.tar.xz` |
| `COMPRESSZST` | `zstd -c -T0 -` | `zstd -c -z -q -` |
| `MAKEFLAGS` | `-j2` | `-j$(($(nproc)+1))` |
| Hardening | `-D_FORTIFY_SOURCE=3` + clash/protection | `-D_FORTIFY_SOURCE=2` + `-fstack-protector-strong` |

## §4 `makepkg.conf.d/` bypass

The base image's `/etc/makepkg.conf` sources
`/etc/makepkg.conf.d/{fortran,rust}.conf`. The full-file COPY replaces the
entire file, so `.d/` snippets are no longer sourced. The curated file
carries the build flags the user wants; this is intentional.

## §5 Rollout

Existing deployments must run `make build` before the first `make up` after
this change. `make up`'s `_verify_image_fresh` only hashes `entrypoint.sh`,
so a build-skipper keeps the old `PKGEXT`. Documented in spec 21 #24 (parallel
to SSH rollout #23). Do **not** extend `_verify_image_fresh` in this change.

## §6 Risks

- **LOW:** paru BuildKit cache may hold prior `.pkg.tar.zst` artifacts; next
  rebuild uses new `PKGEXT`.
- **LOW:** Host edits to `~/.config/pacman/makepkg.conf` outside the repo do
  not propagate until the bind file is updated and `make build` re-runs.
