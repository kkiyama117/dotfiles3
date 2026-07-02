# Set up cargo install (cargo-binstall bootstrap + Rust packages rule)

**Date:** 2026-07-02
**Status:** open (design draft)
**Related:** [design](../specifications/implementations/2026-07-02-cargo-install-design.md), [spec 02](../specifications/02-installed-programs.md), [spec 20](../specifications/20-container-rules.md), [spec 21](../specifications/21-container-build-flow.md), [current host cargo inventory](../references/current_cargo_installed.md), [mise-managed-languages sibling (closed)](2026-07-01-mise-managed-languages.md)

## Context

- The Rust toolchain is already installed in the build: Containerfile
  Layer 3-2 installs **rustup** (`stable` / `profile=minimal`) via the
  upstream installer, so `cargo` is present. `GNUPGHOME` analog:
  `CARGO_HOME` / `RUSTUP_HOME` resolve to `~/.local/share/{cargo,rustup}`
  (`dot_zshenv.tmpl`), backed by the `dotfiles_cargo` / `dotfiles_rustup`
  Podman named volumes (persisted across `make down && make up`,
  destroyed by `make clean`). The `manager = "cargo"` manager is already
  wired in the generator (`LIST_MANAGERS`) and emits
  `dependencies/layer_3/cargo.txt`, which Containerfile Layer 3-4
  consumes via `cargo install --locked`. **Currently `cargo.txt` is
  empty (0 packages)** — the install step is a no-op.
- Two TODOs in `dependencies/packages.toml` are unresolved:
  1. "Write this `Rust packages rule` into docs" — the policy for when
     to install a Rust-depend package via `paru` (AUR prebuilt, no
     rust-toolchain dep, stable) vs `cargo-binstall` (prebuilt binary,
     wants latest) vs `cargo install --locked` (source-only / beta /
     latest-from-source).
  2. "Install `cargo-binstall`, and install other `cargo` packages via
     `cargo-binstall`. Only `cargo-binstall` (or maybe `topgrade`) is
     installed in Containerfile and cached; other packages are installed
     after the container is built, by the user manually (they may need
     beta/latest/source builds, which are too slow and done daily)."
- `docs/references/current_cargo_installed.md` lists the operator's
  current host cargo inventory (~30 packages, including
  `cargo-binstall`, `topgrade`, `cargo-audit`, `cargo-edit`,
  `cargo-expand`, `cargo-zigbuild`, `maturin`, `tauri-cli`, `wasm-pack`,
  `zellij`, `mdbook`, ...).

## Problem

1. Give the container a working **`cargo-binstall`** so the operator can
   install cargo tools at runtime from prebuilt binaries (fast, no
   source compile), without baking every cargo tool into the image.
2. Install **one** build-time cargo tool — `topgrade` — so the container
   boots with the multi-package-manager updater available immediately
   (the operator can run `topgrade` to refresh the whole environment,
   including any cargo tools they install at runtime).
3. Establish a **declarative home in `packages.toml`** for cargo tools
   that are *not* build-installed (the runtime-manual set), so
   `packages.toml` is the single source of truth for *which* cargo
   tools the operator wants — without the build installing them. This
   needs a new toml mechanism to mark "declared but not installed in
   layer 3."
4. Write the **Rust packages rule** as a proper spec (resolving TODO #1
   above): the paru / cargo-binstall / cargo-install selection criteria
   and the build-time / runtime-manual boundary.

## Acceptance criteria

1. `cargo-binstall` is bootstrapped at **build time** in the
   Containerfile `toolchain` stage as **infrastructure** (prebuilt
   binary, NOT a `packages.toml` entry — same category as `rustup` /
   `mise`, which are curl-bootstrapped and not in `packages.toml`).
   After `make build && make up`, `podman exec dotfiles-manjaro zsh -ic
   'cargo binstall -V'` prints a version.
2. `topgrade` is declared in `dependencies/packages.toml` with
   `manager = "cargo"`, `layer = 3`, `has_configs = false`; `make
   gen-deps` emits it to `dependencies/layer_3/cargo.txt`. The
   Containerfile installs it via **`cargo binstall --only-signed -y`** (not
   `cargo install --locked`), using the bootstrapped binstall. After
   `make up`, `podman exec dotfiles-manjaro zsh -ic 'which topgrade'`
   resolves (or `topgrade -V` succeeds).
3. A **new layer number `layer = 6`** is introduced as the
   **runtime-manual** layer: cargo entries with `layer = 6` are emitted
   by the generator to `dependencies/layer_6/cargo.txt` as a
   **reference list** (NOT consumed by any Containerfile build stage —
   the build only reads `layer_3`). The generator needs no functional
   change for this (it already emits `layer_<N>/<manager>.txt` for any
   `layer >= 1`); only the spec 02 AUTO-GEN heading for layer 6 is
   special-cased to read "Layer 6 — runtime-manual (not
   build-installed)" (mirroring the existing layer-0 "already in the
   base image" special case). `schema` stays at 1.
