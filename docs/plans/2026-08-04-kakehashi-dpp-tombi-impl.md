# dpp-ext-toml treated by tombi — Implementation Plan

**Status:** executing
**Spec:** [2026-08-04-kakehashi-dpp-tombi-design](../specifications/implementations/2026-08-04-kakehashi-dpp-tombi-design.md)
**Parent issue:** [2026-08-04-kakehashi-dpp-tombi](../issues/2026-08-04-kakehashi-dpp-tombi.md)
**Review trail:** [pass-1 aggregate](../reviews/2026-08-04-kakehashi-dpp-tombi-review-pass1.md) (A, Approved)

## Phase 1 — Files

1. `dot_config/tombi/config.toml` (new): `[[schemas]]` dpp entry +
   discovery/shadowing header.
2. `dot_config/tombi/dpp.schema.json` (new): dpp.vim `Plugin` /
   `MultipleHook` / dpp-ext-toml `Toml` derived schema.
3. `chezmoi apply` → `~/.config/tombi/`.

**Acceptance**: both files land; no other repo file changes.

## Phase 2 — Verification (re-executes design §5-P1..P5)

1. P1 `tombi lint ~/.config/nvim/deps/*.toml` — 8 clean.
2. P2 broken variant — CLI schema errors.
3. P3 broken variant — LSP pull (headless nvim → kakehashi) shows errors.
4. P4 positive control — clean.
5. P5 real `dpp.toml` — 0 diagnostics.

**Acceptance**: P1/P4/P5 clean; P2/P3 error.

## Phase 3 — Docs close-out

1. Result-log in `docs/issues/2026-08-04-phase-kakehashi-dpp-tombi.md`.
2. Issue → closed; design status → Approved.

**Acceptance**: issue closed; result-log carries the evidence table.

**Rollback**: delete both `dot_config/tombi` files + `chezmoi apply`;
user config falls back to defaults (no behavior change for plain TOML).
