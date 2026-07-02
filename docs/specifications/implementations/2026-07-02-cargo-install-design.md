# Cargo install (cargo-binstall bootstrap + Rust packages rule) — Design

**Status:** DRAFT (revised after review pass-1; see [aggregate review](../../reviews/2026-07-02-cargo-install-review-pass1.md))
**Date opened:** 2026-07-02
**Issue:** [`docs/issues/2026-07-02-cargo-install.md`](../../issues/2026-07-02-cargo-install.md)
**Author:** kiyama

## §1 Context & success criteria

The Rust toolchain is already built: Containerfile Layer 3-2 installs
**rustup** (`stable`, `profile=minimal`) via the upstream installer, so
`cargo` is on PATH (`$CARGO_HOME/bin`, set by `dot_zshenv.tmpl`).
`CARGO_HOME` / `RUSTUP_HOME` resolve to `~/.local/share/{cargo,rustup}`,
backed by the `dotfiles_cargo` / `dotfiles_rustup` Podman named volumes
(persist across `make down && make up`, destroyed by `make clean`).
The `manager = "cargo"` generator path is already wired
(`LIST_MANAGERS` includes `"cargo"`) and emits
`dependencies/layer_3/cargo.txt`, which Containerfile Layer 3-4 consumes
via `cargo install --locked`. **`layer_3/cargo.txt` is currently empty**
(0 packages), so the cargo install step is a no-op today.

What is missing is the *policy and bootstrap* for cargo-installed tools:
no `cargo-binstall` exists in the image (so runtime cargo installs
compile from source — slow), the "Rust packages rule" is an unresolved
TODO in `packages.toml`, and there is no declarative home in
`packages.toml` for cargo tools the operator wants tracked but *not*
build-installed.

- **S1:** `cargo-binstall` is bootstrapped at build time in the
  Containerfile `toolchain` stage as **infrastructure** (prebuilt binary
  via the upstream installer / GitHub release, NOT a `packages.toml`
  entry — same category as `rustup` Layer 3-2 and `mise` Layer 3-3).
  `podman exec dotfiles-manjaro zsh -ic 'cargo binstall -V'` prints a
  version after `make build && make up`.
- **S2:** `topgrade` is declared in `dependencies/packages.toml`
  (`manager = "cargo"`, `layer = 3`, `has_configs = false`); `make
  gen-deps` emits it to `dependencies/layer_3/cargo.txt`. The
  Containerfile installs it via **`cargo binstall --only-signed -y`**
  (not `cargo install --locked`), using the bootstrapped binstall. `--only-signed`
  mandates a signed prebuilt source (B-F2: the review-suggested `--secure` flag
  does not exist; the correct flag is `--only-signed`). Verified: `topgrade` has
  a signed source (QuickInstall, sigstore-verified) so `--only-signed` succeeds
  and topgrade stays at layer 3. `podman exec dotfiles-manjaro zsh -ic
  'which topgrade'` resolves after `make up` (subject to the rollout note in S6).
- **S3:** A new **`layer = 6`** is the **runtime-manual** layer. Cargo
  entries with `layer = 6` are emitted by the generator to
  `dependencies/layer_6/cargo.txt` as a **reference list** (NOT consumed
  by any Containerfile build stage). The generator emits
  `layer_<N>/<manager>.txt` for any `layer >= 1` with entries, so this
  needs **no change to the txt emission path (`write_txt_files`)** — only a
  `render_doc_block` heading special-case for layer 6 (§5.3, A-F2). The spec 02
  AUTO-GEN heading for layer 6 reads "Layer 6 — runtime-manual (not
  build-installed)" (mirrors the existing layer-0 "already in the base image"
  special case). `schema` stays at 1.
- **S4:** The runtime-manual cargo set is declared in `packages.toml`
  at `layer = 6`: `cargo-outdated`, `cargo-expand`, `cargo-edit`,
  `cargo-zigbuild`, `maturin`. `make gen-deps` emits
  `layer_6/cargo.txt` listing them. The Containerfile does **not** read
  `layer_6/cargo.txt`.
