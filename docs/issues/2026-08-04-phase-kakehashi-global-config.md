# Phase complete — global kakehashi configuration

**Date:** 2026-08-04
**Status:** executed
**Parent:** [2026-08-04-kakehashi-global-config.md](2026-08-04-kakehashi-global-config.md)
**Plan:** [2026-08-04-kakehashi-global-config-impl](../plans/2026-08-04-kakehashi-global-config-impl.md)

## Acceptance evidence

| Criterion | Result | Evidence |
|---|---|---|
| S1 — config loads; bridge runs | ✅ | `make gen-deps` idempotent; headless-nvim LSP pull with only the user config: broken Python → 3 pyright errors; broken Lua → 2 emmylua_ls errors + 1 hint |
| S2 — mise config + packages.toml | ✅ | `cargo:emmylua_ls` switch committed (user's `94f5556` already carried the tool entries); `rust-analyzer` paru layer 4 in `dependencies/packages.toml` |
| S3 — gen-deps + tests | ✅ | `make gen-deps` regenerated spec 02 + `layer_4/paru.txt` (24 packages); pytest `41 passed` (venv; host lacks pytest) |
| S4 — host rust-analyzer | ✅ | `paru -S rust-analyzer` → `/usr/sbin/rust-analyzer` (extra `20260608-1`); stale `~/.local/share/cargo/bin/rust-analyzer` proxy removed; `--version` → `rust-analyzer 1 (7ea2b259ca 2026-06-07)` |
| S5 — chezmoi apply + resolution | ✅ | `~/.config/kakehashi/kakehashi.toml` installed; all eight `cmd[0]` resolve (6 mise shims, `/usr/sbin/rust-analyzer`, `/usr/sbin/clangd`) |
| S6 — spec 20 narrowing | ✅ | `I-KAKEHASHI6` reworded to the final-image property (build-prepass scratch rendering allowed; verified against the Containerfile) |

## Notes / residuals

- `kakehashi diagnose` (one-shot CLI) returns 0 diagnostics even on broken
  files because the pull races the downstream server's async analysis
  (`pulls_answered=0` in metrics); the LSP flow (nvim) pulls correctly.
  Upstream CLI timing characteristic, not a config defect.
- The local `~/.config/mise/config.toml` had been rewritten by an
  independent nvim-config agent session (07:41–08:22 on 2026-08-04); the
  repo now matches the final host state (cargo:emmylua_ls).
- Container parity (Layer 3-4 mise install incl. cargo:emmylua_ls; Layer 4
  rust-analyzer) is exercised on the next `make build`, not by this change.
