# dpp-ext-toml treated by tombi — Design

**Status:** Approved
**Date opened:** 2026-08-04
**Issue:** [`../../issues/2026-08-04-kakehashi-dpp-tombi.md`](../../issues/2026-08-04-kakehashi-dpp-tombi.md)
**Author:** kiyama
**Review required:** letter A (spec 09 §2.2, ordinary design)

## §1 Context & success criteria

dpp-ext-toml (`denops/@dpp-exts/toml/main.ts`) is a pure loader: it parses
a TOML file with Deno's `@std/toml/parse` into dpp plugin definitions.
Its `autoload/dpp/ext/toml.vim#syntax()` provides *manual Vim syntax
embedding* for the embedded vim/lua hook strings — it is not guarded by
`if !has('nvim')`; in nvim it merely disables tree-sitter highlighting for
that buffer (`if has('nvim') && exists(':TSBufDisable')`). It provides no
schema validation and no LSP integration. The nvim config's dpp TOML files
live in `~/.config/nvim/deps/*.toml` (8 files, 2026-08-04); they already
get nvim filetype `toml`, so kakehashi attaches tombi to them today (plain
TOML lint/format only).

With taplo, per-kind TOML treatment came from `taplo.toml` schema config.
Tombi 1.2.6 replaces this with `[[schemas]]` glob entries in a tombi
config. This design delivers the dpp-specific treatment via a user-level
tombi config.

Success criteria:

- **S1** — `dot_config/tombi/config.toml` maps the nvim `deps/*.toml`
  files to a local dpp schema via `[[schemas]]` glob `**/.config/nvim/
  deps/*.toml`, with the schema path resolved relative to the config dir.
- **S2** — `dot_config/tombi/dpp.schema.json` derives from dpp.vim
  `Plugin` / `MultipleHook` and dpp-ext-toml `Toml` types; every field
  used by the 8 real deps files validates clean (no false positives).
- **S3** — A broken variant (wrong type + unknown key) produces schema
  diagnostics both via `tombi lint` and via the LSP path (headless nvim →
  kakehashi → tombi → user config).
- **S4** — Files outside the glob stay plain-TOML (positive control
  clean); kakehashi config, mise config, packages.toml, and the nvim repo
  are untouched.
- **S5** — `chezmoi apply` installs both files under
  `~/.config/tombi/`; the config file documents discovery + shadowing.

## §2 Alternatives considered

- **A — User-level tombi config (CHOSEN).** `~/.config/tombi/config.toml`
  + `dpp.schema.json`, chezmoi-managed. Applies everywhere, survives
  outside nvim; glob pins `**/.config/nvim/deps/*.toml`.
- **B — Project `tombi.toml` in the nvim repo.** More precise scoping, but
  it would *shadow* the user config for the whole nvim repo and the nvim
  repo is owned by a concurrent agent session. Rejected for now;
  documented as the escape hatch if repo-local overrides are needed.
- **C — Per-file comment directives** (`#:schema …`). Invasive, per-file;
  rejected.
- **D — Nothing (plain TOML lint/format only).** Loses per-type
  validation/completion; rejected.

## §3 Architecture / Invariants

Verified tombi 1.2.6 facts (source: `rust/serde_tombi/src/config.rs`,
`crates/tombi-lsp/src/config_manager.rs`):

1. **Config discovery is per document.** `load_with_path(file_dir)` walks
   up: `.tombi.toml` → `tombi.toml` → `.config/tombi.toml` →
   `pyproject.toml` (with `[tool.tombi]`); the first hit wins as the
   *project* config and the search stops — the walk continues at parent
   dirs only while no project config has been found. Otherwise the *user*
   config applies (`$XDG_CONFIG_HOME/tombi/config.toml` or
   `~/.config/tombi/config.toml`), then the *system* config
   (`/etc/tombi/config.toml`), then built-in defaults.
2. **Project config replaces the user config entirely** — no merge.
3. `[[schemas]]` entries match by glob `include` against the document path
   (verified: absolute-path globs like `**/deps/*.toml` match), with a
   schema `path` resolved relative to the config file's directory (for
   user config: relative to `~/.config/tombi/`).
4. Schema validation is strict by default (`schema.strict = true` →
   `additionalProperties: false` when unspecified); an explicit
   `additionalProperties` wins.
5. `pyproject.toml` / `Cargo.toml` are already special-cased (schemastore
   catalog + built-in cargo/pyproject/uv extensions) — nothing to add.

Invariants:

- **I-DT1 — Glob scoping.** The schema applies only to
  `**/.config/nvim/deps/*.toml`; all other TOML keeps default treatment
  (positive control: a `bogus_key` outside the glob stays clean).
- **I-DT2 — No false positives on real files.** Schema fields derive from
  dpp.vim `Plugin` (all optional; `name` derived from repo basename),
  `MultipleHook` (`plugins` required; `hooks_file` / `hook_add` /
  `hook_source` / `hook_post_source` optional) and dpp-ext-toml `Toml`;
  `on_map` is a `Record<string, string|string[]>`; `denops_wait` (boolean)
  included; `ftplugin` is a string Record; `dummy_mappings` is a
  `[string, string][]` tuple (exactly 2 items). `extAttrs` /
  `protocolAttrs` are free-form.
- **I-DT3 — Strict-but-scoped.** `additionalProperties: false` on plugin
  and multiple_hooks tables catches typos (`hook_addd`) while top-level
  stays lenient (`additionalProperties: true`).
