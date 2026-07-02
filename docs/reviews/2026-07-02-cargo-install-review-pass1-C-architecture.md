# cargo-install — Review pass-1 (Letter C: architecture / senior engineering)

**Date:** 2026-07-02
**Reviewer:** ecc:architect (subagent)
**Subject:** [`docs/specifications/implementations/2026-07-02-cargo-install-design.md`](../../specifications/implementations/2026-07-02-cargo-install-design.md)
**Pass:** 1
**Status:** in-review

## Verdict

**Approve with conditions.** The design is coherent, well-scoped, and
consistent with the repo's established patterns (it consciously mirrors
the mise-managed-languages sibling). The infra-bootstrap choice for
`cargo-binstall` is the right call and is consistent with the
rustup/mise precedent. Two conditions must be addressed before
implementation: (a) the `layer = 6` semantic overload of the `layer`
field needs an explicit contract-table update in spec 02 (not just a
prose note), and (b) the §2-C1 rejection is under-argued relative to
the semantic debt C2 introduces. Several lower-severity items are
noted for the next revise.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| F1 | MEDIUM | open | `02-installed-programs.md` Contract table; design §3 I3, §4.5 | `layer = 6` overloads the `layer` field's documented semantics ("Containerfile layer index") with a declaration-category sentinel; contract table must be updated, not just annotated in prose |
| F2 | MEDIUM | open | design §2 C1 vs C2 | The rejection of C1 (`runtime_only` flag) is under-argued — "minimal change" is asserted but the semantic cost of overloading `layer` is not weighed against the small schema-bump cost |
| F3 | MEDIUM | open | design §3 I2, §5.5; `20-container-rules.md` I5 | The "infra exception" category (rustup/mise/cargo-binstall) is growing without a normative membership criterion; I-CARGO1 is cargo-specific where a general "installer-infra" carve-out from I5 is needed |
| F4 | MEDIUM | open | design §7 Risk, §5.4 spec 24 §3 | The spec-24 rule "build-time layer=3 must have prebuilt" is policy-only; no generator-level guard prevents a source-only crate at `layer = 3` breaking the build with a confusing `cargo binstall` error |
| F5 | LOW | open | design §5.3 `render_doc_block` | The nested-ternary heading special-case (`layer == 0 ... else layer == 6 ... else default`) does not scale; a lookup table is more maintainable |
| F6 | LOW | open | design §2 C3 | The C3 rejection ("loses SoT benefit") does not acknowledge that the SoT benefit for a non-enforced reference list is weaker than for a build-enforced list; the asymmetry should be stated |
| F7 | LOW | open | design §5.2 Layer 3-6 | `cargo binstall -y --no-confirm` lists two conflicting non-interactive flags (`-y` and `--no-confirm`); Q2 already flags this but the example code should not carry both pending resolution |

### F1 details

> **Quote (spec 02 Contract table):** `layer | yes | integer ≥ 1
> (Containerfile layer index)`. **Design §3 I3:** "`layer = 6` =
> runtime-manual reference list (no Containerfile stage; the build only
> reads `layer_3`). The build stages are 0-5, so 6 reads as
> 'post-final-image / runtime.'"

