# mise-Managed Languages (go / python / deno) Install Layer — Design

**Status:** DRAFT
**Date opened:** 2026-07-01
**Issue:** [`docs/issues/2026-07-01-mise-managed-languages.md`](../../issues/2026-07-01-mise-managed-languages.md)
**Author:** kiyama

## §1 Context & success criteria

The container's `toolchain` stage (Containerfile Layer 3-3, see
[spec 21](../21-container-build-flow.md)) installs the **mise binary**
(`curl https://mise.run | sh`) and `dot_zshenv.tmpl` activates mise
shims at runtime (`eval "$(mise activate zsh --shims)"` with
`MISE_DATA_DIR=$XDG_DATA_HOME/mise`). Layer 1-5 provisions the
`~/.local/share/mise` mountpoint and the Makefile mounts the
`dotfiles_mise` named volume there — the same persistence pattern used
for cargo / rustup. But **no step installs any mise-managed language**,
so the shims resolve to nothing.

`mise` is currently a **doc-only manager** in
`programs/generate_deps/main.py` (`DOC_ONLY_MANAGERS = ("mise",
"custom")`): `packages.toml` entries with `manager = "mise"` appear only
in the spec 02 AUTO-GEN block and produce **no** `layer_<N>/mise.txt`.
There is no generated list the Containerfile could consume, hence no
install path.

- **S1:** `go`, `python`, `deno` are declared in
  `dependencies/packages.toml` with `manager = "mise"`, `layer = 3`,
  `has_configs = false`; `make gen-deps` regenerates the spec 02 AUTO-GEN
  block and emits `dependencies/layer_3/mise.txt`.
- **S2:** `mise` is moved from `DOC_ONLY_MANAGERS` to `LIST_MANAGERS`
  in `programs/generate_deps/main.py`; the mise rendering emits one
  `<name>@latest` line per tool (bare `mise install <tool>` reads a
  `mise.toml`, not latest, so the `@latest` suffix is required).