- **S5:** The Containerfile `toolchain` sub-layer ordering is
  `3-2 rustup` → `3-3 mise binary` → `3-4 mise install languages`
  (moved up from 3-5) → `3-5 cargo-binstall bootstrap` (new) →
  `3-6 cargo tools via cargo binstall` (was 3-4, command switched from
  `cargo install --locked` to `cargo binstall --only-signed -y`, renumbered). An
  empty `layer_3/cargo.txt` still does not break the build (the
  `if [ -n "$pkgs" ]` guard + `(3, "cargo")` in `EXPECTED_EMPTY_FILES`
  preserved).
- **S6:** `make down && make up` preserves cargo / rustup toolchain
  binaries (the named volumes persist — regression check). **Rollout /
  migration (E-F2):** because `cargo-binstall` and `topgrade` are NEW entries
  in `$CARGO_HOME/bin`, an existing `dotfiles_cargo` named volume (from a prior
  build) will NOT pick them up on `make up` (Podman does not re-populate a
  non-empty volume). Run `make clean` (or `podman volume rm dotfiles_cargo`)
  before the first `make up` after this change; subsequent `make down && make
  up` then persists the new binaries.
- **S7:** `programs/generate_deps/tests/` is green (existing
  `test_cargo_manager.py` + new/updated tests for the layer-6
  runtime-manual heading and the `layer_6/cargo.txt` emission).
- **S8:** Specs updated: new **`24-rust-packages-rule.md`**; spec 02
  (cargo manager rule + layer-6 note + Contract-table `layer` row update for
  layer 6, M2); spec 20 (a general **`I-INFRA1`** installer-infra carve-out +
  **`I-CARGO1`** as its cargo instance, M4/M6; + delegated-rules row → spec 24);
  spec 21 (Stage 3 rows 3-4/3-5/3-6 + acceptance criteria for binstall/topgrade
  + bidirectional link to spec 24, L10).
- **S9:** No secret is baked into any image layer (extends I4 / spec 13
  I-S4 — cargo-binstall and cargo tools are public binaries fetched over
  HTTPS; no credentials involved).

## §2 Alternatives considered

- **A1 — `cargo-binstall` as a `packages.toml` cargo entry, installed via
  `cargo install --locked` (chosen? no).** Keeps `packages.toml` as the
  single SoT (I5) and reuses the existing Layer 3-4 path. **Rejected**:
  it compiles `cargo-binstall` itself from source (~minutes), which
  defeats the tool's purpose (binstall exists to *avoid* source
  compiles). `cargo-binstall` is installer **infrastructure**, like
  `rustup` / `mise`, which are already curl-bootstrapped and not in
  `packages.toml` — so the consistent choice is a Containerfile
  bootstrap (A2).
- **A2 — `cargo-binstall` as a Containerfile prebuilt bootstrap (chosen).**
  Mirror `rustup` (Layer 3-2) / `mise` (Layer 3-3): curl the upstream
  installer / GitHub release tarball, extract the prebuilt binary to
  `$CARGO_HOME/bin`. Fast (no compile); precedent already exists for
  treating the toolchain installer as infra outside `packages.toml`.
  Cost: one more "infra exception" to the `packages.toml` SoT — but
  rustup/mise are already exceptions, so this is consistent, not a
  precedent break.
- **A3 — `cargo-binstall` via the `paru` AUR `cargo-binstall` package.**
  Prebuilt, but conflicts with the Rust packages rule (paru packages
  should not depend on the Rust toolchain). `cargo-binstall` *is* a
  Rust toolchain tool, so paru is the wrong manager. **Rejected.**
- **B1 — Build-time cargo tools via `cargo install --locked` (status
  quo Layer 3-4).** Source compiles every build-time cargo tool — slow,
  and `topgrade` is a large Rust project. **Rejected** for any
  prebuilt-available tool.
- **B2 — Build-time cargo tools via `cargo binstall --only-signed -y` (chosen).**
  Requires `cargo-binstall` to be bootstrapped first (Layer 3-5), then
  Layer 3-6 reads `layer_3/cargo.txt` and runs `cargo binstall --only-signed -y ${=pkgs}`
  (fast prebuilt, signed-only — H2/B-F2). The Rust packages rule (spec 24) requires build-time
  `layer_3` cargo entries to have **signed** prebuilt binaries; unsigned-only / source-only tools
  are runtime-manual (`layer = 6`).