The `layer` field is contractually defined as a Containerfile layer
index. There is no Containerfile layer 6 — the build stages are 0-5
(design itself states this). Declaring `layer = 6` therefore uses the
field as a sentinel for a *declaration category* ("runtime-manual,
not build-installed"), not a build stage. This is a semantic overload:
the same field means "build stage" for layers 1-5 and "declaration
category" for layer 6. A reader encountering `layer = 6` in
`packages.toml` without the spec-24 context will reasonably look for a
Containerfile Layer 6 and find none.

The design's §4.5 says spec 02 gets "a prose note to the `cargo`
manager rule" mentioning layer 6. That is insufficient: the
*contract table* definition of `layer` is the normative source, and it
must be updated to acknowledge that layer 6 is a non-build sentinel,
or split into two fields. Without the table update, the contract and
the usage diverge.

**Suggested fix:** In `02-installed-programs.md`, update the Contract
table `layer` row to: `integer ≥ 0; layers 1-5 = Containerfile build
stage index; layer 0 = already in base image; layer 6 = runtime-manual
reference list (not build-installed; no Containerfile stage).` Cross-ref
spec 24 §3. **Verification:** re-read the contract table after the
edit and confirm a new reader can infer layer-6 semantics without
reading the design doc.

### F2 details

> **Quote (design §2 C1):** "Semantically explicit; generalizes to any
> manager. Cost: schema bump + `validate` / `write_txt_files` /
> doc-block changes + tests. **Rejected in favor of C2** for minimal
> change."

C1 (a `runtime_only = true` flag, schema 1→2) is semantically
superior: it expresses "declared but not build-installed" as an
explicit boolean orthogonal to the build stage, generalizes to any
manager (not just cargo), and does not overload `layer`. C2 reuses
`layer` as a sentinel, which introduces the F1 semantic debt. The
rejection asserts "minimal change" as the sole criterion without
weighing the semantic cost. The schema-bump cost of C1 is bounded
(one field, one validator branch, one test) and the generator is
small (~200 lines). The tradeoff is real but the design does not
make it explicitly.

**Suggested fix:** Expand the C1 rejection to state: "C1 is
semantically cleaner and generalizes, but the schema bump + 4-site
edit cost is not justified for a single use case (cargo runtime-manual
tools). C2 is chosen on the minimal-change principle; the semantic
overload of `layer` is mitigated by the spec-02 contract-table update
(F1). If a second manager ever needs a runtime-manual layer, revisit
C1." **Verification:** confirm the expanded justification is
internally consistent with F1's fix.

### F3 details

> **Quote (design §3 I2):** "`cargo-binstall` is bootstrapped in the
> Containerfile from a prebuilt binary and is NOT a `packages.toml`
> entry. It occupies the same 'toolchain installer' category as
> `rustup` (Layer 3-2) and `mise` (Layer 3-3). A new `I-CARGO1`
> invariant records this (spec 20)."

> **Quote (`20-container-rules.md` I5):** "All packages must originate
> from `dependencies/packages.toml`. Ad-hoc `pacman -S` / `paru -S`
> calls in the Containerfile are forbidden once `gen-deps` is wired."

I5 is stated absolutely, yet `rustup`, `mise`, and now
`cargo-binstall` are all curl-bootstrapped in the Containerfile
without being in `packages.toml`. These are de-facto exceptions, but
spec 20 has no formal carve-out — only the `paru` case is documented
(via `I-AUR2`, which declares `paru` as `manager = "custom"` doc-only,
a different mechanism). The design proposes `I-CARGO1` for
cargo-binstall specifically, but the pattern is general: any
"installer-infra" tool (an installer whose purpose is to install
other things, bootstrapped from a prebuilt binary) is excluded from
`packages.toml`. Without a general criterion, each new infra tool
needs a new `I-*1` invariant and the exception list grows ad hoc.

**Suggested fix:** In spec 20, add a general invariant (e.g. `I-INFRA1`):
"Toolchain *installer* binaries (`rustup`, `mise`, `cargo-binstall`) are
curl-bootstrapped in the Containerfile and are NOT `packages.toml`
entries. Criterion: a tool whose sole purpose is to install/manage
other tools (an installer-of-installers), and which ships an official
prebuilt binary, is infra — not a package. `I-CARGO1` is an instance of
`I-INFRA1`." **Verification:** confirm `rustup`, `mise`,
`cargo-binstall` all satisfy the stated criterion and no
`packages.toml` entry does.

### F4 details

> **Quote (design §7 Risk):** "If a build-time cargo entry ever lacks
> a prebuilt, `cargo binstall` errors (does not auto-fall back to
> source). The Rust packages rule (spec 24) requires build-time
> `layer = 3` cargo entries to have prebuilt binaries; source-only
> tools must go to `layer = 6`."

The spec-24 rule is a documentation/policy guard. There is no
generator-level validation that a `layer = 3` cargo entry actually
ships a prebuilt binary on GitHub releases. A maintainer adding a
source-only crate at `layer = 3` (e.g. a crate that is
cargo-installable but has no binstall-compatible release) will get a
`cargo binstall` failure at build time with an error that does not
point to spec 24. The `validate()` function in `main.py` checks
`name`/`manager`/`layer`/`has_configs` but nothing about prebuilt
availability (which is inherently undeterminable at gen time without
network access). So the guard is necessarily policy-level — but the
design should at least document the failure mode and the recovery path
in spec 24 so the build-break is diagnosable.

**Suggested fix:** In spec 24 §3, add: "If a `layer = 3` cargo entry
has no prebuilt binary, `cargo binstall -y` fails at Layer 3-6 with a
'no prebuilt artifact found' error. Recovery: move the entry to
`layer = 6` (runtime-manual, install via `cargo install --locked`
at runtime). The generator cannot pre-validate prebuilt availability;
the spec-24 rule is the only guard." **Verification:** confirm the
recovery path is actionable and does not require a build-flow change.

### F5 details

> **Quote (design §5.3):**
> ```python
> heading = (
>     "#### Layer 0 — already in the base image"
>     if layer == 0
>     else "#### Layer 6 — runtime-manual (not build-installed)"
>     if layer == 6
>     else f"#### Layer {layer} — install list"
> )
> ```

A nested ternary with magic numbers does not scale if layer 7+ gains
special semantics. A lookup table is clearer and extensible:

```python
_LAYER_HEADINGS = {
    0: "Layer 0 — already in the base image",
    6: "Layer 6 — runtime-manual (not build-installed)",
}
heading = f"#### {_LAYER_HEADINGS.get(layer, f'Layer {layer} — install list')}"
```

**Verification:** existing layer-0 and layer-1..4 headings render
identically; layer 6 renders the new heading.

### F6 details

> **Quote (design §2 C3):** "Don't declare runtime-manual tools in
> `packages.toml` at all; keep `current_cargo_installed.md` as the
> only record. Loses the SoT benefit and lets the reference doc drift
> from the manifest. **Rejected.**"

The rejection is valid but does not acknowledge that the SoT benefit
for a *non-enforced reference list* (layer 6 — nothing installs it,
nothing verifies it) is structurally weaker than for a *build-enforced
list* (layer 3 — the Containerfile reads it). A layer-6 entry can
still drift from what the operator actually installs at runtime; the
generator cannot detect that. The rejection should state this
asymmetry so the reader understands the SoT claim is "declarative
intent," not "verified state."

**Suggested fix:** Add to C3 rejection: "Note: the SoT benefit for
layer 6 is declarative-only (the list records *intent*, not verified
runtime state — the generator cannot confirm the operator actually
ran `cargo binstall`). The benefit over C3 is that intent lives in
the same manifest as the enforced set, so the two do not diverge in
*declaration*." **Verification:** confirm the qualification is
consistent with §3 I1.

### F7 details

> **Quote (design §5.2 Layer 3-6):** `cargo binstall -y --no-confirm
> ${=pkgs}`

The success criteria (S2) and §3 I3 say `cargo binstall -y`, but the
implementation example in §5.2 adds `--no-confirm`. Q2 already flags
that the exact non-interactive flag set is unresolved. Carrying both
`-y` and `--no-confirm` in the example is confusing — in
`cargo-binstall`, `-y` / `--no-confirm` may be aliases or distinct.
The example should carry a placeholder (e.g. `<non-interactive-flags>`)
until Q2 resolves, to avoid a reader copy-pasting a wrong combination.

**Suggested fix:** Replace `cargo binstall -y --no-confirm ${=pkgs}`
with `cargo binstall <TBD-non-interactive-flags> ${=pkgs}` in the §5.2
example, and resolve Q2 before implementation. **Verification:** the
final flag set is confirmed against `cargo binstall --help` and tested
in a build.

## Verified premises

- **P1:** The generator (`programs/generate_deps/main.py`) emits
  `layer_<N>/<manager>.txt` for any `layer >= 1` with entries —
  verified in `write_txt_files` (skips only `layer < 1`) and
  `render_packages_txt`. So `layer_6/cargo.txt` is produced with zero
  functional generator change. The design's S3 claim is accurate.
- **P2:** `EXPECTED_EMPTY_FILES = ((3, "cargo"), (4, "paru"),
  (3, "mise"))` — confirmed in `main.py`. `(6, "cargo")` is absent, so
  an empty layer-6 set emits no file; the Containerfile never COPYs
  `layer_6/cargo.txt`, so this is safe (design I5 is correct).
- **P3:** The current Containerfile order is 3-2 rustup → 3-3 mise
  binary → 3-4 cargo `install --locked` → 3-5 mise install languages
  (verified at `container/Containerfile:166-235`). The proposed reorder
  to 3-2/3-3/3-4(mise lang)/3-5(binstall)/3-6(cargo binstall) is
  dependency-safe: `cargo-binstall` and cargo tools need only
  rustup/cargo (3-2), not mise languages; mise languages need only the
  mise binary (3-3), not cargo. No hidden ordering dependency exists
  between the mise-languages and cargo-tools sub-layers.
- **P4:** `rustup` and `mise` are not in `packages.toml` (confirmed:
  spec 02 AUTO-GEN lists no `rustup`/`mise` entries; they are
  curl-bootstrapped in the Containerfile at 3-2/3-3). So treating
  `cargo-binstall` as infra is consistent with existing precedent —
  but I5's absolute wording is not formally reconciled with these
  exceptions (see F3).
- **P5:** The mise-managed-languages sibling design
  (`2026-07-01-mise-managed-languages-design.md`) established the
  pattern this design follows: list-manager promotion, `layer_3/<mgr>.txt`
  emission, Containerfile sub-layer with cache mount, `EXPECTED_EMPTY_FILES`
  entry, spec 02 + spec 21 updates. The cargo design's structure mirrors
  it faithfully, which is a coherence positive.
- **P6:** The `validate()` function in `main.py` checks
  `name`/`manager`/`layer` (non-negative int)/`has_configs`/`description`
  only. No field constrains prebuilt-binary availability, so spec-24's
  "layer=3 must have prebuilt" rule is unenforceable at gen time (see F4).
- **P7:** The design's claim that `schema` stays at 1 under C2 is
  correct: `validate` accepts any `layer >= 0` int, so `layer = 6`
  passes without a schema change. Under C1, `runtime_only` would
  require schema 2 + a `validate` branch — the cost is real but
  bounded.

## Open questions

- **Q-C1:** Should the C1-vs-C2 tradeoff be revisited if a second
  manager (e.g. `nix`, `uv`) ever needs a runtime-manual layer? The
  current design commits to C2 (layer-6 sentinel) for cargo only; if
  the pattern generalizes, the sentinel approach scales worse than a
  flag. The design should state a revisit trigger.
- **Q-C2:** Is layer 6 intended to be cargo-only, or a general
  "runtime-manual" layer for any manager? The design's §3 I3 says
  "layer = 6 = runtime-manual reference list" without a manager
  qualifier, but all examples are cargo. If general, spec 02 should
  say so; if cargo-only, the heading "Layer 6 — runtime-manual"
  (manager-agnostic) is misleading when a non-cargo layer-6 entry
  appears.
- **Q-C3:** Does the design intend to update the spec 02 Contract
  table's `layer` row (F1), or only add a prose note? The §4.5 wording
  ("a prose note to the `cargo` manager rule") suggests the latter,
  which is insufficient.