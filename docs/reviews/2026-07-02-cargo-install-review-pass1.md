# cargo-install — Review pass-1 (Aggregate)

**Date:** 2026-07-02
**Reviewer:** design author (aggregation of 5 subagent per-letter reviews)
**Subject:** [`docs/specifications/implementations/2026-07-02-cargo-install-design.md`](../specifications/implementations/2026-07-02-cargo-install-design.md)
**Pass:** 1
**Status:** done (all findings acknowledged; design revised in the same commit)

## Per-letter reviews

| Letter | Perspective | Verdict | File |
|---|---|---|---|
| A | factual / correctness | Approve (3 LOW) | [`pass1-A-factual.md`](2026-07-02-cargo-install-review-pass1-A-factual.md) |
| B | security | Request changes (2 HIGH, 1 MEDIUM, 2 LOW) | [`pass1-B-security.md`](2026-07-02-cargo-install-review-pass1-B-security.md) |
| C | architecture / senior engineering | Approve with conditions (4 MEDIUM, 3 LOW) | [`pass1-C-architecture.md`](2026-07-02-cargo-install-review-pass1-C-architecture.md) |
| D | consistency / cross-doc | Request changes (1 HIGH, 2 MEDIUM, 3 LOW) | [`pass1-D-consistency.md`](2026-07-02-cargo-install-review-pass1-D-consistency.md) |
| E | operability / runtime | Approve with conditions (3 MEDIUM, 3 LOW) | [`pass1-E-operability.md`](2026-07-02-cargo-install-review-pass1-E-operability.md) |

## Deduplicated findings (post-revise status)

HIGH (MUST be RESOLVED — all RESOLVED):

| ID | Origin | Summary | Post-revise status |
|---|---|---|---|
| H1 | B-F1 | cargo-binstall tarball floating `/latest/`, no checksum | **RESOLVED** — pin v1.20.1; hardcode SHA256 `f12954bc…24f4594e`; `sha256sum -c` before extract (§5.2); recorded in spec 24 + I-CARGO1. Verified asset + SHA. |
| H2 | B-F2 | `cargo binstall` silently trusts unsigned prebuilts | **RESOLVED** — the recommended `--secure` flag does NOT exist in cargo-binstall 1.20.1; the correct flag is `--only-signed`. Layer 3-6 mandates `cargo binstall --only-signed -y`. Verified topgrade HAS a signed source (QuickInstall, sigstore-verified) so `--only-signed` succeeds → topgrade stays at layer 3. Spec 24 §3 rule: build-time (layer=3) cargo entries MUST be `--only-signed`-installable; unsigned-only → layer 6. |
| H3 | D-F1 (≈A-F3) | spec 02 mise bullet "Layer 3-5" not updated after reorder | **RESOLVED** — §5.5 spec-02 edit list now includes: mise bullet `Layer 3-5` → `Layer 3-4`; cargo bullet `cargo install --locked` → `cargo binstall --only-signed -y`. |

MEDIUM (RESOLVED/addressed — all acknowledged):