- **C1 — Runtime-manual declaration via a new flag `runtime_only = true`
  (schema 1 → 2).** Semantically explicit; generalizes to any manager; does
  not overload `layer`. Cost: schema bump + `validate` / `write_txt_files` /
  doc-block changes + tests (bounded — one field, one validator branch, one
  test; generator ~200 lines). **Rejected in favor of C2** on the
  minimal-change principle: the schema-bump + 4-site edit is not justified
  for a single use case (cargo runtime-manual tools). The semantic debt C2
  introduces (overloading `layer`) is mitigated by the spec-02 Contract-table
  update (M2). **Revisit trigger (C-F2):** if a second manager ever needs a
  runtime-manual layer, revisit C1 — the sentinel approach scales worse than a
  flag.
- **C2 — Runtime-manual declaration via a new layer number `layer = 6`
  (chosen).** The generator already emits `layer_<N>/<manager>.txt` for
  any `layer >= 1` with entries, so `layer_6/cargo.txt` is produced with
  **zero functional generator change** — only a 2-line spec-02 heading
  special-case (layer 6 → "runtime-manual"). `schema` stays at 1. The
  Containerfile only reads `layer_3`, so `layer_6` is naturally a
  non-build reference list. Picked for minimal change (A-F1: the issue asks
  for "a new toml mechanism to mark 'declared but not installed in layer 3'";
  this design interprets that as a choice between a new layer number or a new
  flag, and picks the layer number).
- **C3 — Don't declare runtime-manual tools in `packages.toml` at all;
  keep `current_cargo_installed.md` as the only record.** Loses the SoT
  benefit and lets the reference doc drift from the manifest. **Rejected.**
  (C-F6: the SoT benefit for `layer = 6` is declarative-intent only — the
  generator cannot confirm the operator actually ran `cargo binstall`; the
  benefit over C3 is that intent lives in the same manifest as the enforced
  set, so the two do not diverge in *declaration*.)

## §3 Architecture / Invariants

- **I1 (single SoT preserved):** `dependencies/packages.toml` remains
  the only hand-edited package manifest. Build-time cargo tools
  (`layer = 3`) and runtime-manual cargo tools (`layer = 6`) both derive
  from it; `layer_3/cargo.txt` and `layer_6/cargo.txt` are both generated
  (I-FS3). The only cargo-* entity outside `packages.toml` is
  `cargo-binstall` itself, treated as installer infra like `rustup` /
  `mise` (consistent precedent).
- **I2 (cargo-binstall = infra):** `cargo-binstall` is bootstrapped in
  the Containerfile from a prebuilt binary and is NOT a `packages.toml`
  entry. It extends the curl-bootstrap precedent of `rustup` (spec 21 row
  3-2) / `mise` (row 3-3), now formalized as a general **`I-INFRA1`** in
  spec 20 (D-F4/L8: rustup/mise had no `I-` invariant before; this design
  introduces the carve-out rather than "mirroring" a non-existent one). The
  criterion: a tool whose sole purpose is to install/manage other tools
  (an installer-of-installers) and which ships an official prebuilt binary is
  infra — not a `packages.toml` entry. **`I-CARGO1`** is the cargo instance of
  `I-INFRA1` (C-F3).
- **I3 (layer semantics):** `layer = 3` = build-time toolchain
  (Containerfile stage `toolchain`, installed via `cargo binstall --only-signed -y`,
  prebuilt only). `layer = 6` = runtime-manual reference list (no
  Containerfile stage; the build only reads `layer_3`). The build stages
  are 0-5, so 6 reads as "post-final-image / runtime." The generator
  emits `layer_<N>/<manager>.txt` for any `layer >= 1` with entries;
  `layer_6/cargo.txt` is therefore generated and is a reference list,
  not a build input.
