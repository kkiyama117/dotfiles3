# Global kakehashi configuration — Design

**Status:** Approved
**Date opened:** 2026-08-04
**Issue:** [`../../issues/2026-08-04-kakehashi-global-config.md`](../../issues/2026-08-04-kakehashi-global-config.md)
**Author:** kiyama
**Review required:** letters A + D (spec 09 §2.2)

## §1 Context & success criteria

kakehashi v0.9.0 merges four config layers, lowest → highest:
programmed defaults → user config (`~/.config/kakehashi/kakehashi.toml`) →
project config (`./kakehashi.toml`) → editor `initializationOptions` /
`didChangeConfiguration`. Deep merge per key; later sources win.
(Upstream [`docs/README.md`](https://github.com/atusy/kakehashi/blob/main/docs/README.md),
"Configuration", and
[`configuration-merging-strategy.md`](https://github.com/atusy/kakehashi/blob/main/docs/architecture-decisions/configuration-merging-strategy.md).)

Today the user config layer is empty: nvim pushes everything
(`~/.config/nvim/lua/vimrc/kakehashi_config.lua`,
`~/.config/nvim/lua/vimrc/kakehashi_bridge.lua`, runtime
`didChangeConfiguration` merge with `'keep'` — existing keys win), so
non-nvim editors and the `kakehashi format`/`diagnose` CLIs have no bridge
servers.

Installed LSP servers (audited 2026-08-04):

| server | cmd | install |
|---|---|---|
| denols | `deno lsp` | mise `deno` |
| emmylua_ls | `emmylua_ls` | mise `cargo:emmylua_ls` (EmmyLuaLs/emmylua-analyzer-rust) |
| gopls | `gopls` | mise `go:golang.org/x/tools/gopls` |
| pyright | `pyright-langserver --stdio` | mise `npm:pyright` |
| rust_analyzer | `rust-analyzer` | paru, official `extra` repo (was: broken rustup proxy) |
| tombi | `tombi lsp` | mise `aqua:tombi-toml/tombi` |
| vtsls | `vtsls --stdio` | mise `npm:@vtsls/language-server` |
| clangd | `clangd` | pacman `clang` (layer 1) |

Success criteria:

- **S1** — `dot_config/kakehashi/kakehashi.toml` declares
  `languageServers` for all eight servers with bare-command `cmd`s and
  `workspaceMarkers` mirroring nvim-lspconfig `root_markers` (§5.1), and
  `languages` mirroring the nvim bridge contract (§5.2). The file
  deserializes and the bridge runs: an LSP session configured with only
  the user config pulls real diagnostics (verified: pyright 3 errors on a
  broken Python file; emmylua_ls 2 errors + 1 hint on a broken Lua file).
- **S2** — `dot_config/mise/config.toml` declares the LSP tool entries
  (already committed by the user as `94f5556` "Add LSP from mise"; this
  design switches `emmylua_ls` from `aqua:LuaLS/lua-language-server` to
  `cargo:emmylua_ls` per explicit user choice, and extends the sync
  comment). `rust-analyzer` is declared in
  `dependencies/packages.toml` as `manager = "paru"`, `layer = 4`.
- **S3** — `make gen-deps` is idempotent and updates spec 02's AUTO-GEN
  block (kakehashi `configs` `no` → `yes`; new Layer 4 `rust-analyzer`
  row); the pytest suite passes (updated
  `test_kakehashi_container_install.py` + new
  `test_kakehashi_config_sync.py`).
- **S4** — Host: `paru -S rust-analyzer` installed `/usr/sbin/rust-analyzer`;
  stale `~/.local/share/cargo/bin/rust-analyzer` proxy removed;
  `command -v rust-analyzer` → `/usr/sbin/rust-analyzer`;
  `rust-analyzer --version` exits 0.
- **S5** — `chezmoi apply` installs `~/.config/kakehashi/kakehashi.toml`;
  all eight `cmd[0]` values resolve via mise shims / system packages.
- **S6** — Spec 20 `I-KAKEHASHI6` is narrowed to the final-image property
  (user-approved); no Containerfile/Makefile/nvim-config change.

## §2 Alternatives considered

- **A — Global user config (CHOSEN).** Editor-agnostic catalog per the
  upstream "configured once" model; the nvim layer keeps overriding on
  top. Cost: a third file to keep in sync with the nvim config.
- **B — nvim-only init_options (status quo).** Rejected: other editors and
  the kakehashi CLIs get no bridge.
- **C — rust-analyzer via mise (`aqua:rust-lang/rust-analyzer`).**
  Rejected by explicit user choice: install from pacman/paru. The official
  `extra` repo ships a signed prebuilt (`rust-analyzer 20260608-1`, deps
  `gcc-libs` + `rust-src`). Spec 24 (Rust packages rule) is
  **inapplicable**: its §1 scopes it to packages that depend on the Rust
  toolchain, and this package pulls none. The declaration is instead
  authorized by spec 02's `paru` manager rule — "paru resolves repo
  packages too" — with Layer 4 placement matching the other user-facing
  tools.
- **D — rust-analyzer via rustup component.** Rejected by the same user
  choice; also leaves the container's minimal-profile rustup without it.
- **E — emmylua_ls from `aqua:LuaLS/lua-language-server`.** Rejected by
  explicit user choice: the nvim-lspconfig `cmd` is `emmylua_ls` (the
  EmmyLuaLs Rust analyzer, settings under the `emmylua` namespace), which
  the LuaLS binary does not satisfy. `cargo:emmylua_ls` ships the exact
  `emmylua_ls` binary (0.24.0, verified). Note: on 2026-08-04 an
  independent agent session working on the nvim config made the same
  switch on the host (07:41 add → 08:18 ubi attempt → 08:20
  `cargo:emmylua_ls` + `mise install` at 08:22); this design follows that
  host state.

## §3 Architecture / Invariants

- **I-KC1 — Bare-command `cmd`s.** Every `languageServers.*.cmd[0]` is a
  bare name resolved through PATH (mise shims, `/usr/bin`); no absolute
  paths. kakehashi keeps PATH lookup semantics for `cmd[0]` by design.
- **I-KC2 — Server→provider coverage contract.** The kakehashi
  `languageServers` keys are the authoritative eight-server catalog. Each
  server maps to exactly one install provider — a mise `[tools]` key or a
  `packages.toml` package (see the mapping in
  `test_kakehashi_config_sync.py`). This is a mapping, not set equality:
  `denols` comes from the `deno` runtime entry, `stylua` is a formatter
  with no server entry, and the nvim `bridged_servers` list is a
  deliberate seven-server subset (no clangd).
- **I-KC3 — rust-analyzer is a system package.** Installed via paru from
  the official `extra` repo; the stale rustup proxy must not shadow
  `/usr/bin` (host PATH order puts `$CARGO_HOME/bin` first). The proxy is
  component-independent host state (observed: proxy present, component
  never in the minimal-profile component list); rustup regenerates proxies
  only for installed components, so removal is stable.
- **I-KC4 — No build-flow change.** Containerfile, Makefile, entrypoint,
  specs 21, and nvim config are untouched; Layer 3-4 `mise install` and
  the Layer 4 `aur` stage pick the inventory up via `make gen-deps`.
  Spec 20 `I-KAKEHASHI6` is reworded (not re-scoped): the build pre-pass
  renders the kakehashi config into `/tmp/build-home` scratch, which Stage
  4 removes before the final image layer; the final image still contains
  no configuration.
- **I-KC5 — Config layering preserved.** The global file is the lowest
  non-default layer; editor `initializationOptions`/`didChangeConfiguration`
  still override per key (nvim behavior unchanged).
- **I-KC6 — No secrets or network at runtime.** The config declares
  process commands only; no credentials, no downloads.

## §4 Scope / staging breakdown

1. Issue + design + pass-1 review (letters A + D).
2. `dot_config/kakehashi/kakehashi.toml` (new; §5.1, §5.2); validated with
   the kakehashi CLI and a headless-nvim LSP pull test (§5.4).
3. `dot_config/mise/config.toml`: `aqua:LuaLS/lua-language-server` →
   `cargo:emmylua_ls` (user choice); sync comment names all three targets.
   (The tool entries themselves were committed by the user at `94f5556`.)
4. `dependencies/packages.toml`: `rust-analyzer` between `ripgrep` and
   `rsync` — `manager = "paru"`, `layer = 4`, `has_configs = false`;
   kakehashi `has_configs = false → true`.
5. `programs/generate_deps/tests/`: kakehashi inventory expectation
   (`has_configs: True`), new `test_kakehashi_config_sync.py`
   (server→provider mapping, bare-command check, comment-sync check).
   `make gen-deps` regenerates spec 02 + `layer_4/paru.txt`.
6. Spec 20 `I-KAKEHASHI6` narrowing (user-approved).
7. Host: `paru -S rust-analyzer`; remove the stale rustup proxy; verify.
8. `chezmoi apply`; runtime verification (§5.4).
9. Result-log; close the issue.

Explicit non-changes: `Makefile`, `Containerfile`, entrypoint, nvim config,
specs 21/24, `dot_zshenv.tmpl`, `captureMappings`, `features` (defaults).

## §5 Implementation detail

### §5.1 `languageServers`

Keys mirror the nvim `bridged_servers` names so the bridge's `'keep'` merge
reuses global entries instead of duplicating them:

| key | cmd | languages | workspaceMarkers |
|---|---|---|---|
| denols | `["deno", "lsp"]` | typescript, javascript, typescriptreact, javascriptreact | `[["deno.lock", "deno.json", "deno.jsonc"], ".git"]` |
| emmylua_ls | `["emmylua_ls"]` | lua | `[[".emmyrc.json", ".emmyrc.lua", ".luarc.json", ".luarc.jsonc"], [".luacheckrc", ".stylua.toml", "stylua.toml", "selene.toml", "selene.yml"], ".git"]` |
| gopls | `["gopls"]` | go, gomod, gowork, gotmpl | `["go.work", "go.mod", ".git"]` |
| pyright | `["pyright-langserver", "--stdio"]` | python | `["pyrightconfig.json", "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile", ".git"]` |
| rust_analyzer | `["rust-analyzer"]` | rust | `["Cargo.toml", ".git"]` |
| tombi | `["tombi", "lsp"]` | toml | `["tombi.toml", "pyproject.toml", ".git"]` |
| vtsls | `["vtsls", "--stdio"]` | typescript, javascript, typescriptreact, javascriptreact | `[["package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb", "bun.lock"], ".git"]` |
| clangd | `["clangd"]` | c, cpp, objc, objcpp, cuda | `[".clangd", ".clang-tidy", ".clang-format", "compile_commands.json", "compile_flags.txt", "configure.ac", ".git"]` |

`workspaceMarkers` mirrors nvim-lspconfig `root_markers`, which are passed
to `vim.fs.root` (`/usr/share/nvim/runtime/lua/vim/fs.lua`,
`M.root` iterates top-level entries **in order** — first entry that matches
anywhere wins; a nested-list entry is one equal-priority group searched per
ancestor). kakehashi's documented semantics are identical (flat = priority
order, nested = equal group), so lspconfig lists are transcribed
**as-is**: flat for tombi/pyright/clangd (priority order, `.git` last),
nested for the lspconfig `{group, {'.git'}}` shapes (denols, vtsls,
emmylua), and priority order for gopls' `go.work → go.mod → .git` or-chain.
The rust_analyzer entry is a documented approximation: lspconfig also
recognizes `rust-project.json` and resolves Cargo workspace roots via
`cargo metadata`, which `workspaceMarkers` cannot reproduce; `["Cargo.toml",
".git"]` covers the common cases.

clangd's languages omit lspconfig's `c.doxygen` / `cpp.doxygen` — those
are nvim filetypes, not tree-sitter language ids; kakehashi matches
language ids (c, cpp, objc, objcpp, cuda).

### §5.2 `languages`

- `[languages._] autoInstall = true` (modern form; the top-level
  `autoInstall` is deprecated).
- `bridge._self.enabled = true` for go, javascript, lua, python, rust,
  toml, typescript (the nvim `host_bridge_languages` set).
- `languages.markdown.bridge`: lua→`["emmylua_ls"]`,
  python completion→`["pyright"]` `maxFanOut = 1`,
  rust→`["rust_analyzer"]`, typescript/javascript completion→
  `["vtsls", "denols"]` `maxFanOut = 1` (mirrors
  `vimrc/kakehashi_config.lua::languages()`).
- `languages.rmd` / `languages.quarto` → `base = "markdown"`.
- dpp is intentionally absent: it is nvim-specific (custom parser path in
  the nvim config dir, pushed via nvim `init_options`).

### §5.3 Inventory changes

- `dot_config/mise/config.toml`: `"cargo:emmylua_ls" = "latest" # emmylua_ls
  (Rust EmmyLua analyzer; binary: emmylua_ls)` replaces the aqua LuaLS
  entry; the section comment names all three sync targets
  (`bridged_servers` in the nvim config, `languageServers` in
  `dot_config/kakehashi/kakehashi.toml`).
- `dependencies/packages.toml`: `rust-analyzer` (paru, layer 4,
  official-extra prebuilt); kakehashi `has_configs = true` with a
  `# ~/.config/kakehashi/kakehashi.toml` comment.
- `make gen-deps` regenerates `dependencies/layer_4/paru.txt` and the
  spec 02 AUTO-GEN block.

### §5.4 Verification (all executed 2026-08-04)

- Deserialization + inventory: `make gen-deps` idempotent; pytest suite
  `41 passed` (venv at `/tmp/pytest-venv`; host has no pytest).
- Resolution: `command -v` over all eight `cmd[0]` with mise shims
  prepended — all resolve (6 shims + `/usr/sbin/rust-analyzer` +
  `/usr/sbin/clangd`).
- `kakehashi diagnose` / `format --check` on a Python-fenced Markdown file
  exit 0 (bridge spawns pyright; CLI one-shot returns 0 because the pull
  races pyright's async analysis — `pulls_answered=0` in metrics).
- End-to-end LSP pull with **only the user config**
  (`nvim --headless`, `vim.lsp.config('kakehashi', {cmd={'kakehashi'}})`,
  no init_options): broken Python → 3 pyright errors; broken Lua → 2
  emmylua_ls errors + 1 hint.
- Host: `paru -S rust-analyzer`; `rm ~/.local/share/cargo/bin/rust-analyzer`;
  `command -v rust-analyzer` → `/usr/sbin/rust-analyzer`;
  `rust-analyzer --version` → `rust-analyzer 1 (7ea2b259ca 2026-06-07)`.
- `chezmoi apply` (with `--force` for `dot_config/mise/config.toml`,
  whose local copy was rewritten by an independent nvim-config agent
  session at 07:41–08:22; the only remaining delta was this design's
  comment extension) → `~/.config/kakehashi/kakehashi.toml` installed.

## §6 Error handling and rollback

Host install failure is reversible: `paru -R rust-analyzer` restores the
prior state; the stale proxy can be restored by reinstalling the rustup
toolchain (or `rustup component add rust-analyzer`, which changes the
installation strategy — that is the rollback for the proxy *removal*
specifically, not for the paru choice). Repo changes roll back by reverting
the commits; `make gen-deps` is regenerable. If the kakehashi config were
rejected by a newer kakehashi, the failure is loud (CLI exit 2 / LSP
`RequestFailed`), and the file is chezmoi-revertible.

## §7 Risks / edge cases

- **rustup regenerates the proxy.** rustup creates proxies only for
  installed components; the observed proxy predates the minimal-profile
  state and is component-less. `command -v rust-analyzer` re-checked after
  the install resolves `/usr/sbin`; if a future rustup run recreates the
  proxy, removing it again restores the system binary.
- **`emmylua` settings namespace.** The nvim config pushes settings under
  `emmylua` (EmmyLuaLs fork); `cargo:emmylua_ls` is that fork, so the
  namespace now matches the binary (previously mismatched with LuaLS).
- **clangd inert in nvim.** kakehashi does not attach to C/C++ buffers in
  nvim (not in the nvim `filetypes()` list); the entry serves other
  editors and the CLI only. Deliberate.
- **Container parity.** The container installs the same mise tools
  (Layer 3-4, incl. `cargo:emmylua_ls`) and rust-analyzer (Layer 4 `aur`
  stage, extra repo). Its minimal-profile rustup creates no rust-analyzer
  proxy, so `/usr/bin` resolves there; confirmed on the next container
  build, not by this change.
- **Concurrent agent edits.** The nvim-config agent session was (and may
  remain) active during this work; the mise config and shim state on the
  host changed mid-flight (07:41–08:22). This design follows the final
  host state; the repo now matches it.
- **Moving upstream schema.** kakehashi 0.9.0 keys (`workspaceMarkers`,
  `languages.*.autoInstall`, `bridge._self`) are current per upstream
  docs; a future rename fails loudly (unknown keys are warned, `features`
  keys are fatal) rather than silently.

## §8 Open questions

- **Q1 (resolved — install source):** rust-analyzer via paru (official
  `extra` prebuilt), per user choice.
- **Q2 (resolved — emmylua_ls source):** `cargo:emmylua_ls`, per user
  choice (matches host state set by the nvim-config agent session).
- **Q3 (resolved — spec 20):** `I-KAKEHASHI6` narrowed to the final-image
  property, user-approved.

## §9 Review pass-1 responses

Reviews:
[`2026-08-04-kakehashi-global-config-review-pass1-A-factual.md`](../../reviews/2026-08-04-kakehashi-global-config-review-pass1-A-factual.md),
[`2026-08-04-kakehashi-global-config-review-pass1-D-consistency.md`](../../reviews/2026-08-04-kakehashi-global-config-review-pass1-D-consistency.md).

- **A-F1 (workspaceMarkers semantics):** addressed — §5.1 now transcribes
  lspconfig lists as-is, with the `vim.fs.root` source (`M.root` iterates
  top-level entries in order) cited; pyright/tombi/clangd flat, denols/
  vtsls/emmylua nested, gopls priority chain; rust_analyzer approximation
  documented.
- **A-F2 (eight-server readiness / verification):** addressed — §5.4
  records `command -v` for all eight, the headless-nvim LSP pull tests
  (pyright, emmylua_ls) and the pytest suite; the config-sync test is now
  a server→provider mapping (I-KC2), not equality.
- **A-F3 (spec 24 justification):** addressed — §2 alternative C cites
  spec 02's `paru` Layer-4 rule instead and states spec 24 is
  inapplicable (no rust toolchain dependency).
- **A-F4 (rustup proxy claim):** addressed — §3 I-KC3 and §7 describe the
  proxy as observed host state without asserting "component never
  installed"; §6 distinguishes proxy-removal rollback from strategy
  change.
- **A-F5 (clangd doxygen filetypes):** addressed — §5.1 documents the
  exclusion (nvim filetypes vs tree-sitter language ids).
- **A-F6 (mise delta already tracked):** addressed — §1 S2 and §4 record
  the user's `94f5556` commit; the actual delta is the aqua→cargo switch
  plus the comment extension.
- **D-F1 (I-KC2 equality):** addressed — I-KC2 and
  `test_kakehashi_config_sync.py` define the explicit server→provider
  mapping and the intentional nvim subset.
- **D-F2 (spec 24):** addressed — same fix as A-F3.
- **D-F3 (I-KAKEHASHI6 conflict):** addressed — spec 20 I-KAKEHASHI6
  narrowed to the final-image property, explicitly allowing build-prepass
  scratch rendering (verified against the Containerfile pre-pass flow);
  user-approved.
- **D-F4 (link conventions):** addressed — repo-relative links for
  internal docs; upstream docs cited by URL.
- **D-F5 (mise delta):** addressed — same fix as A-F6.
