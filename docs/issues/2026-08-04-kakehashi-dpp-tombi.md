# dpp-ext-toml config files treated by tombi (per-type TOML schemas)

**Date:** 2026-08-04
**Status:** closed (see [result-log](2026-08-04-phase-kakehashi-dpp-tombi.md))
**Related:** [design](2026-08-04-kakehashi-dpp-tombi-design.md),
[plan](2026-08-04-kakehashi-dpp-tombi-impl.md)

## Context

- dpp-ext-toml (`denops/@dpp-exts/toml/main.ts`) is a pure loader: it
  parses a TOML file with Deno's `@std/toml/parse` into dpp plugin
  definitions. Its `autoload/dpp/ext/toml.vim#syntax()` provides manual Vim
  syntax embedding (also active in nvim, with a tree-sitter disable guard)
  but no schema or LSP integration.
- The nvim config's dpp TOML files live in `~/.config/nvim/deps/*.toml`
  (8 files as of 2026-08-04); they already get filetype `toml`, so
  kakehashi attaches tombi to them today (plain TOML lint/format only).
- With the old taplo setup, different kinds of TOML (dpp plugin configs,
  `pyproject.toml`, …) were distinguished per file type via taplo's schema
  config. Tombi 1.2.6 offers the equivalent as `[[schemas]]` glob entries
  in a tombi config (project `tombi.toml` or user
  `~/.config/tombi/config.toml`).

## Problem

How to give the dpp config files their own tombi treatment (validation,
completion) — the per-type distinction taplo provided — and does kakehashi
need any change?

## Acceptance criteria

1. A user-level tombi config (`~/.config/tombi/config.toml`, chezmoi
   `dot_config/tombi/config.toml`) maps the nvim `deps/*.toml` files to a
   local dpp JSON schema (`dpp.schema.json`, derived from dpp.vim `Plugin`
   / `MultipleHook` and dpp-ext-toml `Toml` types).
2. `tombi lint` on the real `~/.config/nvim/deps/*.toml` files: all clean.
3. A broken variant (wrong type + unknown key) fails with schema
   diagnostics — via CLI and via the LSP path (kakehashi in nvim).
4. Files outside the glob stay plain-TOML (no false positives).
5. No kakehashi config change needed (tombi already covers language
   `toml`; verified).

## Notes

- kakehashi side is unchanged: `languageServers.tombi` already covers
  language `toml`, and the `.git` workspace marker roots the nvim config
  dir; tombi's per-document discovery then reaches the user config.
- Shadowing caveat: a project `tombi.toml` / `.tombi.toml` /
  `pyproject.toml` with `[tool.tombi]` anywhere up-tree replaces the user
  config entirely for files under it.
- `pyproject.toml` / `Cargo.toml` need no custom schema: tombi's
  schemastore catalog + built-in cargo/pyproject/uv extensions already
  handle them.