- **I4 (persistence parity):** cargo tools install under
  `$CARGO_HOME = ~/.local/share/cargo` (the `dotfiles_cargo` named-volume
  mountpoint); `cargo-binstall` and build-time cargo tools install their
  binaries into `$CARGO_HOME/bin`. The
  named volumes persist across `make down && make up` (spec 21
  acceptance #8 analog), identical to the existing cargo/rustup
  pattern. `make clean` destroys them (operator must back up).
- **I5 (empty-list safety):** `(3, "cargo")` stays in
  `EXPECTED_EMPTY_FILES` so the Containerfile's unconditional
  `COPY --from=deps layer_3/cargo.txt` never breaks on an empty list; the
  `if [ -n "$pkgs" ]` guard skips the install. `layer_6/cargo.txt` is
  NOT in `EXPECTED_EMPTY_FILES` (the Containerfile never COPYs it), so
  an empty layer-6 set simply emits no file — safe.
- **I6 (no binstall download cache — revised, E-F1):** `cargo-binstall`
  has NO persistent download cache; it uses a per-run RAII `tempdir` inside
  `$CARGO_HOME` (cleaned up after each install) — verified against upstream
  source (`crates/bin/src/initialise.rs`, `crates/binstalk-downloader/src/download.rs`).
  There is therefore **no** BuildKit `--mount=type=cache` for binstall
  downloads on Layers 3-5/3-6; rebuilds re-fetch the pinned tarball / prebuilt
  archives from GitHub. The download is small and the integrity gate (H1 SHA)
  is the meaningful control. The `cargo/registry` + `cargo/git` cache mounts
  are also dropped from Layer 3-6 (E-F5: `cargo binstall` resolves metadata
  via the crates.io HTTP API, not the registry/git index) — they remain on
  Layers 4-1/4-2 where `paru` / Rust AUR packages still need them.
- **I7 (no runtime entrypoint coupling):** all installs happen at
  build time. The runtime entrypoint (`container/bind/layer_5_files/
  entrypoint.sh`) is unchanged. The user installs runtime-manual
  (`layer = 6`) tools by hand after `make up` via `cargo binstall <pkg>`
  — there is no automation for that in this task (deferred to a future
  issue, see §7).
- **I8 (no new secrets):** cargo-binstall and cargo tools are public
  binaries fetched over HTTPS; no credentials. I4 / spec 13 I-S4 hold
  unchanged.

## §4 Scope / staging breakdown

Single feature, edits across generator / SoT / Containerfile / tests /
specs, each independently verifiable:

1. **Generator** — `programs/generate_deps/main.py`: special-case the
   spec-02 AUTO-GEN heading for layer 6 ("runtime-manual (not
   build-installed)") via a `_LAYER_HEADINGS` lookup table (L5/C-F5, mirrors
   the layer-0 case). No change to the txt emission path (layer-6 emission
   already works). Update stale comments mentioning layer numbers if any.
2. **SoT** — `dependencies/packages.toml`: add `topgrade`
   (`manager = "cargo"`, `layer = 3`); add the five runtime-manual
   entries (`cargo-outdated`, `cargo-expand`, `cargo-edit`,
   `cargo-zigbuild`, `maturin`) at `layer = 6`. Resolve / remove the two
   resolved TODOs (the Rust-packages-rule TODO moves to spec 24; the
   cargo-binstall TODO is resolved by this design).
3. **Containerfile** — `container/Containerfile`: reorder/renumber the
   `toolchain` stage to 3-2/3-3/3-4(mise languages)/3-5(cargo-binstall
   bootstrap)/3-6(cargo tools via `cargo binstall --only-signed -y`). The
   binstall bootstrap RUN pins v1.20.1 + verifies a hardcoded SHA256 before
   extracting (H1/B-F1); the cargo-tools RUN switches from `cargo install
   --locked` to `cargo binstall --only-signed -y` (H2/B-F2). NO
   `~/.cache/cargo-binstall` cache mount (M7/E-F1 — caches nothing); the
   `cargo/registry`+`cargo/git` cache mounts are dropped from 3-6 (E-F5).
4. **Tests** — `programs/generate_deps/tests/`: update / add a test
   asserting `layer_6/cargo.txt` is emitted from `layer = 6` cargo
   entries and that the spec-02 doc block renders the layer-6
   "runtime-manual" heading. Keep `test_cargo_manager.py` green. Add a
   `test-deps` Make target + `08-automations.md` entry (M9/E-F3, spec 03
   §Contract).
5. **Specs** — new `docs/specifications/24-rust-packages-rule.md`;
   update `02-installed-programs.md` (cargo manager rule + layer-6
   note, AUTO-GEN regenerated), `20-container-rules.md`
   (`I-CARGO1` + delegated-rules row for spec 24), `21-container-build-flow.md`
   (Stage 3 rows 3-4/3-5/3-6 + acceptance for binstall/topgrade).
