# kakehashi-container-install — Review pass-1 (Letter D: consistency / cross-doc)

**Date:** 2026-07-16
**Reviewer:** reviewer (D-consistency)
**Subject:** [../specifications/implementations/2026-07-16-kakehashi-container-install-design.md](../specifications/implementations/2026-07-16-kakehashi-container-install-design.md)
**Pass:** 1
**Status:** done

## Verdict

**Approve.** Naming, lifecycle, links, labels, dependency-generation rules, and
the A–E review set conform to specs 00, 02, and 09. Cross-document ambiguity
with the prior `herdr` Layer 3-8 design is addressed.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| D-F1 | MEDIUM | addressed | §2 E / I-KAKEHASHI1 | Divergence from the recent mise-first `herdr` decision lacked a cross-reference |
| D-F2 | LOW | addressed | §4 / §5.3 | Reuse of the vacated Layer 3-8 ordinal was implicit |
| D-F3 | LOW | addressed | design header | Required review letters were stated only at the end |
| D-F4 | LOW | addressed | §3 heading | Heading casing differed from the spec 00 design template |

### D-F1 details

Alternative E now links the approved `herdr` mise-management design and
explains why this tool takes a different path.

### D-F2 details

The revised design explicitly assigns `kakehashi` to Layer 3-8 and acceptance
criterion #26.

### D-F3 details

The design header now lists the required A + B + C + D + E review set.

### D-F4 details

The heading now matches `Architecture / Invariants`.

## Verified premises

- P1: The required review set is the union of network and build-flow classes in
  spec 09 §2.2.
- P2: `make gen-deps` remains the only writer of spec 02's AUTO-GEN block.
- P3: Issue and design slugs, dates, relative links, and S/I/Q labels conform
  to spec 00.
- P4: The issue and design consistently specify build-time, x86_64-only,
  unpinned-latest installation into `~/.local/bin`.

## Open questions

- None.
