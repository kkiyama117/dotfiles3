# kakehashi-container-install — Review pass-1 (Letter A: factual / correctness)

**Date:** 2026-07-16
**Reviewer:** reviewer (A-factual)
**Subject:** [../specifications/implementations/2026-07-16-kakehashi-container-install-design.md](../specifications/implementations/2026-07-16-kakehashi-container-install-design.md)
**Pass:** 1
**Status:** done

## Verdict

**Approve.** Repository and upstream premises are accurate. The revised design
closes the path, inventory-placement, and archive-evidence ambiguities.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| A-F1 | LOW | addressed | §3 I-KAKEHASHI2 / §5.2 | `$HOME` and `/home/${USERNAME}` path notation needed an explicit equivalence |
| A-F2 | LOW | addressed | §4 step 2 / §5.3 | "Alphabetically placed" conflicted with the currently grouped Layer 3 section |
| A-F3 | LOW | RESOLVED | §1 / §5.2 | The one-member archive premise needed direct evidence |

### A-F1 details

The design now states that `$HOME` is `/home/${USERNAME}` in the toolchain
stage and consistently specifies `$HOME/.local/bin/kakehashi` as the install
command destination.

### A-F2 details

The design now places the declaration alongside other custom Layer 3 entries
without claiming that the existing section is alphabetically ordered.

### A-F3 details

The v0.8.0 x86_64 GNU/Linux archive was downloaded and inspected on
2026-07-16. `tar -tvzf` reported exactly one regular executable member named
`kakehashi`.

## Verified premises

- P1: `dot_zshenv.tmpl` conditionally adds `$HOME/.local/bin` to `PATH`; the
  build-time install creates that directory.
- P2: GitHub's latest stable release is v0.8.0 and its x86_64 GNU/Linux asset
  name matches the design.
- P3: The toolchain stage runs as `${USERNAME}` and has curl and tar available.
- P4: `manager = "custom", layer = 3` is a doc-only inventory pattern already
  used by Layer 3 tools.

## Open questions

- None.
