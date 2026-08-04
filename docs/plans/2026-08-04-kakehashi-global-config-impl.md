# Global kakehashi configuration — Implementation Plan

**Status:** executing
**Spec:** [2026-08-04-kakehashi-global-config-design](../specifications/implementations/2026-08-04-kakehashi-global-config-design.md)
**Parent issue:** [2026-08-04-kakehashi-global-config](../issues/2026-08-04-kakehashi-global-config.md)
**Review trail:** [pass-1 aggregate](../reviews/2026-08-04-kakehashi-global-config-review-pass1.md) (A + D, Approved)

## Phase 1 — Config & inventory files (single commit)

1. `dot_config/kakehashi/kakehashi.toml` (new): eight `languageServers`
   (§5.1) + `languages` bridge section (§5.2).
2. `dot_config/mise/config.toml`: `cargo:emmylua_ls` switch + comment
   naming all three sync targets.
3. `dependencies/packages.toml`: `rust-analyzer` (paru, layer 4);
   kakehashi `has_configs = true`.
4. `programs/generate_deps/tests/test_kakehashi_container_install.py`:
   `has_configs: True`.
5. `programs/generate_deps/tests/test_kakehashi_config_sync.py` (new):
   server→provider mapping, bare commands, comment sync.
6. `docs/specifications/20-container-rules.md`: I-KAKEHASHI6 narrowing.
7. `make gen-deps` (regenerates spec 02 + `layer_4/paru.txt`).

**Acceptance**: pytest suite green; `make gen-deps` idempotent
(doc_updated=False on rerun).

## Phase 2 — Host install

1. `paru -S rust-analyzer`; `rm ~/.local/share/cargo/bin/rust-analyzer`.
2. `chezmoi apply` (--force for the mise config).

**Acceptance**: `command -v rust-analyzer` → `/usr/sbin/rust-analyzer`;
`rust-analyzer --version` exit 0; all eight `cmd[0]` resolve with mise
shims on PATH.

## Phase 3 — Runtime verification

1. Headless-nvim LSP pull with only the user config: broken Python → 3
   pyright errors; broken Lua → emmylua_ls errors.
2. `kakehashi diagnose` / `format --check` on a Python-fenced Markdown
   file.

**Acceptance**: diagnostics pull for pyright and emmylua_ls; CLI runs exit
0.

## Phase 4 — Docs close-out

1. Result-log in `docs/issues/2026-08-04-phase-kakehashi-global-config.md`.
2. Issue → closed.

**Acceptance**: issue status `closed`; design status `Approved`.

**Rollback**: revert the Phase-1 commit (gen-deps regenerable); host:
`paru -R rust-analyzer` (proxy restoration documented in design §6).
