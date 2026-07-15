# herdr-mise-management — Implementation review prompt pass-2

**Date:** 2026-07-15
**Subject:** [`../specifications/implementations/2026-07-15-herdr-mise-management-design.md`](../specifications/implementations/2026-07-15-herdr-mise-management-design.md)
**Implementation evidence:** [`../issues/2026-07-15-phase-herdr-mise-management.md`](../issues/2026-07-15-phase-herdr-mise-management.md)
**Required letters:** A + C + E

Use the common output schema and severity/status vocabulary from
[`../specifications/09-review.md`](../specifications/09-review.md) §3.

## Letter A — factual / correctness

Read the working-tree implementation, policy tests, normative specs, approved
design, and result-log. Verify that the declared mise key, removed bespoke
install, update settings, generated inventory, and recorded runtime evidence
match the repository state.

## Letter C — architecture / senior engineering

Verify that `dot_config/mise/config.toml` is the sole install/version/update
authority, that removal from `packages.toml` follows the mise-manager contract,
and that no duplicate installation or stale normative contract remains.

## Letter E — operability / runtime

Verify build success, shim resolution, removal of the old path, one-time
`dotfiles_mise` migration, restart persistence, regression checks, upgrade
procedure, rollback feasibility, and carried pass-1 risks E1/E2.

## Expected output

Produce one per-letter review for A, C, and E plus an aggregate pass-2 review.
Every finding must include an ID, severity, status, and location. The pass may
terminate only when no `open`, `REGRESSION`, or `blocked` finding remains.
