# Bake `makepkg.conf` into the container — Implementation Plan

**Status:** done
**Date:** 2026-07-09
**Issue:** [`../issues/2026-07-09-makepkg-conf-container.md`](../issues/2026-07-09-makepkg-conf-container.md)
**Design:** [`../specifications/implementations/2026-07-09-makepkg-conf-container-design.md`](../specifications/implementations/2026-07-09-makepkg-conf-container-design.md)

## File structure

| Path | Action |
|---|---|
| `container/bind/layer_1_files/makepkg.conf` | create |
| `container/.gitignore` | modify |
| `container/Containerfile` | modify (Layer 1-2 COPY) |
| `docs/specifications/01-file-structures.md` | modify |
| `docs/specifications/20-container-rules.md` | modify (`I-MAKEPKG1`) |
| `docs/specifications/21-container-build-flow.md` | modify |
| `docs/specifications/03-makefile.md` | modify |
| `docs/references/host_config_list.md` | modify |
| `container/tests/container/test_entrypoint.py` | modify |

## Phase 1 — Plumbing

- [x] Copy host `~/.config/pacman/makepkg.conf` to bind dir
- [x] Allowlist in `container/.gitignore`
- [x] Add `COPY bind/layer_1_files/makepkg.conf /etc/makepkg.conf` in Layer 1-2

**Acceptance:** `git check-ignore -v container/bind/layer_1_files/makepkg.conf`
returns nothing; Containerfile has one COPY before mirrorlist.

## Phase 2 — Spec sync

- [x] Update specs 01, 03, 20, 21, host_config_list.

## Phase 3 — Test

- [x] Add `test_makepkg_conf_baked_into_layer_1_2` to `test_entrypoint.py`.

## Phase 4 — Build + smoke

- [x] `make build`, `make up`, verify `PKGEXT` and `paru --version`.

## Phase 5 — Review

- [x] A + C + E per spec 09 (Containerfile change). Aggregate:
  [`docs/reviews/2026-07-09-makepkg-conf-container-review-pass1.md`](../reviews/2026-07-09-makepkg-conf-container-review-pass1.md).
  C-F1 (`.d` bypass premise) resolved in design §4 + `I-MAKEPKG1`.
