# kakehashi-global-config — Review pass-1 (Letter D: consistency)

**Date:** 2026-08-04
**Reviewer:** Reviewer-D
**Subject:** [Global kakehashi configuration design](../specifications/implementations/2026-08-04-kakehashi-global-config-design.md)
**Pass:** 1
**Status:** done

## Verdict

**Request changes.** The proposed TOML and the design's §5.1 table are
consistent, and the generated Layer 4 / spec 02 effects fit the existing build
flow. However, the inventory-sync invariant is not implementable as written,
the spec 24 rationale uses criteria outside their scope, and the asserted spec
20 non-change conflicts with I-KAKEHASHI6's current wording.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| D-F1 | HIGH | open | `docs/specifications/implementations/2026-08-04-kakehashi-global-config-design.md:84-88` | “Three-way inventory sync” incorrectly requires unlike inventories to agree. |
| D-F2 | MEDIUM | open | `docs/specifications/implementations/2026-08-04-kakehashi-global-config-design.md:70-75` | The rust-analyzer manager decision is attributed to spec 24 criteria that do not apply. |
| D-F3 | MEDIUM | open | `docs/specifications/implementations/2026-08-04-kakehashi-global-config-design.md:92-94,115-116` | “No spec 20 change” conflicts with I-KAKEHASHI6's claim that the build creates no configuration. |
| D-F4 | MEDIUM | open | `docs/specifications/implementations/2026-08-04-kakehashi-global-config-design.md:7,15-20,48-50,73-74` | Spec and source references do not follow spec 00 §7 link/deep-anchor rules. |
| D-F5 | LOW | open | `docs/specifications/implementations/2026-08-04-kakehashi-global-config-design.md:45-47,160-164` | The mise delta is described as adding entries that are already tracked, obscuring the actual change. |

### D-F1 details

I-KC2 says the kakehashi `languageServers` keys, mise `[tools]`, and
`packages.toml` “must agree on the server inventory.” They cannot be equal:

- `clangd` is provided by the `clang` package and is intentionally absent from
  nvim's `bridged_servers`.
- `rust_analyzer` is represented by the differently named
  `rust-analyzer` package.
- `denols` is provided by the `deno` runtime entry.
- mise also contains `StyLua`, which is a formatter, not one of the eight
  `languageServers`.

The proposed static test therefore needs a mapping/coverage contract, not set
equality. Define the authoritative eight-server catalog and map each server to
its install provider (`mise` tool key or `packages.toml` package); treat the
nvim list as a deliberate seven-server subset and formatters as separate.

### D-F2 details

Spec 24 §1 says packages that do **not** depend on the Rust toolchain use the
normal pacman/paru rules and are out of scope. Its §2 `paru` branch additionally
requires a stable prebuilt **AUR** binary. The design says the official
`extra/rust-analyzer` package has no Rust toolchain dependency and is not AUR,
so it does not “satisfy spec 24 §2's paru criteria.”

The selected declaration is nevertheless supported by spec 02's paru rule,
which explicitly permits official-repository packages assigned to Layer 4.
Replace the spec 24 justification with that spec 02 rule and state that spec 24
is inapplicable.

### D-F3 details

Spec 20 I-KAKEHASHI6 currently says the build “creates no configuration.”
Under spec 21 Stage 2 and spec 13 §5a, an unguarded non-secret chezmoi file is
rendered into `/tmp/build-home`; therefore the new kakehashi TOML will exist in
build scratch before Stage 5 removes it. The stronger invariant “no runtime
state or configuration is baked into the final image” still holds, and spec
21's stage structure does not need to change.

Either narrow I-KAKEHASHI6 to the final-image property while explicitly
allowing deleted build-prepass config, or revise the design's non-change claim.
No Containerfile or Makefile edit is implied by this documentation correction.

### D-F4 details

The design contains only one Markdown link. References such as “spec 09
§2.2,” “spec 02,” and “spec 24 §2” are plain text with no target or section
anchor, contrary to spec 00 §7. The upstream `docs/README.md` wording is also
ambiguous with this repository's own `docs/README.md`, and the nvim source
references are unlinked paths in an external checkout.

Convert repository references to Markdown links and section references to
anchored links. Use explicit upstream URLs (or a repository reference document
with URL and retrieval date) for upstream and external-checkout evidence.

### D-F5 details

The cited `dot_config/mise/config.toml` already contains every tool listed in
§5.3, and `git diff` reports no uncommitted mise change. Its current comment
mentions only nvim `bridged_servers`, not all three sync targets. Thus the
actual proposed mise delta is a comment update, not adding the tool entries
described by S2.

Rewrite S2/§5.3 to distinguish pre-existing tracked tools from the planned
comment change. This also keeps the implementation plan and changed-file
expectations accurate.

## Verified premises

- P1: Parsed TOML comparison confirms every `cmd`, `languages`, and
  `workspaceMarkers` value in design §5.1 matches all eight entries in
  `dot_config/kakehashi/kakehashi.toml`; no §5.1/config contradiction was
  found.
- P2: The `2026-08-04` date and `kakehashi-global-config` slug are consistent
  across issue, design, prompt, and requested review filename, satisfying spec
  00 §3.1-§3.2 and spec 09 §2.
- P3: Flipping kakehashi `has_configs` to true and adding
  `rust-analyzer` as `manager = "paru", layer = 4` will make `make gen-deps`
  update spec 02's AUTO-GEN rows and `dependencies/layer_4/paru.txt`.
- P4: The generated Layer 4 entry is consumed by the existing spec 21
  `aur` Stage 4-2 flow and is consistent with spec 20 I5, I8, and I-AUR2.
  This requires no Containerfile or Makefile edit.
- P5: The nvim bridge contract can remain unchanged: its seven
  `bridged_servers` deliberately exclude `clangd`, while the global config can
  expose clangd to other editors and the CLI.
- P6: No date or slug convention violation was found.

## Open questions

- Q1: Will the config-sync test validate an explicit server-to-provider
  mapping and the intentional nvim subset, rather than equality among the
  three files?
- Q2: Will spec 20 I-KAKEHASHI6 be narrowed to “no configuration baked in the
  final image,” or will the kakehashi file be excluded from the build pre-pass?