4. The runtime-manual cargo set is declared in `packages.toml` at
   `layer = 6`: `cargo-outdated`, `cargo-expand`, `cargo-edit`,
   `cargo-zigbuild`, `maturin`. `make gen-deps` emits
   `layer_6/cargo.txt` listing them (reference only). The Containerfile
   does **not** read `layer_6/cargo.txt`.
5. The Containerfile `toolchain` sub-layer ordering is updated to:
   `3-2 rustup` → `3-3 mise binary` → `3-4 mise install languages`
   (moved up from 3-5) → `3-5 cargo-binstall bootstrap` (new) →
   `3-6 cargo tools via cargo binstall` (was 3-4, command switched from
   `cargo install --locked` to `cargo binstall --only-signed -y`, renumbered).
   An empty `layer_3/cargo.txt` still does not break the build (the
   `if [ -n "$pkgs" ]` guard + `(3, "cargo")` in `EXPECTED_EMPTY_FILES`
   preserved).
6. `make down && make up` preserves cargo / rustup toolchain binaries
   (the `dotfiles_cargo` / `dotfiles_rustup` named volumes persist —
   regression check of the existing behavior). **Rollout (E-F2):** because
   `cargo-binstall` and `topgrade` are NEW entries in `$CARGO_HOME/bin`, an
   existing `dotfiles_cargo` named volume will NOT pick them up on `make up`
   (Podman does not re-populate a non-empty volume); run `make clean` (or
   `podman volume rm dotfiles_cargo`) before the first `make up` after this
   change.
7. `programs/generate_deps/tests/` is green (existing
   `test_cargo_manager.py` + any new/updated tests for the layer-6
   runtime-manual heading and the layer-6 emission).
8. Specs updated: new **`docs/specifications/24-rust-packages-rule.md`**
   (the Rust packages rule: paru vs cargo-binstall vs cargo-install;
   build-time vs runtime-manual; `cargo-binstall` = infra exception;
   `layer = 6` = runtime-manual convention);
   [`02-installed-programs.md`](../specifications/02-installed-programs.md)
   (cargo manager rule + layer-6 note);
   [`20-container-rules.md`](../specifications/20-container-rules.md)
   (a general `I-INFRA1` installer-infra carve-out + `I-CARGO1` as its cargo
   instance, or cross-ref to spec 24);
   [`21-container-build-flow.md`](../specifications/21-container-build-flow.md)
   (Stage 3 rows 3-4/3-5/3-6 + acceptance criteria for binstall/topgrade).
9. No secret is baked into any image layer (extends I4 / spec 13 I-S4 —
   unchanged; cargo-binstall and cargo tools are public binaries fetched
   over HTTPS, no credentials involved).

## Notes

- **`cargo-binstall` is infrastructure, not a `packages.toml` tool.**
  Like `rustup` (Layer 3-2) and `mise` (Layer 3-3), it is the *installer*
  for the rest of the cargo ecosystem and is curl-bootstrapped from a
  prebuilt binary. Putting it in `packages.toml` and compiling it via
  `cargo install --locked cargo-binstall` would defeat its own purpose
  (binstall exists to avoid source compiles). It is therefore a
  Containerfile bootstrap, outside the `packages.toml` SoT, with the
  same precedent as rustup/mise.
- **Build-time vs runtime-manual split.** `layer = 3` cargo entries are
  build-installed (via `cargo binstall`, prebuilt only). `layer = 6`
  cargo entries are *declared for reference* and installed by the
  operator at runtime via `cargo binstall <pkg>` (or `cargo install
  --locked` for source/beta). The broader curated-set build-install
  (bulk-importing the rest of `current_cargo_installed.md` into the
  build) is a **separate future issue** (deferred, not this one).
- **`layer = 6` rationale.** Build stages are 0-5 (0 base, 1 pacman, 2
  prepass, 3 toolchain, 4 aur, 5 runtime-final). Layer 6 reads as
  "post-final-image / runtime" — there is no Containerfile stage 6, so
  a `layer_6/<mgr>.txt` is naturally a non-build reference list. The
  generator already emits `layer_<N>/<manager>.txt` for any `layer >= 1`
  with entries, so this needs no functional generator change.
- **Why swap mise-languages before cargo-binstall.** Operator
  preference: group the mise sub-layers (binary + languages) at 3-3/3-4
  and the cargo sub-layers (binstall + tools) at 3-5/3-6. No build
  dependency forces either order; the reorder is cosmetic and keeps the
  two ecosystems as contiguous blocks.

## Status update (2026-07-02)

Design drafted at
[`../specifications/implementations/2026-07-02-cargo-install-design.md`](../specifications/implementations/2026-07-02-cargo-install-design.md).
Pending review pass (security/build letters per
[`09-review.md`](../specifications/09-review.md)) before implementation.