6. **Regen** — `make gen-deps` to materialize `layer_3/cargo.txt`
   (`topgrade`), `layer_6/cargo.txt` (the five), and refresh the spec 02
   AUTO-GEN block.

**Rollback (E-F6):** reverting the tracked changes + `make gen-deps`
regenerates `layer_3/cargo.txt` to empty and refreshes the spec 02 block; the
generator never deletes stale `dependencies/layer_6/cargo.txt` (or the
`layer_6/` dir) — run `git clean -fdx dependencies/layer_6` to purge.

**Rollout (E-F2):** see S6 — `make clean` (or `podman volume rm
dotfiles_cargo`) before the first `make up` after this change.

## §5 Implementation detail

### 5.1 `dependencies/packages.toml` (new entries)

```toml
[[tool]]
name = "topgrade"
manager = "cargo"
layer = 3
has_configs = false
description = "multi-package-manager updater; build-time cargo tool (prebuilt via cargo-binstall)"

# Layer 6 — runtime-manual cargo tools (NOT build-installed; the operator
# installs them at runtime via `cargo binstall <pkg>`). Declared here so
# packages.toml is the single source of truth for the wanted cargo set;
# `make gen-deps` emits `layer_6/cargo.txt` as a reference list the
# Containerfile never reads. See spec 24 (Rust packages rule).
[[tool]]
name = "cargo-outdated"
manager = "cargo"
layer = 6
has_configs = false
description = "runtime-manual cargo tool; detect outdated crate deps"

[[tool]]
name = "cargo-expand"
manager = "cargo"
layer = 6
has_configs = false
description = "runtime-manual cargo tool; pretty-print macro expansion"

[[tool]]
name = "cargo-edit"
manager = "cargo"
layer = 6
has_configs = false
description = "runtime-manual cargo tool; cargo-add/rm/set-version/upgrade"

[[tool]]
name = "cargo-zigbuild"
manager = "cargo"
layer = 6
has_configs = false
description = "runtime-manual cargo tool; cross-compile via zig toolchain"

[[tool]]
name = "maturin"
manager = "cargo"
layer = 6
has_configs = false
description = "runtime-manual cargo tool; build & publish Rust-Python extensions"
```

The two `packages.toml` TODO blocks are resolved: the "Rust packages
rule" TODO is replaced with a pointer to spec 24; the
cargo-binstall/topgrade TODO is replaced with a one-line note that
`cargo-binstall` is infra (Containerfile bootstrap) and `topgrade` is
the build-time cargo tool (this design).

### 5.2 `container/Containerfile` (toolchain stage)

Reorder to (sub-layer renumber; mise languages moves 3-5→3-4, cargo
moves to 3-5/3-6):

