# Phase complete — cargo-binstall bootstrap + Rust packages rule

**Date:** 2026-07-02
**Phase:** cargo-install (5 phases — generator / SoT / Containerfile / specs / build-verify)
**Issue:** [`2026-07-02-cargo-install.md`](2026-07-02-cargo-install.md) → closed
**Plan:** [`../plans/2026-07-02-cargo-install-impl.md`](../plans/2026-07-02-cargo-install-impl.md)
**Design:** [`../specifications/implementations/2026-07-02-cargo-install-design.md`](../specifications/implementations/2026-07-02-cargo-install-design.md)
**Review trail:** [pass1-A](../reviews/2026-07-02-cargo-install-review-pass1-A-factual.md) / [B](../reviews/2026-07-02-cargo-install-review-pass1-B-security.md) / [C](../reviews/2026-07-02-cargo-install-review-pass1-C-architecture.md) / [D](../reviews/2026-07-02-cargo-install-review-pass1-D-consistency.md) / [E](../reviews/2026-07-02-cargo-install-review-pass1-E-operability.md) / [aggregate](../reviews/2026-07-02-cargo-install-review-pass1.md); implementation review (consolidated Phases 1-4, c65922c..10be9ee) — **Approved**, no Critical/Important.

## Summary

`cargo-binstall` is bootstrapped at build time as infrastructure (Containerfile
Layer 3-5, version-pinned v1.20.1 + SHA256-gated prebuilt musl tarball, NOT a
`packages.toml` entry — `I-INFRA1`/`I-CARGO1`). `topgrade` is the one build-time
cargo tool (`layer = 3`), installed via `cargo binstall --only-signed -y` (the
review-suggested `--secure` flag does not exist; `--only-signed` is the correct
strict flag; verified `topgrade` resolves via a signed QuickInstall source).
Five runtime-manual cargo tools (`cargo-edit`, `cargo-expand`, `cargo-outdated`,
`cargo-zigbuild`, `maturin`) are declared at a new `layer = 6` (runtime-manual
reference list — declared for SoT, NOT build-installed). The `toolchain`
sub-layers reordered to 3-2 rustup / 3-3 mise binary / 3-4 mise languages / 3-5
cargo-binstall bootstrap / 3-6 cargo tools. The Rust packages rule is normative
in spec 24; spec 02 (Contract table `layer` row + mise/cargo bullets), spec 20
(`I-INFRA1`/`I-CARGO1` + Delegated-rules row), spec 21 (Stage-3 rows + acceptance
#14-17) are updated. `schema` stays at 1; no functional generator change (only a
`_LAYER_HEADINGS` lookup for the layer-6 doc heading). No secret baked into any
image layer. A new `make test-deps` target runs the generator pytest suite (28
passing).

## Acceptance evidence

| # | Criterion (issue) | Verification | Result |
|---|---|---|---|
| S1 | `cargo-binstall` bootstrapped at build time as infra | `podman build --target toolchain` log: `sha256sum -c` → `/tmp/binstall.tgz: OK`; `cargo binstall -V` → `1.20.1`; runtime `podman exec ... cargo binstall -V` → `1.20.1` | PASS |
| S2 | `topgrade` declared (layer 3) + installed via `cargo binstall --only-signed -y` | `layer_3/cargo.txt` contains `topgrade`; build log: `cargo binstall --only-signed -y topgrade` → `Verified signature ... QuickInstall` → installed; runtime `which topgrade` → `$CARGO_HOME/bin/topgrade`, `topgrade -V` → `17.6.2` | PASS |
| S3 | `layer = 6` runtime-manual mechanism (no functional generator change) | `test_layer6_runtime.py` (4 tests) pass; `render_doc_block` uses `_LAYER_HEADINGS` lookup; `layer_6/cargo.txt` emitted automatically | PASS |
| S4 | 5 runtime-manual tools declared at layer 6 | `layer_6/cargo.txt` lists cargo-edit/cargo-expand/cargo-outdated/cargo-zigbuild/maturin; Containerfile does NOT read `layer_6/*` | PASS |
| S5 | toolchain sub-layer ordering 3-2/3-3/3-4/3-5/3-6; empty `layer_3/cargo.txt` safe | Containerfile Stage 3 reordered (review verified lines 173-216); `(3,"cargo")` in `EXPECTED_EMPTY_FILES` + `if [ -n "$pkgs" ]` guard preserved | PASS |
| S6 | `make down && make up` preserves cargo binaries (+ rollout) | after `make down && make up` (volume preserved): `cargo binstall -V` → `1.20.1`, `which topgrade` resolves. Rollout used targeted `podman volume rm dotfiles_cargo` (NOT `make clean`, which would wipe `dotfiles_gnupg`) | PASS |
| S7 | generator tests green | `make test-deps` → `28 passed in 0.49s` | PASS |
| S8 | specs updated (24 / 02 / 20 / 21) | spec 24 created (83 lines); spec 02 Contract table `layer` row + mise/cargo bullets + AUTO-GEN; spec 20 `I-INFRA1`/`I-CARGO1` + Delegated row; spec 21 Stage-3 rows 3-4/3-5/3-6 + acceptance #14-17 (review verified) | PASS |
| S9 | no secret baked into any image layer | all fetches are public HTTPS binaries with SHA256 integrity gate; no credentials in any RUN (extends I4 / spec 13 I-S4) | PASS |

