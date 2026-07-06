# cargo-install — Review pass-1 (Letter A: factual)

**Date:** 2026-07-02
**Reviewer:** review subagent (Letter A — factual / correctness)
**Subject:** [`docs/specifications/implementations/2026-07-02-cargo-install-design.md`](../specifications/implementations/2026-07-02-cargo-install-design.md)
**Pass:** 1
**Status:** done

## Verdict

**Approve.** The design's factual foundation is solid. Every key claim about
the existing codebase (packages.toml entries, Containerfile layer structure,
generator behavior, EXPECTED_EMPTY_FILES, schema version, current cargo
inventory) was verified against the cited sources and confirmed accurate.
Three LOW-severity findings are noted — one unsupported attribution in §C2,
one wording-precision issue in §S3, and one stale-comment gap — none of which
undermine the design's correctness or block implementation.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| F1 | LOW | open | design §C2 (alternatives) | "user explicitly offered 'new number or new flag'" not found in cited issue |
| F2 | LOW | open | design §S3 / §C2 | "no functional generator change" is imprecise: a `render_doc_block` heading edit IS a generator code change (though not an emission-path change) |
| F3 | LOW | open | design §4 step 1 vs `dependencies/packages.toml` mise comment | packages.toml mise comment references "Layer 3-5"; will become stale after proposed reorder to 3-4; design does not explicitly scope updating it |

### F1 details

**Quote (design §C2):**
> Picked for minimal change and because the user explicitly offered "new
> number or new flag."

**Issue:** The cited issue
(`docs/issues/2026-07-02-cargo-install.md`) problem §3 says only:
> "This needs a new toml mechanism to mark 'declared but not installed in
> layer 3.'"

The phrase "new number or new flag" does not appear anywhere in the issue
text. The attribution may originate from an unrecorded conversation, but as
written the claim is not supported by the cited source.

**Suggested fix:** Either (a) add a pointer to the exact source (issue line,
chat log, or commit) where the user offered "new number or new flag", or (b)
soften to "the issue asks for a new toml mechanism; this design interprets
that as a choice between a new layer number or a new flag, and picks the
layer number for minimal change."

**Verification steps:** `grep -rn "new number or new flag"
docs/issues/2026-07-02-cargo-install.md` → no matches.

---

### F2 details

**Quote (design §S3):**
> The generator emits `layer_<N>/<manager>.txt` for any `layer >= 1` with
> entries; `layer_6/cargo.txt` is therefore generated and is a reference
> list, not a build input.

**Quote (design §C2):**
> The generator already emits `layer_<N>/<manager>.txt` for any `layer >= 1`
> with entries, so `layer_6/cargo.txt` is produced with **zero functional
> generator change** — only a 2-line spec-02 heading special-case (layer 6
> → "runtime-manual").

**Issue:** The phrase "zero functional generator change" / "no functional
generator change" (§S3) could be misread as "no generator code change at
all." The design does propose a code change to `render_doc_block` (§5.3,
adding a `layer == 6` heading branch). The distinction is correct — the txt
*emission* path (`write_txt_files`) needs no change, only the *doc-block
heading* renderer — but the shorthand in §S3 omits this qualifier.

**Suggested fix:** In §S3, change "no functional generator change" to "no
change to the txt emission path (`write_txt_files`); only a `render_doc_block`
heading special-case for layer 6 is added (see §5.3)."

**Verification steps:** `grep -n "render_doc_block\|write_txt_files" design`
→ confirm §5.3 proposes a `render_doc_block` edit; `grep -n "no functional
generator change" design` → confirm the unqualified shorthand in §S3.

---

### F3 details

**Quote (`dependencies/packages.toml`, mise comment block, ~line 87):**
> # Layer 3: mise-managed languages (Containerfile `toolchain` stage, Layer
> 3-5).

**Issue:** The design's §5.2 proposes reordering the toolchain sub-layers so
that mise-managed languages move from Layer 3-5 to Layer 3-4. After this
reorder, the packages.toml comment "Layer 3-5" becomes stale. The design's
§4 step 1 says "Update stale comments mentioning layer numbers if any" but
scopes that to the *generator* file (`programs/generate_deps/main.py`), not
to `packages.toml`. The packages.toml mise comment is not explicitly scoped
for update.

**Suggested fix:** Extend §4 step 2 (SoT — packages.toml) to include:
"update the mise comment block's layer reference from 'Layer 3-5' to 'Layer
3-4' to match the reordered Containerfile."

**Verification steps:** After implementation, `grep -n "Layer 3-5"
dependencies/packages.toml` → should return no mise-comment matches (the
Layer 3-5 reference should be updated to 3-4 or removed).

---

## Verified premises

- **P1:** `cargo-binstall` is NOT an active entry in `packages.toml` today.
  It appears only in a commented-out TODO block
  (`dependencies/packages.toml`, the `# TODO: Plan, review, implement` section
  with `#[[tool]] #name = "cargo-binstall"`). Verified by reading the full
  file — no active `[[tool]]` entry has `name = "cargo-binstall"`.