- **S3:** The Containerfile `toolchain` stage gains a sub-layer 3-5
  that runs `mise install` reading `layer_3/mise.txt`; tools land in
  `~/.local/share/mise` (the `dotfiles_mise` named-volume mountpoint),
  copy-on-first-mount into the volume on `make up` (analog of spec 21
  acceptance #8).
- **S4:** After `make up`, `podman exec dotfiles-manjaro zsh -ic
  'go version; python --version; deno --version'` prints a version for
  each (shims active via `dot_zshenv.tmpl`).
- **S5:** `make down && make up` preserves the installed languages (the
  `dotfiles_mise` named volume persists).
- **S6:** An empty mise list does not break the build (the Containerfile
  `if [ -n "$pkgs" ]` guard + `(3, "mise")` in the generator's
  `EXPECTED_EMPTY_FILES`, mirroring the cargo/paru empty-list policy).
- **S7:** `programs/generate_deps/tests/` is green with a new
  `test_mise_manager.py`; `test_custom_manager.py` is updated (its
  "`custom` behaves like `mise`: doc-only" premise is now obsolete).
- **S8:** Specs 02 (mise manager rule) and 21 (Layer 3-5 row + acceptance
  criterion) are updated.

## §2 Alternatives considered

- **A1 — Make `mise` a list manager, mirroring pacman/paru/cargo
  (chosen).** Move `mise` into `LIST_MANAGERS`; the generator emits
  `layer_3/mise.txt` (one `<name>@latest` per line); the Containerfile
  installs from it in the `toolchain` stage. Keeps `packages.toml` the
  single hand-edited SoT (invariant I-FS3) and reuses the exact pattern
  already proven for pacman / paru / cargo. Cost: a small generator
  change (mise special-case rendering for `@latest` + moving it between
  the two manager tuples + `EXPECTED_EMPTY_FILES`).
- **A2 — Add a chezmoi-managed `mise.toml` config** (e.g.
  `dot_config/mise/config.toml` with a `[tools]` section listing
  `go = "latest"`, etc.) and have the `toolchain` stage run `mise install`
  reading it (the build-prepass already renders chezmoi to
  `/tmp/build-home`). This is the *idiomatic mise* way, but creates a
  **dual SoT** (`packages.toml` doc-only + `mise.toml` executable) that
  can drift, and goes against I-FS3 ("`packages.toml` is the only
  hand-edited package manifest"). Rejected.
- **A3 — Hand-write the go/python/deno list inline in the Containerfile.**
  Simplest, but breaks single-SoT the hardest and is the easiest to let
  drift from `packages.toml`. Rejected.
- **A4 — Keep `mise` doc-only and pass the tool list via build-args /
  ENV.** Fragile, non-declarative, and against the repo's SoT
  philosophy. Rejected.

## §3 Architecture / Invariants

- **I1 (single SoT preserved):** `dependencies/packages.toml` remains
  the only hand-edited package manifest; `layer_3/mise.txt` is generated
  (I-FS3). The mise tool *list* and the *doc* both derive from
  `packages.toml` — no parallel `mise.toml`.
- **I2 (list-manager symmetry):** `mise` joins `pacman` / `paru` /
  `nix` / `uv` / `cargo` as a list manager. The only mise-specific quirk
  is the `@latest` suffix in the rendered line (because bare
  `mise install <tool>` reads a `mise.toml`, not latest — verified via
  `mise install --help`).
- **I3 (persistence parity):** mise-managed languages install into
  `MISE_DATA_DIR = ~/.local/share/mise`, which is the `dotfiles_mise`
  named-volume mountpoint. Build-time installs are baked in the image
  and copy-on-first-mount into the volume on the first `make up`,
  identical to the cargo / rustup pattern (spec 21 acceptance #8).
- **I4 (empty-list safety):** `(3, "mise")` is added to
  `EXPECTED_EMPTY_FILES` so the Containerfile's unconditional
  `COPY --from=deps layer_3/mise.txt` never breaks on an empty list;
  the `if [ -n "$pkgs" ]` guard skips the install. Mirrors the
  cargo/paru empty-list policy.
- **I5 (no new runtime entrypoint coupling):** the install happens at
  build time only. The runtime entrypoint (`container/bind/layer_5_files/
  entrypoint.sh`) is unchanged; mise shims are already activated by
  `dot_zshenv.tmpl`.
- **I6 (cache reuse):** the Layer 3-5 `RUN` carries a BuildKit
  `--mount=type=cache,target=/home/${USERNAME}/.cache/mise` so
  mise's download cache survives across rebuilds without bloating
  image layers (mirrors the cargo cache mounts in Layer 3-4).
- **I7 (global default for shims):** `mise install` alone sets no
  default version, so runtime shims error "No version is set for
  shim: <tool>". Layer 3-5 therefore runs `mise use -g ${=pkgs}`
  after `mise install` to write the global default config
  (`~/.config/mise/config.toml`, `[tools] ... = "latest"`). That
  config is a **derived build artifact** (driven by `layer_3/mise.txt`,
  itself derived from `packages.toml`) — NOT a parallel hand-edited
  `mise.toml` — so the single SoT (I1) is preserved. It rides the
  stage chain into the runtime image (Layer 5-3 strips chezmoi's toml
  + bash remnants, NOT `~/.config/mise`). Verified empirically.

## §4 Scope / staging breakdown

Single feature, four edits + two spec updates, each independently
verifiable:

1. **Generator** — `programs/generate_deps/main.py`: move `mise` into
   `LIST_MANAGERS`, special-case rendering (`<name>@latest`), add
   `(3, "mise")` to `EXPECTED_EMPTY_FILES`, fix stale comments.
2. **SoT** — `dependencies/packages.toml`: add the three `[[tool]]`
   entries (go / python / deno, layer 3).
3. **Containerfile** — `container/Containerfile`: add Layer 3-5
   (`COPY --from=deps layer_3/mise.txt` + `mise install` with cache
   mount), after Layer 3-4 (cargo).
4. **Tests** — new `test_mise_manager.py`; update `test_custom_manager.py`.
5. **Specs** — `02-installed-programs.md` (mise manager rule) and
   `21-container-build-flow.md` (Layer 3-5 row + acceptance).
6. **Regen** — `make gen-deps` to materialize `layer_3/mise.txt` and
   refresh the spec 02 AUTO-GEN block.

## §5 Implementation detail

### 5.1 `dependencies/packages.toml` (new entries)

```toml
# Layer 3: mise-managed languages (Containerfile `toolchain` stage, Layer 3-5).
# Add `[[tool]]` entries with `manager = "mise"` and `layer = 3`.
# Run `make gen-deps` to regenerate `dependencies/layer_3/mise.txt`
# (one `<name>@latest` per line; mise is now a list manager).
[[tool]]
name = "go"
manager = "mise"
layer = 3
has_configs = false
description = "Go programming language (mise-managed, latest)"

[[tool]]
name = "python"
manager = "mise"
layer = 3
has_configs = false
description = "CPython (mise-managed, latest)"

[[tool]]
name = "deno"
manager = "mise"
layer = 3
has_configs = false
description = "Deno runtime (mise-managed, latest)"
```

### 5.2 `programs/generate_deps/main.py`

- Module docstring: replace "mise (version-pinned, not list-based)
  produce no txt" with "`mise` produces `layer_<N>/mise.txt` with one
  `<name>@latest` per line".
- `LIST_MANAGERS = ("pacman", "paru", "nix", "uv", "cargo", "mise")`
- `DOC_ONLY_MANAGERS = ("custom",)`
- `EXPECTED_EMPTY_FILES: tuple[tuple[int, str], ...] = ((3, "cargo"),
  (4, "paru"), (3, "mise"))`
- In `render_packages_txt`, when `manager == "mise"`, emit
  `f"{name}@latest"` (with the inline `# description` comment retained).
  All other managers keep bare `name`. The doc-block renderer
  (`render_doc_block`) is unchanged (it shows `name`, not the version
  suffix — the version is an install-detail, not an inventory fact).

### 5.3 `container/Containerfile` (new Layer 3-5)

Inserted in the `toolchain` stage, after Layer 3-4 (cargo install):

```dockerfile
# Layer 3-5: install mise-managed languages from the generated list.
#
# `dependencies/` is outside the container/ build context, so it is
# exposed via the named BuildKit context `deps` (see Makefile) and read
# with `COPY --from=deps`. Comments and blank lines are stripped before
# `mise install`. The list contains only `manager = "mise"` entries,
# rendered as `<name>@latest` (bare `mise install <tool>` would read a
# mise.toml instead of latest, so the @latest suffix is required).
# `mise` is on PATH via ~/.local/bin (set in .zshenv); MISE_DATA_DIR is
# sourced from /tmp/build-home/.zshenv. Tools install into
# ~/.local/share/mise (the dotfiles_mise named-volume mountpoint), so
# they copy-on-first-mount into the volume on the first `make up`
# (spec 21 acceptance #8 analog). A BuildKit cache mount on
# ~/.cache/mise keeps mise's download cache across rebuilds without
# bloating image layers (mirrors the cargo cache mounts in 3-4).
# `${=pkgs}` (zsh split) restores per-package args.
COPY --from=deps layer_3/mise.txt /tmp/mise_tools.txt
RUN --mount=type=cache,target=/home/${USERNAME}/.cache/mise,uid=${HOST_UID},gid=${HOST_GID} \
    zsh -c 'set -eo pipefail; \
      source /tmp/build-home/.zshenv; \
      pkgs=$(sed "s/#.*//" /tmp/mise_tools.txt | xargs); \
      if [ -n "$pkgs" ]; then \
        mise install ${=pkgs}; \
        mise use -g ${=pkgs}; \
      else \
        echo "toolchain: mise install list is empty -- skipping"; \
      fi; \
    '
```

`mise use -g` is required alongside `mise install`: `mise install` alone
sets no default version, so the shims error "No version is set for
shim: <tool>" at runtime (verified). `mise use -g ${=pkgs}` writes the
global default config (`~/.config/mise/config.toml`, `[tools] ... =
"latest"`), which rides the stage chain into the runtime image (Layer 5-3
strips chezmoi's toml + bash remnants, NOT `~/.config/mise`) and lets the
shims resolve at runtime. The config is a derived build artifact (driven
by the same `layer_3/mise.txt`), not a parallel hand-edited `mise.toml`,
so the single SoT (`packages.toml`) is preserved.

### 5.4 Tests

New `programs/generate_deps/tests/test_mise_manager.py`:

- `assert "mise" in main.LIST_MANAGERS`
- `assert "mise" not in main.DOC_ONLY_MANAGERS`
- `test_validate_accepts_mise` (a mise entry validates)
- `test_mise_entry_emits_at_latest_txt`: a layer-3 mise entry produces
  `layer_3/mise.txt` whose non-comment lines are `<name>@latest`
  (isolate `EXPECTED_EMPTY_FILES` via monkeypatch for determinism)
- `test_mise_expected_empty_file`: with no mise entries, `layer_3/mise.txt`
  is still emitted (empty) because of `(3, "mise")`
- `test_mise_entry_rendered_in_doc_block`: the doc block includes the
  mise rows (and shows `name`, not `name@latest`)

Update `programs/generate_deps/tests/test_custom_manager.py`:

- Replace the docstring clause "`custom` behaves like `mise`: doc-only,
  no .txt emitted" with "`custom` is doc-only, no .txt emitted (mise is
  now a list manager; see test_mise_manager.py)".
- Remove / adjust any assertion that paired `mise` with `custom` in
  `DOC_ONLY_MANAGERS` (there is none beyond the docstring today, but
  audit before editing).

### 5.5 Spec updates

- `docs/specifications/02-installed-programs.md` — two edits:
  1. The "Source of truth" intro enumerates list managers as
     `pacman`/`paru`/`nix`/`uv`/`cargo`; add `mise` so the enumeration
     matches the new reality.
  2. Rewrite the `mise` bullet under "manager rules":
     > `mise`: list-based manager for programming languages and tools
     > except `Rust`. Emits `dependencies/layer_<N>/mise.txt` (one
     > `<name>@latest` per line) and is installed in the `toolchain` stage
     > (Layer 3-5). Bare `mise install <tool>` reads a `mise.toml`, not
     > latest, so the generator appends `@latest`.
- `docs/specifications/21-container-build-flow.md` — add a Layer 3-5 row
  to the stage table (`toolchain` stage; `COPY --from=deps layer_3/mise.txt`
  + `mise install` with `~/.cache/mise` cache mount; inputs:
  `/tmp/build-home/.zshenv`, `dependencies/layer_3/mise.txt`) and a new
  acceptance criterion: after `make up`, `go version` / `python --version`
  / `deno --version` succeed via shims; `make down && make up` preserves
  them (named-volume persistence).

## §6 Verification

1. `make gen-deps` is idempotent and produces `layer_3/mise.txt`
   containing `go@latest`, `python@latest`, `deno@latest`; the spec 02
   AUTO-GEN block lists the three under Layer 3.
2. `pytest programs/generate_deps/tests/` is green (existing 15 tests +
   new mise tests).
3. `podman build --target toolchain` succeeds in isolation and the
   resulting image has `mise`, `go`, `python`, `deno` under
   `~/.local/share/mise/installs`.
4. `make build` (full) succeeds.
5. `make up && podman exec dotfiles-manjaro zsh -ic
   'go version; python --version; deno --version'` prints a version for
   each.
6. `make down && make up && podman exec dotfiles-manjaro zsh -ic
   'go version'` still prints (named-volume persistence, S5).

## §7 Open questions

- **Q1 (per-tool version pinning):** the current design hardcodes
  `@latest` for every mise tool. Future per-tool pinning (e.g.
  `python = "3.14"`, `go = "1.26.4"`) would need an optional `version`
  field in `packages.toml` and generator logic to emit
  `<name>@<version>`. Deferred — the design dialogue chose `latest` for
  all three.
- **Q2 (XDG-ization + chezmoi config templating):** go env
  (`GOPATH` / `GOPROXY` / `GOMODCACHE`), python (`PIP_CACHE_DIR` / `UV`),
  and deno (`DENO_DIR`) are not XDG-ized and not templated under
  chezmoi (`has_configs = false` for all three). Not requested; tracked
  as a future phase if a tool's config needs to be managed.