# Align pi-config management to nvim_config direct-clone style

**Date:** 2026-07-14
**Status:** closed (Phases 1-5 done; commit at develop HEAD; awaiting push authorization)
**Related:** [pi-provider-config-managed](./2026-07-14-pi-provider-config-managed.md), [design](../specifications/implementations/2026-07-14-pi-config-direct-clone-design.md), [spec 11](../specifications/11-pre-required-env-values.md)

## Motivation

`/data/pi-config` is currently managed via clone-to-intermediate (`~/.local/share/pi-config`) + symlink (`run_after_configure-pi-agent.sh.tmpl`), while `/data/nvim_config` uses the simpler direct-clone approach (clone into `~/.config/nvim`, no symlink script). The pi-config repo structure already maps 1:1 to `~/.pi/` (top-level `agent/` and `providers/`), so the intermediate layer is unnecessary complexity.

## Scope

- Remove the `run_after_configure-pi-agent.sh.tmpl` symlink script
- Change `.chezmoiexternal.toml.tmpl` to clone pi-config directly into `~/.pi` (container-only, gated by `runtime`)
- Update `.chezmoiignore` to allow the external only for container runtime
- Extend `/data/pi-config/.gitignore` to cover all `~/.pi` runtime state
- Bump pi-config tag to `pi-config-v2026-07-14-2`
- In-place migration of the running container's `~/.pi`
- Update Dockerfile for fresh container builds

## Key risks (from oracle review)

- **R1**: Host `~/.pi` is a `PI_harness.git` checkout — external must be container-gated
- **R2**: `.chezmoiignore` `.pi` entry silently skips the external — must be runtime-conditional
- **R3**: Existing non-empty `~/.pi` won't be overwritten by chezmoi clone — needs explicit migration

## Acceptance criteria

1. `run_after_configure-pi-agent.sh.tmpl` deleted
2. `.chezmoiexternal.toml.tmpl` clones pi-config into `~/.pi` (container runtime only)
3. `.chezmoiignore` allows `.pi` external for container runtime only
4. `/data/pi-config/.gitignore` covers `run-history.jsonl`, `intercom/`, `.pi-subagents/`, `*.pre-pi-config.*`
5. pi-config tagged `pi-config-v2026-07-14-2` and pushed
6. `pi_config_ref` default bumped to `pi-config-v2026-07-14-2` in `.chezmoi.toml.tmpl` and spec 11
7. All tests pass (updated for new paths, removed symlink test)
8. `programs/chezmoi_pi_commit.sh` fallback path removed
9. Container in-place migration succeeds (pi works after migration)
10. Dockerfile updated for fresh builds
11. PI_harness `.gitignore` comment updated