| ID | Origin | Summary | Post-revise status |
|---|---|---|---|
| M1 | B-F3 | `curl\|tar` into PATH-injected dir, no integrity gate | **RESOLVED** — verified tarball is single-file (`tar -tzf` lists only `cargo-binstall`); extract to staging dir + `mv` into `$CARGO_HOME/bin` after the SHA gate. |
| M2 | C-F1 ≈ D-F3 | `layer=6` overloads the `layer` field; spec 02 contract table not updated | **RESOLVED** — spec 02 Contract table `layer` row updated to "integer ≥ 0; 1-5 = Containerfile stage index; 0 = base image; 6 = runtime-manual reference (not build-installed, see spec 24)". §5.5 explicit. |
| M3 | C-F2 | C1 (flag) rejection under-argued vs C2 semantic debt | **addressed** — §2 C1 rejection expanded: C1 is semantically cleaner/generalizable but the schema-bump + 4-site edit is not justified for a single use case; C2 chosen on minimal-change; revisit trigger stated (a second manager needing a runtime-manual layer). |
| M4 | C-F3 | infra-exception (rustup/mise/cargo-binstall) growing without a normative criterion | **RESOLVED** — spec 20 gains a general `I-INFRA1` (installer-infra carve-out: a tool whose sole purpose is to install/manage other tools, with an official prebuilt binary, is infra — not a `packages.toml` entry); `I-CARGO1` is an instance of `I-INFRA1`. |
| M5 | C-F4 | "layer=3 must have prebuilt" is policy-only; no generator guard | **addressed** — spec 24 §3 documents the failure mode + recovery: a layer=3 entry with no signed prebuilt fails `cargo binstall --only-signed` loudly → move to layer 6 (runtime-manual, `cargo install --locked`). Generator cannot pre-validate (no network at gen time); spec-24 rule is the only guard. |
| M6 | D-F2 | `I-CARGO` vs `I-CARGO1` glyph inconsistency | **RESOLVED** — unified to `I-CARGO1` in S8 + issue acceptance #8. |
| M7 | E-F1 | `~/.cache/cargo-binstall` cache mount caches nothing (binstall uses per-run tempdir in `$CARGO_HOME`) | **RESOLVED** — dropped the `~/.cache/cargo-binstall` cache mounts from Layers 3-5/3-6; I6 rewritten ("cargo-binstall has no persistent download cache; per-run RAII tempdir in `$CARGO_HOME`; no BuildKit cache mount for binstall downloads; rebuilds re-fetch"). Verified against upstream source. |
| M8 | E-F2 | named-volume migration not addressed (existing `dotfiles_cargo` won't get new `$CARGO_HOME/bin` binaries) | **RESOLVED** — added a "Rollout / migration" note (§4/§5): run `make clean` (or `podman volume rm dotfiles_cargo`) before the first `make up` after this change; subsequent `make down && make up` then persists (S6). |
| M9 | E-F3 | no `test-deps` Make target; spec 03 requires `08-automations.md` entry | **RESOLVED** — add a `test-deps` Make target (`python3 -m pytest programs/generate_deps/tests/`) + `08-automations.md` entry. |

LOW (addressed/INCOMPLETE — all acknowledged):

| ID | Origin | Summary | Post-revise status |
|---|---|---|---|
| L1 | A-F1 | "user explicitly offered 'new number or new flag'" unsupported attribution | **addressed** — softened to "the issue asks for a new toml mechanism; this design picks a new layer number (C2) over a new flag (C1) on the minimal-change principle." |
| L2 | A-F2 | "no functional generator change" imprecise | **addressed** — §S3 now reads "no change to the txt emission path (`write_txt_files`); only a `render_doc_block` heading special-case (§5.3)." |
| L3 | B-F4 | no TLS pinning | **addressed** — accepted risk, consistent with rustup/mise precedent; noted in spec 24 (the SHA gate is the meaningful integrity control, not TLS pinning). |
| L4 | B-F5 | cache mount cross-build isolation / authenticated-source guard | **moot** — the cache mount is dropped (M7); no `~/.cache/cargo-binstall` mount exists. spec 24 keeps a one-line note that binstall invocations are public-binary-only. |
| L5 | C-F5 | nested-ternary heading special-case | **addressed** — §5.3 uses a `_LAYER_HEADINGS` lookup table instead of a nested ternary. |
| L6 | C-F6 | C3 rejection does not state the SoT asymmetry (layer 6 = declarative intent, not verified state) | **addressed** — §2 C3 rejection notes: layer-6 SoT is declarative-intent only (the generator cannot confirm the operator actually ran `cargo binstall`); the benefit over C3 is that intent lives in the same manifest as the enforced set. |
| L7 | C-F7 ≈ E-F4 | `cargo binstall -y --no-confirm` redundant/ambiguous | **RESOLVED** — use `cargo binstall --only-signed -y` (single flag set; `-y` = `--no-confirm` alias; `--no-confirm` dropped). Q2 RESOLVED. Verified via `cargo-binstall --help`. |
| L8 | D-F4 | "mirrors how rustup/mise are documented as curl-bootstrapped infra" overstated (no I-RUSTUP/I-MISE exist) | **addressed** — §3 I2 reframed: "extending the curl-bootstrap precedent of rustup (spec 21 row 3-2) / mise (row 3-3), now formalized as `I-INFRA1` (with `I-CARGO1` as the cargo instance)." |
| L9 | D-F5 | pre-existing `I-GPG9` dangling reference in spec 20 I-GIT3 | **INCOMPLETE (out of scope)** — not caused by this design (pre-existing). Recorded for a separate cleanup issue (follow-up: `docs/issues/` to fix I-GPG9 → real number or define it). Not a blocker for this pass. |
| L10 | D-F6 | spec 21 ↔ spec 24 bidirectional links not in edit list | **addressed** — §5.5 now lists: spec 21 acceptance criterion links spec 24; spec 24 §3/§5 link back to spec 02 (layer contract) + spec 21 (stage table). |
| L11 | E-F5 | `cargo/registry`+`cargo/git` cache mounts ineffective for binstall (uses crates.io HTTP API) | **RESOLVED** — dropped from Layer 3-6; kept on Layers 4-1/4-2 (paru / Rust AUR still need them). Verified. |
| L12 | E-F6 | generator never deletes stale `layer_6/` dir on revert | **addressed** — §4 rollback note: after revert + `make gen-deps`, `dependencies/layer_6/cargo.txt` lingers; `git clean -fdx dependencies/layer_6` purges it. |

## Open questions resolved

| OQ | Resolution |
|---|---|
| Q1 (cargo-binstall asset) | **RESOLVED** — `cargo-binstall-x86_64-unknown-linux-musl.tgz` @ v1.20.1; single root-level binary; SHA256 `f12954bc382e1d0b2df3fbfb217a05d92c25570e4517841e0613499a24f4594e` (verified by download + `sha256sum`). |
| Q2 (non-interactive flag) | **RESOLVED** — `cargo binstall --only-signed -y`; `-y` = `--no-confirm` (alias); works without a TTY. `--secure` (suggested by B) is NOT a real flag; `--only-signed` is. Verified via `cargo-binstall --help` + dry-runs. |
| Q3 (test target) | **RESOLVED** — add `test-deps` Make target + `08-automations.md` entry (spec 03 §Contract). |
| Q4 (non-x86_64 arch) | out of scope (single-arch build); noted in §7. |

## Prioritized actions applied in the revise

1. (H1) pin cargo-binstall v1.20.1 + hardcoded SHA256 + `sha256sum -c`.
2. (H2) `cargo binstall --only-signed -y` for the build path; topgrade stays layer 3 (signed source verified).
3. (H3) spec 02 mise/cargo bullets updated for the reorder + binstall command.
4. (M7/M11) drop ineffective cache mounts (`~/.cache/cargo-binstall`, `cargo/registry`, `cargo/git` on 3-6); rewrite I6.
5. (M8) add the rollout/migration note (`make clean` before first `make up`).
6. (M9) add `test-deps` Make target + `08-automations.md` entry.
7. (M2) update spec 02 Contract table `layer` row for layer 6.
8. (M4) add `I-INFRA1` to spec 20; `I-CARGO1` is an instance.
9. (M5) spec 24 §3 failure-mode + recovery text.
10. (L5) `_LAYER_HEADINGS` lookup table in the generator.
11. (L7) flag set finalized.
12. (L9) I-GPG9 dangling ref recorded as out-of-scope follow-up.
13. Remaining LOW wording fixes (L1, L2, L3, L6, L8, L10, L12) applied inline.

## Pass termination judgement

Per spec 09 §2.3: every finding is in `RESOLVED` / `addressed` / `INCOMPLETE (with stated reason + follow-up)`. The single INCOMPLETE item (L9 — pre-existing I-GPG9 dangling ref) is out of scope with a named follow-up (separate cleanup issue) and is not caused by this design. **No `open` / `REGRESSION` / `blocked` remains.** Pass 1 terminates; the design is handed back for user review before the implementation plan (writing-plans).