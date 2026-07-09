# Bake `makepkg.conf` into the container image (Layer 1-2 COPY)

**Date:** 2026-07-09
**Status:** closed
**Related:** [design](../specifications/implementations/2026-07-09-makepkg-conf-container-design.md), [plan](../plans/2026-07-09-makepkg-conf-container-impl.md), [result log](2026-07-09-phase-makepkg-conf-container.md), [review pass-1](../reviews/2026-07-09-makepkg-conf-container-review-pass1.md), [spec 20](../specifications/20-container-rules.md), [spec 21](../specifications/21-container-build-flow.md), [host config inventory §8](../references/host_config_list.md)

## Context

- The container uses the Manjaro base image's `/etc/makepkg.conf` (default
  `PKGEXT='.pkg.tar.zst'`). The host previously used
  `~/.config/pacman/makepkg.conf` with `PKGEXT='.pkg.tar.xz'` and custom
  build/compression flags, but that file was **not** migrated to chezmoi.
- `makepkg` runs in Containerfile Layer 4-1 (`makepkg -si` to bootstrap
  `paru`) and at runtime via `paru`. Both read `/etc/makepkg.conf`.
- The established pattern for image-owned pacman config is
  `container/bind/layer_1_files/pacman_mirrorlist` → `COPY` in Layer 1-2.

## Problem

Bake a curated `/etc/makepkg.conf` into the image at build time (xz package
compression + host build flags) so AUR builds match the user's prior host
setup, without chezmoi-managed user config or runtime bind mounts.

## Acceptance criteria

1. `container/bind/layer_1_files/makepkg.conf` exists (byte copy of host
   `~/.config/pacman/makepkg.conf`) and is tracked via `container/.gitignore`
   allowlist.
2. Containerfile Layer 1-2 contains
   `COPY bind/layer_1_files/makepkg.conf /etc/makepkg.conf` before
   `pacman -Syu`.
3. Specs 01, 03, 20 (`I-MAKEPKG1`), and 21 (Layer 1-2 inputs + acceptance
   #24) are updated.
4. After `make build` + `make up`, in-container
   `grep PKGEXT /etc/makepkg.conf` shows `PKGEXT='.pkg.tar.xz'`; `paru
   --version` still works (no regression).