```dockerfile
# Layer 3-2: Install rustup (unchanged)
# Layer 3-3: Install mise binary (unchanged)

# Layer 3-4: Install mise-managed languages (was 3-5; moved up)
COPY --from=deps layer_3/mise.txt /tmp/mise_tools.txt
RUN --mount=type=cache,target=/home/${USERNAME}/.cache/mise,uid=${HOST_UID},gid=${HOST_GID} \
    zsh -c 'set -eo pipefail; source /tmp/build-home/.zshenv; \
      pkgs=$(sed "s/#.*//" /tmp/mise_tools.txt | xargs); \
      if [ -n "$pkgs" ]; then mise install ${=pkgs}; mise use -g ${=pkgs}; \
      else echo "toolchain: mise install list is empty -- skipping"; fi;'

# Layer 3-5: Install cargo-binstall (prebuilt bootstrap — INFRA, not in packages.toml)
# cargo-binstall is the installer for the rest of the cargo ecosystem;
# like rustup (3-2) / mise (3-3) it is curl-bootstrapped from a prebuilt
# binary (compiling binstall itself via `cargo install` would defeat its
# purpose). Installed to $CARGO_HOME/bin (on PATH via .zshenv).
# H1/B-F1: pin to v1.20.1 + verify a hardcoded SHA256 before extract (the
# release ships sigstore `.sig` files, not a `.sha256sum`, so a literal
# SHA is the simplest reproducible integrity gate). M1/B-F3: the tarball is
# single-file (`tar -tzf` lists only `cargo-binstall`); extract to a staging
# dir and `mv` into $CARGO_HOME/bin (no PATH-traversal risk).
ARG CARGO_BINSTALL_VERSION=1.20.1
ARG CARGO_BINSTALL_SHA256=f12954bc382e1d0b2df3fbfb217a05d92c25570e4517841e0613499a24f4594e
RUN zsh -c 'set -eo pipefail; source /tmp/build-home/.zshenv; \
      curl -L --proto =https --tlsv1.2 -sSf -o /tmp/binstall.tgz \
        https://github.com/cargo-bins/cargo-binstall/releases/download/v${CARGO_BINSTALL_VERSION}/cargo-binstall-x86_64-unknown-linux-musl.tgz; \
      printf "%s  /tmp/binstall.tgz\n" "${CARGO_BINSTALL_SHA256}" | sha256sum -c -; \
      [ "$(tar -tzf /tmp/binstall.tgz | wc -l)" -eq 1 ] && [ "$(tar -tzf /tmp/binstall.tgz)" = "cargo-binstall" ]; \
      tar -xzf /tmp/binstall.tgz -C /tmp && mv /tmp/cargo-binstall "$CARGO_HOME/bin/cargo-binstall" && rm -f /tmp/binstall.tgz; \
      cargo binstall -V; \
    '

# Layer 3-6: Install build-time cargo tools via cargo-binstall (was 3-4)
# H2/B-F2: `--only-signed` mandates a signed prebuilt source (the `--secure`
# flag suggested in review does NOT exist; `--only-signed` is the correct
# one). `-y` = `--no-confirm` (alias; L7/E-F4 — drop the redundant
# `--no-confirm`). M7/E-F1/E-F5: no binstall cache mount and no
# cargo/registry+git cache mounts (binstall resolves via the crates.io HTTP
# API, not the on-disk index).
COPY --from=deps layer_3/cargo.txt /tmp/cargo_tools.txt
RUN zsh -c 'set -eo pipefail; source /tmp/build-home/.zshenv; \
      pkgs=$(sed "s/#.*//" /tmp/cargo_tools.txt | xargs); \
      if [ -n "$pkgs" ]; then cargo binstall --only-signed -y ${=pkgs}; \
      else echo "toolchain: cargo binstall list is empty -- skipping"; fi; \
    '
```

Notes:
- The `cargo-binstall-x86_64-unknown-linux-musl.tgz` release asset is
  the official prebuilt static binary (no glibc dependency). **Q1 RESOLVED:**
  verified at v1.20.1 — the tgz exists, is single-file (`tar -tzf` lists only
  `cargo-binstall`), and `tar` extraction + `mv` places it at
  `$CARGO_HOME/bin/cargo-binstall`. SHA256
  `f12954bc382e1d0b2df3fbfb217a05d92c25570e4517841e0613499a24f4594e`
  (verified by download + `sha256sum`). The version + SHA are `ARG`s so an
  upgrade is a deliberate, auditable edit (H1).
- `${=pkgs}` (zsh split) is preserved, matching the existing cargo/mise
  sub-layers.
- **Q2 RESOLVED:** the non-interactive flag set is `cargo binstall
  --only-signed -y` (`-y` = `--no-confirm` alias; `--secure` is NOT a real
  flag). Verified via `cargo-binstall --help` + dry-runs; works without a TTY.
  `--only-signed` makes binstall reject unsigned-only packages; verified that
  `topgrade` resolves via a signed source (QuickInstall, sigstore-verified),
  so it stays at layer 3 (H2).

### 5.3 `programs/generate_deps/main.py`

- `render_doc_block`: add a heading special-case for layer 6 (and keep
  the layer-0 case). Minimal diff:

  ```python
  _LAYER_HEADINGS = {
      0: "Layer 0 — already in the base image",
      6: "Layer 6 — runtime-manual (not build-installed)",
  }
  heading = f"#### {_LAYER_HEADINGS.get(layer, f'Layer {layer} — install list')}"
  ```

- No change to `LIST_MANAGERS` / `DOC_ONLY_MANAGERS` / `validate` /
  `write_txt_files` / `EXPECTED_EMPTY_FILES`. `schema` stays at 1. The
  layer-6 cargo entries flow through the existing `write_txt_files`
  loop and emit `layer_6/cargo.txt` automatically.