- **I-DT4 — No kakehashi change.** tombi + language `toml` + `.git`
  workspace marker already deliver the bridge.

## §4 Scope / staging breakdown

1. `dot_config/tombi/config.toml` (new): `[[schemas]]` dpp entry.
2. `dot_config/tombi/dpp.schema.json` (new): the schema.
3. `chezmoi apply` → `~/.config/tombi/`.
4. Verification (via approved plan; exploratory evidence already gathered
   pre-approval, see §5 note): CLI lint on the 8 real files, broken
   variant, positive control, headless-nvim LSP pull.
5. Result-log; close issue.

Non-changes: kakehashi config, mise config, packages.toml, nvim config
(the nvim repo may later add its own `tombi.toml`; shadowing caveat
documented in the config file).

## §5 Implementation detail & verification plan

### §5.1 `dot_config/tombi/config.toml`

```toml
[[schemas]]
path = "dpp.schema.json"
include = ["**/.config/nvim/deps/*.toml"]
```

Header comment documents the full discovery chain (project → user →
`/etc/tombi/config.toml` → defaults) and the shadowing rule.

### §5.2 `dot_config/tombi/dpp.schema.json`

- Root: `plugins` (array of plugin), `ftplugins` (string Record),
  `hooks_file` (string), `multiple_hooks` (array of `MultipleHook`).
- Plugin: all dpp.vim `Plugin` fields, every one optional, tuple-typed
  `dummy_mappings`, `additionalProperties: false`.
- `MultipleHook`: `plugins` required; `hooks_file`, `hook_add`,
  `hook_source`, `hook_post_source` optional; `additionalProperties:
  false`.
- Top level `additionalProperties: true` (dpp-ext-toml forwards unknown
  top-level keys).

### §5.3 Verification plan

- P1 — `tombi lint` on `~/.config/nvim/deps/*.toml`: all 8 clean.
- P2 — broken variant (`repo = 42`, `bogus_key`): schema errors via CLI.
- P3 — same broken variant via LSP: headless nvim → kakehashi → tombi →
  user config; pull diagnostics shows the schema errors.
- P4 — positive control (file outside the glob, `bogus_key`): clean.
- P5 — real `dpp.toml` via LSP: stable 0 diagnostics (no false positives).

> Note (lifecycle): §5-P1..P5 evidence was gathered exploratorily before
> approval (2026-08-04) so the schema could be corrected against reality;
> the approved plan re-executes and records it in the result-log.

## §6 Open questions

- **Q1 (resolved — config placement):** user-level `~/.config/tombi/`
  vs nvim-repo project config. User-level chosen (A); shadowing caveat
  documented; a future nvim-repo `tombi.toml` would need the entry moved
  there.
- **Q2 (resolved — schema source):** hand-written from dpp.vim
  `Plugin`/`MultipleHook` + dpp-ext-toml `Toml` types (no public dpp
  schema exists).
- **Q3 (resolved — kakehashi):** no change needed (I-DT4).

## §7 Risks / edge cases

- **Project config shadowing.** Any `.tombi.toml` / `tombi.toml` /
  `.config/tombi.toml` / `pyproject.toml[tool.tombi]` up-tree replaces the
  user config; if the nvim repo adopts one, the dpp schema entry must move
  there (documented in the config header).
- **Schema drift.** dpp.vim `Plugin` grows fields (the type is open); new
  keys error until added. Mitigation: fields are documented, the file is
  chezmoi-managed, and the nvim agent was notified.
- **Other `deps/` dirs.** The glob is pinned to `.config/nvim`; other
  repos' `deps/*.toml` are unaffected (by design).

## §8 Review pass-1 responses

Review:
[`2026-08-04-kakehashi-dpp-tombi-review-pass1-A-factual.md`](../../reviews/2026-08-04-kakehashi-dpp-tombi-review-pass1-A-factual.md)

- **A-F1 (design structure):** addressed — §1 now carries labeled `S1`–`S5`
  criteria; §4 has the staging breakdown; §6 is the Open questions section
  with `Q<n>` labels; §7 risks remain separate.
- **A-F2 (`MultipleHook` fidelity):** addressed — §5.2/I-DT2 and the schema
  now require only `plugins` and accept `hooks_file`, `hook_add`,
  `hook_source`, `hook_post_source` (verified against
  `dpp.vim/denops/dpp/base/config.ts`; type name minified in the local
  cache, shape confirmed).
- **A-F3 (`dummy_mappings` tuple):** addressed — schema items now carry
  `minItems: 2` + `maxItems: 2` alongside `prefixItems`.
- **A-F4 (syntax description):** addressed — §1 no longer claims
  `if !has('nvim')` guarding or "no syntax"; it describes the manual Vim
  syntax embedding with the nvim tree-sitter disable guard.
- **A-F5 (discovery details):** addressed — §3 documents the
  `/etc/tombi/config.toml` system level, the stop-at-first-hit traversal
  semantics, and `.tombi.toml` is included in §7 shadowing risks.
- **A-F6 (issue doc structure):** addressed — the issue now has `## Context`
  and `## Notes`, links the design, and no longer references the
  result-log before its lifecycle stage.
- **A-F7 (lifecycle):** addressed — §5 is now the verification *plan* with
  a note recording the exploratory pre-approval evidence and the approved
  plan/result-log re-execution.
