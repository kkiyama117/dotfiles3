# 24 — Rust packages rule

> Spec status: **active**. Normative rule for selecting the install
> manager of a package that depends on the Rust toolchain (a Rust crate /
> cargo-installable tool), and for the build-time vs runtime-manual
> boundary. The `layer` field semantics (including `layer = 6`) are in
> [`02-installed-programs.md`](02-installed-programs.md); the build-flow
> stage table is in [`21-container-build-flow.md`](21-container-build-flow.md).

## §1 Scope

This rule applies to any package that depends on the Rust toolchain —
i.e. is itself a Rust crate or cargo-installable tool. Packages that do
NOT depend on the Rust toolchain use `pacman` / `paru` / `nix` / `uv` as
usual and are out of scope here.

## §2 Manager selection

- **`paru` (AUR prebuilt)** — preferred when ALL of:
  (a) the package does NOT depend on the rust toolchain (paru packages
  should not pull `rust` / `rustup`), AND
  (b) a stable prebuilt AUR binary exists, AND
  (c) the operator does not need beta / latest-from-source.
- **`cargo-binstall` (prebuilt binary)** — preferred when the package IS
  a rust-toolchain tool and ships a prebuilt binary (fast, no compile,
  latest available). Build-time use MUST pass `--only-signed` (§3).
- **`cargo install --locked` (source)** — only when the package has NO
  prebuilt binary (source-only crate) OR the operator needs beta /
  latest-from-source. Slow (compiles).

## §3 Build-time vs runtime-manual boundary

- **`layer = 3`** — build-installed, via `cargo binstall --only-signed -y`
  (signed prebuilt only). `--only-signed` rejects unsigned-only packages
  (the `--secure` flag does NOT exist in cargo-binstall; `--only-signed`
  is the correct strict flag; `-y` = `--no-confirm`). Use only for tools
  the container must boot with (e.g. `topgrade`, which resolves via a
  signed QuickInstall source). Keep this list small (build cost + image
  size).
- **`layer = 6`** — runtime-manual reference list. Declared in
  `packages.toml` for SoT but NOT build-installed; the operator runs
  `cargo binstall <pkg>` (or `cargo install --locked <pkg>` for
  source-only) after `make up`. Use for the bulk of wanted cargo tools,
  especially beta / latest / source-driven ones.
- **Failure mode + recovery:** if a `layer = 3` cargo entry has no
  signed prebuilt source, `cargo binstall --only-signed -y` fails at
  Layer 3-7 with a "no signed artifact found" error. Recovery: move the
  entry to `layer = 6` (runtime-manual; install via `cargo install
  --locked` or `cargo binstall` without `--only-signed` at the
  operator's discretion). The generator cannot pre-validate
  signed-prebuilt availability (no network at gen time); this rule is
  the only guard.

## §4 `cargo-binstall` is infrastructure

`cargo-binstall` itself is **infrastructure** (Containerfile bootstrap,
NOT a `packages.toml` entry), extending the curl-bootstrap precedent of
`rustup` (spec 21 row 3-3), now formalized as
[`20-container-rules.md`](20-container-rules.md) `I-INFRA1` with
`I-CARGO1` as its cargo instance. The bootstrap is version-pinned +
SHA256-gated (currently v1.20.1, SHA256
`f12954bc382e1d0b2df3fbfb217a05d92c25570e4517841e0613499a24f4594e`); the
pinned version + SHA are `ARG`s in the Containerfile so an upgrade is a
deliberate, auditable edit. binstall invocations are public-binary-only
(no authenticated-source binstall shares a cache — there is no binstall
cache mount; see spec 21 / `I-CARGO1`).

## §5 `layer = 6` convention

No Containerfile stage 6 exists (build stages are 0-5). `layer = 6` is a
reference list only: the generator emits `layer_6/<manager>.txt`
automatically for any `layer = 6` entries (no functional generator
change); it is NOT in `EXPECTED_EMPTY_FILES`, so an empty layer-6 set
emits no file. The Containerfile never `COPY`s `layer_6/*`. The spec 02
AUTO-GEN block renders the heading "Layer 6 — runtime-manual (not
build-installed)".

## Related

- Installed-programs contract + `layer` field: [`02-installed-programs.md`](02-installed-programs.md)
- Container rules (`I-INFRA1` / `I-CARGO1`): [`20-container-rules.md`](20-container-rules.md)
- Build flow / Stage 3 rows: [`21-container-build-flow.md`](21-container-build-flow.md)
- Cargo install design: [`implementations/2026-07-02-cargo-install-design.md`](implementations/2026-07-02-cargo-install-design.md)
