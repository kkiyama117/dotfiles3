# Add a global kakehashi configuration

**Date:** 2026-08-04
**Status:** closed (see [result-log](2026-08-04-phase-kakehashi-global-config.md))
**Related:** [design](../specifications/implementations/2026-08-04-kakehashi-global-config-design.md), spec 02, spec 24

## Context

[`kakehashi`](https://github.com/atusy/kakehashi) v0.9.0 is installed on the
host (`~/.local/bin/kakehashi`) and in the container (Layer 3-8, see
[2026-07-16-kakehashi-container-install.md](2026-07-16-kakehashi-container-install.md)).
Until now it has only been configured editor-side: nvim pushes
`languageServers` + `languages` via `init_options` and a runtime
`didChangeConfiguration` (nvim config `lua/vimrc/kakehashi_config.lua` +
`lua/vimrc/kakehashi_bridge.lua`). There is no
`~/.config/kakehashi/kakehashi.toml`, so other editors and the `kakehashi
format` / `kakehashi diagnose` CLIs run on programmed defaults with no
bridge servers.

Almost all LSP servers are installed via `mise`
(`dot_config/mise/config.toml`: gopls, pyright, vtsls, lua-language-server,
tombi, deno) or via pacman/paru (clangd from `clang`).

Two discovered problems:

1. nvim-lspconfig's `emmylua_ls` `cmd` is `["emmylua_ls"]`, but only
   `lua-language-server` exists (mise aqua:LuaLS/lua-language-server); the
   nvim bridge's `exepath()` fallback keeps the unresolvable name, so the
   emmylua bridge cannot spawn.
2. `~/.local/share/cargo/bin/rust-analyzer` is a stale rustup proxy
   (symlink to `rustup`); the rust-analyzer component is not installed, so
   running it fails with "Unknown binary 'rust-analyzer'". The rustup
   toolchain profile is minimal and the component was never added.

## Problem

Provide a global kakehashi user config that declares the LSP-server catalog
once (editor-agnostic), and make every declared server actually resolvable
on the host and in the container.

## Acceptance criteria

1. `dot_config/kakehashi/kakehashi.toml` exists, loads without error
   (`kakehashi --config-file … diagnose/format` exit 0 on a Markdown file
   with a Python fence, with mise shims on PATH), and declares
   `languageServers` for denols, emmylua_ls, gopls, pyright, rust_analyzer,
   tombi, vtsls, clangd with bare-command `cmd`s.
2. `languages` mirrors the nvim bridge contract: `bridge._self` host
   bridging for go/javascript/lua/python/rust/toml/typescript, markdown
   injection bridges (lua→emmylua_ls, python→pyright, rust→rust_analyzer,
   typescript/javascript→vtsls+denols), rmd/quarto `base = "markdown"`.
3. `dot_config/mise/config.toml` syncs the already-present local LSP tool
   entries into the repo; `rust-analyzer` is declared in
   `dependencies/packages.toml` as `manager = "paru"`, `layer = 4`
   (official `extra` repo prebuilt, per user choice over mise/cargo).
4. `make gen-deps` regenerates spec 02 (kakehashi `has_configs` flips to
   `yes`; new Layer 4 rust-analyzer row); `make test-deps` passes with the
   updated kakehashi tests plus a new config-sync regression test.
5. Host: `paru -S rust-analyzer` installs `/usr/bin/rust-analyzer`, the
   stale rustup proxy at `~/.local/share/cargo/bin/rust-analyzer` is
   removed, and `command -v rust-analyzer` resolves to `/usr/bin/rust-analyzer`.
6. `chezmoi apply` places `~/.config/kakehashi/kakehashi.toml`; with mise
   shims on PATH, an LSP session using only the user config pulls real
   diagnostics (verified 2026-08-04: pyright 3 errors on a broken Python
   file; emmylua_ls 2 errors + 1 hint on a broken Lua file), and every
   declared server's `cmd[0]` resolves (`command -v`).

## Notes

- No Containerfile, Makefile, nvim-config, or spec 20/21 change is
  required: Layer 3-4 `mise install` and the Layer 4 `aur` stage pick up
  the inventory changes through `make gen-deps` alone.
- clangd is included even though nvim never attaches kakehashi to C/C++
  buffers (not in `vimrc.kakehashi_config` filetypes); it serves other
  editors and the kakehashi CLI. It can be dropped by removing one entry.
- The nvim-side `emmylua` settings namespace (`emmylua` vs `Lua`) is a
  pre-existing nvim concern, out of scope here.