## Representative command output

### S1 — cargo-binstall bootstrap (toolchain-stage build)

```
[3/3] STEP 8/10: RUN zsh -c '... curl ... -o /tmp/binstall.tgz ...; printf "%s  /tmp/binstall.tgz\n" "$SHA" | sha256sum -c -; ... mv /tmp/cargo-binstall "$CARGO_HOME/bin/cargo-binstall"; cargo binstall -V'
/tmp/binstall.tgz: OK
1.20.1
```

### S2 — topgrade via cargo binstall --only-signed -y (toolchain-stage build)

```
[3/3] STEP 10/10: RUN zsh -c '... cargo binstall --only-signed -y ${=pkgs}'
 INFO resolve: Resolving package: 'topgrade'
 WARN resolve: Error while downloading and extracting from fetcher github.com: No signature present
 INFO resolve: Verified signature for package 'topgrade-17.6.2-x86_64-unknown-linux-gnu': timestamp:1781957038 file:topgrade-17.6.2-x86_64-unknown-linux-gnu.tar.gz hashed
 WARN The package topgrade v17.6.2 (x86_64-unknown-linux-gnu) has been downloaded from third-party source QuickInstall
 INFO   - topgrade => /home/kiyama/.local/share/cargo/bin/topgrade
 INFO Done in 2.722045861s
```

`--only-signed` rejected the unsigned GitHub-release fetcher and resolved via
the signed QuickInstall source (sigstore-verified). topgrade stays at layer 3.

### S1/S2 — runtime smoke (after `podman volume rm dotfiles_cargo && make up`)

```
$ podman exec dotfiles-manjaro zsh -ic 'cargo binstall -V'
1.20.1
$ podman exec dotfiles-manjaro zsh -ic 'which topgrade && topgrade -V'
/home/kiyama/.local/share/cargo/bin/topgrade
topgrade 17.6.2
```

### S6 — persistence across `make down && make up` (volume preserved)

```
$ make down && make up && sleep 4
$ podman exec dotfiles-manjaro zsh -ic 'cargo binstall -V && which topgrade'
1.20.1
/home/kiyama/.local/share/cargo/bin/topgrade
```

### S4 — layer-6 tools are reference-only (NOT build-installed)

```
$ podman exec dotfiles-manjaro zsh -ic 'ls ~/.local/share/cargo/bin | grep -E "cargo-outdated|cargo-expand|cargo-edit|cargo-zigbuild|maturin" || echo "none (expected — layer 6 is runtime-manual)"'
none (expected — layer 6 is runtime-manual)
```

The operator installs the layer-6 tools at runtime via `cargo binstall <pkg>`.

### GPG regression check (dotfiles_gnupg preserved)

```
$ podman exec dotfiles-manjaro zsh -ic 'gpg --list-secret-keys ... | grep -q D131EE0BBB05F21E && echo "GPG key present (preserved)"'
GPG key present (preserved)
```

The targeted `podman volume rm dotfiles_cargo` (instead of `make clean`) left
`dotfiles_gnupg` intact — the GPG key from the 2026-07-02 host-key import
survives.

## Deviations / caveats

1. **Plan Phase 5 Step 3 said `make clean && make up` — corrected to
   `podman volume rm dotfiles_cargo && make up`.** `make clean` removes the
   image AND all four volumes including `dotfiles_gnupg` (the GPG key) and
   `dotfiles_mise`/`dotfiles_rustup`. The rollout intent was to reset ONLY the
   cargo volume (so the new `$CARGO_HOME/bin` binaries copy-on-first-mount from
   the image). The targeted `podman volume rm dotfiles_cargo` achieves that
   without destroying the GPG key or forcing an image rebuild. The plan/design
   rollout note is updated to recommend `podman volume rm dotfiles_cargo` over
   `make clean` for this migration.
2. **zsh `=`-quoting fix (commit 10be9ee).** The plan's Phase 3 code used
   `curl --proto =https` inside `zsh -c '...'`; zsh's `=`-word expansion treats
   `=https` as a command path lookup, breaking the download. Fixed to
   `--proto "=https"` (matching the existing rustup Layer 3-2 line). Caught
   during the Phase 5 build attempt.
3. **Stage 3 header comment refreshed (review Minor 1, commit 7ad7352).** The
   pre-existing header mentioned cargo registry/git cache mounts that moved to
   the aur stage (4-1/4-2); updated to reflect the rustup/mise cache mounts +
   binstall's no-cache + the crates.io HTTP API.
4. **Phases 1-4 were implemented in a single consolidated implementer run**
   (the implementer went beyond the Phase 1 scope), then reviewed as one
   consolidated gate (c65922c..10be9ee, Approved). The per-phase SDD gates were
   collapsed; the consolidated review + the Phase 5 build evidence cover the
   same ground.
5. **Minor (left, cosmetic):** commit `08948d7` message contains literal `\n`
   sequences instead of real newlines. Non-blocking; the branch is not pushed.

## Secrecy invariants (unchanged)

- No GPG key material or Bitwarden credential is baked into any image layer.
  `cargo-binstall` and the cargo tools are public binaries fetched over HTTPS
  with a SHA256 integrity gate; no credentials in any RUN (extends I4 / spec 13
  I-S4).
- The `dotfiles_gnupg` named volume was preserved (targeted cargo-volume reset,
  not `make clean`); the GPG key survives.