- **P2:** `rustup` and `mise` are curl-bootstrapped in the Containerfile and
  are NOT in `packages.toml`. Containerfile Layer 3-2 runs
  `curl ... https://sh.rustup.rs | sh -s -- -y ...` (`container/Containerfile`
  Layer 3-2); Layer 3-3 runs `curl https://mise.run | sh` (Layer 3-3). Neither
  has a `[[tool]]` entry in `packages.toml`. ✓

- **P3:** The generator emits `layer_<N>/<manager>.txt` for any `layer >= 1`
  with entries. `programs/generate_deps/main.py` `write_txt_files`:
  `if layer < 1: continue` then loops `for mgr in LIST_MANAGERS: entries =
  by_mgr.get(mgr); if not entries: continue; out = DEPS_DIR / f"layer_{layer}"
  / f"{mgr}.txt"`. `cargo` is in `LIST_MANAGERS`. So `layer = 6` cargo entries
  would produce `layer_6/cargo.txt` with no emission-path change. ✓

- **P4:** `EXPECTED_EMPTY_FILES = ((3, "cargo"), (4, "paru"), (3, "mise"))`
  exactly as the design claims (`programs/generate_deps/main.py`, lines
  ~44-48). ✓

- **P5:** Current Containerfile Layer 3-4 uses `cargo install --locked`
  reading `layer_3/cargo.txt`. Verified at `container/Containerfile` Layer
  3-4: `COPY --from=deps layer_3/cargo.txt /tmp/cargo_tools.txt` →
  `cargo install --locked ${=pkgs}`. ✓

- **P6:** `layer_3/cargo.txt` is currently empty (0 packages). Verified by
  reading the generated file: header + `# manager: cargo | layer: 3 |
  packages: 0` + no entries. Consistent with `packages.toml` having no active
  `manager = "cargo"` entries. ✓

- **P7:** All 5 runtime-manual package names are present in
  `docs/references/current_cargo_installed.md`: `cargo-outdated v0.19.0`,
  `cargo-expand v1.0.123`, `cargo-edit v0.13.11`, `cargo-zigbuild v0.23.0`,
  `maturin v1.14.0`. ✓

- **P8:** Current Containerfile Layer 3-5 does `mise install ${=pkgs}` +
  `mise use -g ${=pkgs}`. Verified at `container/Containerfile` Layer 3-5. ✓

- **P9:** `schema = 1` in `dependencies/packages.toml` (first non-comment
  line). Generator `SCHEMA = 1` and `load_tools` checks
  `data.get("schema") != SCHEMA`. ✓

- **P10:** `render_doc_block` has a layer-0 special case:
  `heading = (f"#### Layer {layer} — already in the base image" if layer == 0
  else f"#### Layer {layer} — install list")`. The design's proposed layer-6
  branch mirrors this pattern. ✓

- **P11:** The Containerfile build reads `layer_1/pacman.txt` (Layer 1-2),
  `layer_3/cargo.txt` (Layer 3-4), `layer_3/mise.txt` (Layer 3-5), and
  `layer_4/paru.txt` (Layer 4-2). It does NOT read `layer_6/cargo.txt`. ✓

- **P12:** `programs/generate_deps/tests/test_cargo_manager.py` exists and
  tests: `cargo` in `LIST_MANAGERS`, `validate` accepts cargo manager,
  `render_packages_txt` emits cargo entries, `write_txt_files` creates
  `layer_3/cargo.txt`, and empty-cargo-txt emission. ✓

- **P13:** `docs/specifications/20-container-rules.md` exists with invariants
  I4/I5/I6/I8 and I-AUR1–4. No `I-CARGO` invariant exists yet; the design
  proposes adding `I-CARGO1`. ✓

- **P14:** Two unresolved TODOs exist in `packages.toml`: (1)
  `# TODO: Write this `Rust packages rule` into docs` (Layer 4 paru comment
  block); (2) `# TODO: Plan, review, implement` (cargo-binstall/topgrade
  commented-out block). ✓

- **P15:** Build stages are 0–5 (0 base image, 1 base/pacman, 2
  build-prepass, 3 toolchain, 4 aur, 5 runtime). The design's claim that
  "layer 6 reads as post-final-image / runtime" is semantically consistent:
  no Containerfile stage 6 exists. ✓

- **P16 (observation):** `spec 02` contract table says `layer | yes | integer
  ≥ 1`, but `packages.toml` already has `pacman` at `layer = 0` and the
  generator `validate` allows `layer >= 0` (not `>= 1`). This is pre-existing
  spec drift, NOT introduced by this design. The design's `layer = 6` is
  within both constraints. No design error; noted for completeness.

## Open questions

- **Q-A1 (for design author, from F1):** Where does the quote "new number or
  new flag" originate? If from an unrecorded conversation, consider softening
  the attribution or adding a citation. (Non-blocking; LOW.)
- **Q-A2 (for design author, from F3):** Should the packages.toml mise
  comment ("Layer 3-5") be explicitly scoped for update in §4 step 2, given
  the reorder moves mise languages to 3-4? (Non-blocking; LOW.)