### 5.4 `docs/specifications/24-rust-packages-rule.md` (new)

Content outline:
- §1 Scope (when this rule applies: any package that depends on the
  Rust toolchain, i.e. is itself a Rust crate / cargo-installable tool).
- §2 Manager selection:
  - **`paru` (AUR prebuilt)** — preferred when (a) the package does NOT
    depend on the rust toolchain (paru packages should not pull
    `rust`/`rustup`), and (b) a stable prebuilt AUR binary exists, and
    (c) the operator does not need beta/latest-from-source.
  - **`cargo-binstall` (prebuilt binary)** — preferred when the package
    IS a rust-toolchain tool and ships a prebuilt binary on GitHub
    releases (fast, no compile, latest available).
  - **`cargo install --locked` (source)** — only when the package has
    NO prebuilt binary (source-only crate) OR the operator needs
    beta/latest-from-source. Slow (compiles).
- §3 Build-time vs runtime-manual boundary:
  - **`layer = 3`** — build-installed, via `cargo binstall --only-signed -y`
    (signed prebuilt only — H2/B-F2: `--only-signed` rejects unsigned-only
    packages). Use only for tools the container must boot with (e.g.
    `topgrade`, which resolves via a signed QuickInstall source). Keep this
    list small (build cost + image size).
  - **`layer = 6`** — runtime-manual reference list. Declared in
    `packages.toml` for SoT but NOT build-installed; the operator runs
    `cargo binstall <pkg>` (or `cargo install --locked <pkg>` for
    source-only) after `make up`. Use for the bulk of wanted cargo
    tools, especially beta/latest/source-driven ones.
  - **Failure mode + recovery (M5/C-F4):** if a `layer = 3` cargo entry has
    no signed prebuilt source, `cargo binstall --only-signed -y` fails at
    Layer 3-6 with a "no signed artifact found" error. Recovery: move the
    entry to `layer = 6` (runtime-manual; install via `cargo install --locked`
    or `cargo binstall` without `--only-signed` at the operator's discretion).
    The generator cannot pre-validate signed-prebuilt availability (no
    network at gen time); this spec-24 rule is the only guard.
- §4 `cargo-binstall` itself is **infrastructure** (Containerfile
  bootstrap, not in `packages.toml`), extending the curl-bootstrap precedent
  of `rustup` / `mise`, now formalized as **`I-INFRA1`** in spec 20 with
  **`I-CARGO1`** as its cargo instance (M4). The bootstrap is version-pinned
  + SHA256-gated (H1); the pinned version + SHA are recorded here and in
  `I-CARGO1` so an upgrade is a deliberate review event. (L4/B-F5, moot: no
  binstall cache mount exists — I6 — so there is no authenticated-source
  cache-sharing concern; binstall invocations are public-binary-only.)
- §5 `layer = 6` convention (no Containerfile stage 6; reference list
  only; generator emits `layer_6/<mgr>.txt` automatically; not in
  `EXPECTED_EMPTY_FILES`).

### 5.5 Spec updates

- `02-installed-programs.md` (H3/D-F1 + M2/C-F1): regenerate AUTO-GEN (via
  `make gen-deps`); update the **Contract table `layer` row** to "integer ≥ 0;
  1-5 = Containerfile stage index; 0 = base image; 6 = runtime-manual
  reference (not build-installed, see spec 24)"; update the `mise` manager
  bullet `(Layer 3-5)` → `(Layer 3-4)` and the `cargo` manager bullet
  `cargo install --locked` → `cargo binstall --only-signed -y`; add a prose
  note: "Build-time cargo tools (`layer = 3`) are installed via `cargo binstall
  --only-signed -y` (signed prebuilt only); `layer = 6` is the runtime-manual
  reference layer (not build-installed). See
  [`24-rust-packages-rule.md`](24-rust-packages-rule.md)."
- `20-container-rules.md` (M4/C-F3 + M6/D-F2): add a general **`I-INFRA1`**
  (installer-infra carve-out: rustup/mise/cargo-binstall — a tool whose sole
  purpose is to install/manage other tools, with an official prebuilt binary,
  is infra, not a `packages.toml` entry) and **`I-CARGO1`** as its cargo
  instance (pinned v1.20.1 + SHA256); add a "Delegated rules" row → spec 24.
- `21-container-build-flow.md` (L10/D-F6): update the Stage-3 rows to
  3-2/3-3/3-4 (mise languages)/3-5 (cargo-binstall bootstrap, pinned+SHA)/3-6
  (cargo tools via `cargo binstall --only-signed -y`); add acceptance criteria
  linking spec 24: "`cargo binstall -V` and `which topgrade` succeed after
  `make up` (preceded by `make clean` on an existing `dotfiles_cargo` volume —
  S6); an empty `layer_3/cargo.txt` does not break the build; `make down &&
  make up` preserves cargo binaries."

## §6 Testing

- Generator unit tests (`programs/generate_deps/tests/`):
  - extend `test_cargo_manager.py` (or a new `test_layer6_runtime.py`)
    to assert: `layer = 6` cargo entries produce `layer_6/cargo.txt`
    with the right names, and do NOT appear in `layer_3/cargo.txt`.
  - assert the spec-02 doc block renders the "Layer 6 — runtime-manual"
    heading for layer 6.
  - assert `layer = 3` cargo entries (topgrade) still produce
    `layer_3/cargo.txt` (regression).
- Manual / build verification:
  - `make gen-deps` → `layer_3/cargo.txt` contains `topgrade`;
    `layer_6/cargo.txt` contains the five; spec 02 AUTO-GEN regenerated.
  - `make build` succeeds; `make up`; `cargo binstall -V` and
    `which topgrade` succeed in the container.
  - `make down && make up` → cargo binaries persist.
  - `programs/generate_deps` tests green via the new `make test-deps` target
    (M9/E-F3: `python3 -m pytest programs/generate_deps/tests/`; baseline 24
    passed).

## §7 Risks / open questions

- **Q1 — RESOLVED.** Asset `cargo-binstall-x86_64-unknown-linux-musl.tgz` @
  v1.20.1; single root binary; SHA256
  `f12954bc382e1d0b2df3fbfb217a05d92c25570e4517841e0613499a24f4594e`
  (verified by download + `sha256sum`). Extract to staging + `mv` (not `tar -C`).
- **Q2 — RESOLVED.** `cargo binstall --only-signed -y`; `-y` = `--no-confirm`
  (alias); `--secure` is NOT a real flag (the review's suggestion was
  incorrect — the correct strict flag is `--only-signed`). Verified via
  `cargo-binstall --help` + dry-runs; works without a TTY. `topgrade` resolves
  via a signed QuickInstall source, so `--only-signed` succeeds.
- **Q3 — RESOLVED.** Add a `test-deps` Make target (`python3 -m pytest
  programs/generate_deps/tests/`) + `08-automations.md` entry (spec 03).
- **Q4 — Arch / asset for non-x86_64.** The container build is x86_64
  (Manjaro base); the musl tarball is x86_64-only. If multi-arch is ever
  needed, the bootstrap must pick the asset by `uname -m`. Out of scope
  for this task (single arch); noted for completeness.
- **Risk — `cargo binstall` availability for `topgrade` — RESOLVED.**
  `topgrade` ships signed prebuilt binaries (QuickInstall, sigstore-verified),
  so `cargo binstall --only-signed -y topgrade` succeeds (verified by
  `--only-signed --dry-run`). If a build-time cargo entry ever lacks a signed
  prebuilt, `cargo binstall --only-signed` errors loudly → move to layer 6
  (spec 24 §3 failure mode). The unsigned-prebuilt concern (B-F2) is closed.
- **Out-of-scope follow-up (L9/D-F5):** spec 20 I-GIT3 references an
  undefined `I-GPG9` (pre-existing, not caused by this design). File a
  separate cleanup issue to fix the dangling reference.

## §8 Deferred (separate future issue)

- Bulk-import the rest of `current_cargo_installed.md` into the build
  (`layer = 3`) — the "curated set in build" the operator marked as
  future. Tracked separately; out of scope here.
- Runtime automation that reads `layer_6/cargo.txt` and offers to
  `cargo binstall` the runtime-manual set at container start (or on
  demand). Out of scope; `layer = 6` is a reference list only in this
  task.