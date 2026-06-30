# Result-log — chezmoi-config-template (manage runtime chezmoi.toml via .chezmoi.toml.tmpl)

**Date:** 2026-06-30
**Phase:** chezmoi-config-template
**Issue:** [2026-06-30-chezmoi-config-template.md](2026-06-30-chezmoi-config-template.md) → closed
**Plan:** [2026-06-30-chezmoi-config-template-impl.md](../plans/2026-06-30-chezmoi-config-template-impl.md)
**Design:** [2026-06-30-chezmoi-config-template-design.md](../specifications/implementations/2026-06-30-chezmoi-config-template-design.md)

## Summary

Replaced the hardcoded `chezmoi.toml` heredoc in `entrypoint.sh` and the
static `bind/layer_2_files/chezmoi.toml` with a single dotfiles-managed
`.chezmoi.toml.tmpl` at the chezmoi source root (repo root). Both phases
build-prepass (`BUILD_MODE=true`) and runtime entrypoint (`BUILD_MODE`
unset → `false`) render `~/.config/chezmoi/chezmoi.toml` via
`chezmoi execute-template --init` (surgical; no `chezmoi init` git side
effects). `bind/layer_2_files/` was removed. Layer 5-3 still strips the
carried-forward config so the entrypoint renders it fresh.

## Acceptance evidence (S1–S11)

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| S1 | `chezmoi.toml` from single `.chezmoi.toml.tmpl`; no entrypoint heredoc | PASS | `.chezmoi.toml.tmpl` committed (`cfb4ead`); `entrypoint.sh` heredoc replaced by `chezmoi execute-template --init` (`cfeead5`); `rg 'cat >.*TOML'` → none |
| S2 | `build_mode` driven by `BUILD_MODE` env | PASS | template renders `true` with `BUILD_MODE=true`, `false` unset (Phase 1 Step 3 + Phase 2 Step 4) |
| S3 | both phases use `execute-template --init` | PASS | Containerfile Stage 2 `RUN BUILD_MODE=true chezmoi execute-template --init` (`c233c11`); entrypoint same command (`cfeead5`) |
| S4 | `bind/layer_2_files/` + COPY removed | PASS | `ls container/bind/` shows only `layer_1_files/`, `layer_5_files/`; no COPY in Containerfile |
| S5 | `BUILD_MODE` inline (not ENV); absent from inspect/image Env | PASS | `podman inspect` / `podman image inspect` `Env` → `OK_CONTAINER` / `OK_IMAGE` (no `BUILD_MODE`) |
| S6 | Layer 5-3 strip preserved | PASS | baked image (`--entrypoint bypassed`) `~/.config/chezmoi/` has only `chezmoistate.boltdb` (no `chezmoi.toml`) |
| S7 | `make build` green; `.chezmoi.toml.tmpl` ignored by `chezmoi apply` | PASS | image `00564308eb87`; `chezmoi managed \| grep chezmoi.toml` → `NOT_MANAGED` (special file) |
| S8 | `make up` (±secrets): Up, apply OK, `build_mode=false` (USERNAME-owned), secrecy unchanged, toolchain persists | PASS | `Up`; `chezmoi.toml = build_mode = false`, owner `kiyama`; all-proc environ `OK_ALL_CLEAN` (no `BW_*`); `rustc 1.96.0` |
| S9 | build-prepass render = `build_mode = true` | PASS | `BUILD_MODE=true chezmoi execute-template --init < .chezmoi.toml.tmpl` → `build_mode = true`; build reached Stage 2 `chezmoi apply` (log `chezmoi apply` count = 1, green) |
| S10 | host not broken | PASS | host render (unset) → `build_mode = false` (correct host/runtime value); `chezmoi apply` does not re-render the config template, so existing host config is unaffected |
| S11 | specs 01/13/20/21 + comments updated | PASS | `4dfa07c`; `rg layer_2_files\|heredoc\|created fresh by the entrypoint\|root-owned.*COPY` in 01/13/20/21 → none |

## Q1 / Q2 outcomes

- **Q1 (`env` inside `execute-template --init`):** RESOLVED — works. `chezmoi execute-template --init < tmpl` with `BUILD_MODE=true` renders `build_mode = true`; unset renders `false`. (Caveat found during verification: `podman run` stdin tests require `-i` to attach stdin; the actual Containerfile/entrypoint use native shell `< file` redirect, so this is only a test-harness detail.)
- **Q2 (entrypoint template-exists guard):** RESOLVED — added. `entrypoint.sh` now `[ -f "$CONFIG_TEMPLATE" ] || exit 1` with a loud two-line diagnostic before rendering. Not triggered in normal `make up` (the bind always carries `.chezmoi.toml.tmpl`).

## Secrecy invariants (unchanged by this change)

- No `BW_*` in `podman inspect` `Env`, image `Env`, or any `/proc/*/environ` after exec (`OK_CONTAINER`, `OK_IMAGE`, `OK_ALL_CLEAN`).
- No `BUILD_MODE` in `podman inspect` / image `Env` (inline `RUN`, not `ENV`).
- All secrecy checks used quiet `grep -qi` (presence/absence only) — no credential values printed.

## Commit trail

1. `9b6b98d` — docs: raise issue + design
2. `367d152` — docs: add implementation plan (5 phases); approve design
3. `cfb4ead` — feat(chezmoi): add `.chezmoi.toml.tmpl` config template
4. `c233c11` — feat(container): render build-prepass from template; drop `bind/layer_2_files`; fix stale comments
5. `cfeead5` — feat(entrypoint): render from template via `execute-template --init`; guard on template presence
6. `4dfa07c` — docs: sync specs 01/13/20/21

## Deviations from plan

- None functional. Minor: `bind/layer_2_files/chezmoi.toml` was gitignored
  (not tracked), so it was removed from disk only (no `git rm`) — the plan
  said `git rm -r` which failed harmlessly; replaced with `rm -rf`.
- Plan's `podman run ... < file` verification commands needed `-i` for
  stdin attach (test-harness detail; not a code change).

## Image

- `localhost/dotfiles-manjaro:latest` → `00564308eb87` (after Phase 3; Phase 5 rebuild was a cached no-op, same ID).

## Follow-ups (out of scope, tracked elsewhere)

- Wire the actual `{{ if .build_mode }}` guard into `.zshenv` (spec 21 #6 known drift; no build-only dotfile exists yet).
- `make bw-secrets` setup helper (still doc-only / out of scope).