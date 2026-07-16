# kakehashi-container-install — Review pass-1 (Letter C: architecture / senior engineering)

**Date:** 2026-07-16
**Reviewer:** reviewer (C-architecture)
**Subject:** [../specifications/implementations/2026-07-16-kakehashi-container-install-design.md](../specifications/implementations/2026-07-16-kakehashi-container-install-design.md)
**Pass:** 1
**Status:** done

## Verdict

**Approve.** The custom Layer 3 design now documents why it intentionally
diverges from the mise-managed `herdr` precedent, states its testability
boundary, and gives the build-flow integration exact identifiers.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| C-F1 | HIGH | RESOLVED | §1 / §2 E | The mise/aqua rejection lacked registry evidence and reconciliation with the approved `herdr` direction |
| C-F2 | MEDIUM | addressed | §2 B / §5.4 | Inline moving-release logic had only static regression coverage |
| C-F3 | LOW | addressed | §4 / §5.3 | Layer and acceptance ordinals and inventory insertion point were unspecified |
| C-F4 | MEDIUM | addressed | S5 / I-KAKEHASHI3 / §5.4 | "Latest" and the full-rebuild refresh cost needed precise operator semantics |

### C-F1 details

`mise registry` and an aqua-registry code search returned no `kakehashi`
package on 2026-07-16. Upstream recommends downloading a release binary and
placing it on `PATH`. The revised alternative analysis links the `herdr`
mise-management design and records that the user selected the literal
`~/.local/bin` path after being offered a mise-shim alternative.

### C-F2 details

The design now states that static checks are regression guards and an uncached
image build is the functional gate. It also defines when extracting a dedicated
installer script becomes justified.

### C-F3 details

The design now names Layer 3-8, spec 21 acceptance criterion #26, and placement
with the custom Layer 3 inventory entries.

### C-F4 details

The revised text distinguishes latest-at-layer-execution from a live latest
guarantee and documents the full no-cache Podman build needed to refresh.

## Verified premises

- P1: `custom` entries appear in spec 02 but generate no manager install list.
- P2: Layer 3-8 is free after the `herdr` installer migration.
- P3: `~/.local/bin` is not hidden by a named runtime volume.
- P4: Scope and rollback remain focused and reversible.

## Open questions

- None.
