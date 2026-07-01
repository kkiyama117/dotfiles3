# Install go / python / deno via mise in the container

**Date:** 2026-07-01
**Status:** closed (see [result-log](2026-07-01-phase-mise-managed-languages.md))
**Related:** [design](../specifications/implementations/2026-07-01-mise-managed-languages-design.md), [plan](../plans/2026-07-01-mise-managed-languages-impl.md), [result-log](2026-07-01-phase-mise-managed-languages.md), [spec 02](../specifications/02-installed-programs.md), [spec 21](../specifications/21-container-build-flow.md)

## Context

- The container's `toolchain` stage (Containerfile Layer 3-3) installs the
  **mise binary** (`curl https://mise.run | sh`) and `dot_zshenv.tmpl`
  activates mise shims at runtime (`eval "$(mise activate zsh --shims)"`
  with `MISE_DATA_DIR=$XDG_DATA_HOME/mise`). Layer 1-5 provisions the
  `~/.local/share/mise` mountpoint and the Makefile mounts the
  `dotfiles_mise` named volume there (same persistence pattern as
  cargo/rustup).
- However **no step installs any mise-managed language**, so the shims
  resolve to nothing: `go` / `python` / `deno` are unavailable in the
  container despite mise being present.
- `mise` is currently a **doc-only manager** in
  `programs/generate_deps/main.py` (`DOC_ONLY_MANAGERS = ("mise", "custom")`):
  `packages.toml` entries with `manager = "mise"` appear only in the
  spec 02 AUTO-GEN block and produce **no** `layer_<N>/mise.txt`. There
  is therefore no generated list the Containerfile could consume.

## Problem

Give the container a working, persisted set of mise-managed languages
(go, python, deno) installed at build time and surfaced via the existing
mise shims at runtime — while keeping `dependencies/packages.toml` the
single hand-edited source of truth (invariant I-FS3) and matching the
existing pacman / paru / cargo generated-list pattern.

## Acceptance criteria

1. `go`, `python`, `deno` are declared in `dependencies/packages.toml`
   with `manager = "mise"`, `layer = 3`, `has_configs = false`.
2. `mise` becomes a **list manager** in
   `programs/generate_deps/main.py` (moved from `DOC_ONLY_MANAGERS` to
   `LIST_MANAGERS`); `make gen-deps` emits
   `dependencies/layer_3/mise.txt` with one `<name>@latest` line per tool.
3. The Containerfile `toolchain` stage gains a sub-layer (3-5) that runs
   `mise install` reading `layer_3/mise.txt`; tools land in
   `~/.local/share/mise` (the `dotfiles_mise` named-volume mountpoint).
4. After `make up`, `podman exec dotfiles-manjaro zsh -ic
   'go version; python --version; deno --version'` prints a version for
   each (shims active via `dot_zshenv.tmpl`).
5. `make down && make up` preserves the installed languages (the
   `dotfiles_mise` named volume persists; analog of spec 21 acceptance
   #8 for cargo/rustup).
6. An empty mise list does not break the build (the Containerfile
   `if [ -n "$pkgs" ]` guard + `(3, "mise")` in the generator's
   `EXPECTED_EMPTY_FILES`).
7. `programs/generate_deps/tests/` is green with a new
   `test_mise_manager.py` covering the list-based rendering + doc block;
   `test_custom_manager.py` is updated (its "behaves like mise: doc-only"
   premise is now obsolete).
8. Specs 02 (mise manager rule) and 21 (Layer 3-5 row + acceptance) are
   updated to record the new mechanism.

## Notes

- All three tools are pinned to `latest` (per design dialogue Q1 → A).
  The generator therefore emits `<name>@latest` per line; bare
  `mise install <tool>` reads a `mise.toml` and is **not** "latest", so
  the `@latest` suffix is required.
- Per-tool version pinning (non-`latest`) is out of scope (deferred open
  question Q1 in the design).
- go/python/deno XDG-ization + chezmoi config templating (GOPATH, DENO_DIR,
  pip/UV cache, etc.) is also deferred (open question Q2).