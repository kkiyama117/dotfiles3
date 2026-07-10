# nvim in container: E5113 "No parser for language lua" + unconsumed layer_4/pacman.txt

**Date:** 2026-07-10
**Status:** closed (fixed same day)
**Related:** [spec 02](../specifications/02-installed-programs.md),
[spec 21](../specifications/21-container-build-flow.md),
[nvim external config issue](2026-07-09-nvim-external-config.md)

## Problem

Opening any `*.lua` file with nvim inside the container raised:

```text
Error in BufReadPost Autocommands for "*":
…/usr/share/nvim/runtime/ftplugin/lua.lua: Vim(runtime):E5113: Lua chunk:
…/vim/treesitter.lua:460: Parser could not be created for buffer 1 and
language "lua": …/languagetree.lua:133: No parser for language "lua"
```

## Root cause

Two stacked causes:

1. **`neovim-git` (AUR) ships no tree-sitter grammars.** Nvim 0.12+
   built-in ftplugins (`lua`, `c`, `markdown`, `vim`, `vimdoc`, `query`)
   call `vim.treesitter.start()` unconditionally. The official `neovim`
   pacman package depends on `tree-sitter-c tree-sitter-lua
   tree-sitter-markdown tree-sitter-query tree-sitter-vim
   tree-sitter-vimdoc`, but `neovim-git` declares none of them and ships
   an **empty** `/usr/lib/nvim/parser/` directory, so every default
   ftplugin `vim.treesitter.start()` errors.
2. **`dependencies/layer_4/pacman.txt` was generated but never consumed.**
   The Containerfile `aur` stage only read `layer_4/paru.txt`; the
   `manager = "pacman"`, `layer = 4` entries (previously just `rsync`)
   were silently never installed (verified: `pacman -Qi rsync` failed in
   the running container). Convention clarified while fixing this:
   `pacman` entries install at Layer 1 only; everything installed at
   Layer 4 goes through `paru` (which also handles official repo
   packages), so a `layer_4/pacman.txt` must never exist.

## Fix

1. `dependencies/packages.toml`: declare the six `tree-sitter-*` grammar
   packages (`manager = "paru"`, `layer = 4`, alongside `neovim-git`) and
   flip the dormant `rsync` entry from `pacman` to `paru`; `make
   gen-deps` regenerates `layer_4/paru.txt` and deletes the
   never-consumed `layer_4/pacman.txt`.
2. No Containerfile change needed: the existing Layer 4-2 `paru -S`
   bulk install consumes `layer_4/paru.txt` (paru installs official repo
   packages too). An interim Layer 4-2 `pacman` step was prototyped and
   reverted in favor of this approach.
3. Spec 02 `paru` manager rule wording clarified (paru also carries
   official-repo packages that belong to Layer 4).

## Verification

- Live container hot-fix: `pacman -S tree-sitter-{c,lua,markdown,query,vim,vimdoc} rsync`,
  then `nvim --clean --headless /tmp/test.lua +q` exits 0 with no E5113
  (grammar `.so` under `/usr/lib/tree_sitter/` is found by the nvim
  0.13-dev parser search path).
- `make gen-deps` regenerates `layer_4/paru.txt` with 21 packages and
  removes `layer_4/pacman.txt`.
- Next `make build` installs them via the existing Layer 4-2 `paru -S`
  bulk step (image-persistent fix).
