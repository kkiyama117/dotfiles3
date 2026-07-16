# Use SSH first for managed external repositories

**Date:** 2026-07-16
**Status:** in-progress
**Related:** [design](../specifications/implementations/2026-07-16-ssh-first-external-fallback-design.md), [plan](../plans/2026-07-16-ssh-first-external-fallback-impl.md), [reviews](../reviews/2026-07-16-ssh-first-external-fallback-review-pass1.md), [pre-required environment values](../specifications/11-pre-required-env-values.md)

## Context

The chezmoi config defaults `PI_CONFIG_URL` and `NVIM_CONFIG_URL` to GitHub SSH
URLs. The container entrypoint currently overrides both values with public
HTTPS URLs unconditionally before the runtime config is rendered.

## Problem

Container startup never attempts the configured SSH URLs, even when the
persistent SSH volume already contains working GitHub configuration and keys.
HTTPS is intended only as a bootstrap fallback when SSH access does not work.

## Acceptance criteria

1. `pi-config` and `nvim_config` each use their SSH URL when an independent,
   non-interactive access probe succeeds.
2. A repository uses its public HTTPS URL only when its SSH probe fails.
3. Explicit `PI_CONFIG_URL` and `NVIM_CONFIG_URL` overrides are preserved.
4. Tests cover SSH success, SSH failure, independent selection, and explicit
   override behavior without contacting GitHub.
5. The environment-value specification describes SSH-first fallback behavior.
6. Existing managed checkouts use the selected transport on their `origin`.
7. Probe execution and signal forwarding are bounded and regression-tested.
8. URL/ref overrides are forwarded by `make up` and safely quoted in TOML.

## Notes

The probe must be non-interactive and timeout-bounded so startup cannot hang on
an SSH prompt or unreachable network.
