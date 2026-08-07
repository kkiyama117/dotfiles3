# Phase complete — dpp-ext-toml treated by tombi

**Date:** 2026-08-04
**Status:** executed
**Parent:** [2026-08-04-kakehashi-dpp-tombi.md](2026-08-04-kakehashi-dpp-tombi.md)
**Plan:** [2026-08-04-kakehashi-dpp-tombi-impl](../plans/2026-08-04-kakehashi-dpp-tombi-impl.md)

## Acceptance evidence

| Criterion | Result | Evidence |
|---|---|---|
| S1 — user tombi config + glob | ✅ | `dot_config/tombi/config.toml`; `[[schemas]]` include `**/.config/nvim/deps/*.toml`; schema path resolved relative to config dir (verified `file:///…/tombi/dpp.schema.json`) |
| S2 — schema clean on real files | ✅ | `tombi lint` on 8 real `~/.config/nvim/deps/*.toml`: all clean (schema fixed per A-F2 `MultipleHook`, A-F3 tuples) |
| S3 — broken variant errors, CLI + LSP | ✅ | CLI: `Expected a value of type String, but found Integer` + `"bogus_key" is not allowed`; LSP (headless nvim → kakehashi → tombi → user config): 3 Error diagnostics pulled |
| S4 — no false positives; no kakehashi change | ✅ | positive control (`bogus_key` outside glob) clean; kakehashi/mise/packages.toml/nvim repo untouched |
| S5 — chezmoi apply | ✅ | `~/.config/tombi/config.toml` + `dpp.schema.json` installed; config header documents discovery + shadowing |

## Notes / residuals

- tombi's per-document discovery walks up from each file; a future
  project `tombi.toml` / `.tombi.toml` / `pyproject.toml[tool.tombi]` in
  the nvim repo would replace the user config for files under it (entry
  would need to move there).
- dpp.vim `Plugin` is an open type; new upstream fields error until added
  to the schema (chezmoi-managed; nvim agent notified).
- CLI glob semantics: patterns match the document path (absolute in LSP);
  cwd-relative patterns like `deps/*.toml` do not match absolute paths.
