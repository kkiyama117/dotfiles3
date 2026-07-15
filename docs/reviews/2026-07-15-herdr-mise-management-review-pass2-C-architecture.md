# herdr-mise-management — Review pass-2 (Letter C: architecture / senior engineering)

**Date:** 2026-07-15
**Reviewer:** Cursor parent agent (Pi review capacity exhausted)
**Subject:** [`../specifications/implementations/2026-07-15-herdr-mise-management-design.md`](../specifications/implementations/2026-07-15-herdr-mise-management-design.md)
**Implementation evidence:** [`../issues/2026-07-15-phase-herdr-mise-management.md`](../issues/2026-07-15-phase-herdr-mise-management.md)
**Pass:** 2
**Status:** done

## Verdict

**Approve.** The migration establishes one install/version/update authority
without adding a new manager or installer abstraction. Normative and
historical documents are synchronized.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| C3 | LOW | RESOLVED | `container/Containerfile`; `dot_config/mise/config.toml:68`; runtime acceptance | The carried stale-binary/shim-precedence risk is closed by removing Layer 3-8 and verifying both shim resolution and old-path absence |

### C3 details

Pass 1 carried the risk that a stale `~/.local/bin/herdr` could compete with
the mise shim. The bespoke image install is gone, the one-time mise-volume
migration was executed, `which herdr` resolves under `$MISE_DATA_DIR/shims`,
and `test ! -x "$HOME/.local/bin/herdr"` passed.

**Verification:** policy test
`test_containerfile_has_no_bespoke_herdr_install` plus result-log S3/S5.

## Verified premises

- P1: `dot_config/mise/config.toml` is the only hand-edited source for the
  Herdr tool identifier and version policy.
- P2: Removing Herdr from `packages.toml` follows the existing contract:
  mise-managed tools are declared outside the dependency generator, and
  `manager = "mise"` remains rejected.
- P3: The Containerfile consumes the rendered mise config through the
  existing generic Layer 3-4 path; there is no Herdr-specific install logic.
- P4: Specs 02, 20, and 21 consistently describe mise ownership, preserve
  stable invariant IDs I-HERDR1..I-HERDR3 and acceptance criterion #25, and
  contain no pinned-binary normative residue.
- P5: The old design is marked `superseded`; the old plan is marked
  `executed` and accurately records the shipped direct-install block; the old
  closed issue and result-log remain unchanged.
- P6: Selecting `latest` is an explicit policy tradeoff documented in the
  approved design and spec 20, not an accidental loss of a pin.

## Open questions

- None.
