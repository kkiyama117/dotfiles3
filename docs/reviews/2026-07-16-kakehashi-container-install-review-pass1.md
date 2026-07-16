# kakehashi-container-install — Review pass-1 aggregate

**Date:** 2026-07-16
**Subject:** [../specifications/implementations/2026-07-16-kakehashi-container-install-design.md](../specifications/implementations/2026-07-16-kakehashi-container-install-design.md)
**Issue:** [../issues/2026-07-16-kakehashi-container-install.md](../issues/2026-07-16-kakehashi-container-install.md)
**Required letters:** A + B + C + D + E

## Letter reviews

| Letter | Verdict | File |
|---|---|---|
| A — factual / correctness | Approve | [A-factual](2026-07-16-kakehashi-container-install-review-pass1-A-factual.md) |
| B — security | Approve with conditions | [B-security](2026-07-16-kakehashi-container-install-review-pass1-B-security.md) |
| C — architecture | Approve | [C-architecture](2026-07-16-kakehashi-container-install-review-pass1-C-architecture.md) |
| D — consistency | Approve | [D-consistency](2026-07-16-kakehashi-container-install-review-pass1-D-consistency.md) |
| E — operability | Approve | [E-operability](2026-07-16-kakehashi-container-install-review-pass1-E-operability.md) |

## Findings (deduplicated)

| IDs | Priority | Status | Response |
|---|---|---|---|
| B-F1, B-F4, E-F4 | 1 | addressed | Hardcode the asset base and use fail-closed curl/zsh tag validation |
| B-F2 | 1 | addressed | Reject non-regular and symlink archive members |
| B-F3, E-F2 | 1 | addressed | Use private staging with exit cleanup |
| C-F1, D-F1 | 2 | RESOLVED | Record registry evidence, the `herdr` precedent, and the user's explicit path choice |
| C-F4, E-F1 | 2 | addressed | Define latest-at-build semantics and the exact full no-cache refresh |
| C-F2, E-F3 | 2 | addressed | State static coverage limits and retain image build as functional gate |
| C-F3, D-F2 | 3 | addressed | Assign Layer 3-8 and acceptance #26 explicitly |
| A-F1, A-F2, D-F3, D-F4 | 3 | addressed | Clarify path, placement, header, and template wording |
| A-F3 | 3 | RESOLVED | Verify the release archive directly |

## Design-side responses

The revised design quotes every finding ID in §9 and applies the responses
summarized above. The unpinned latest-release supply-chain boundary is an
explicit user-selected policy and verified premise, not an unresolved claim of
cryptographic authenticity. Implementation must preserve the documented
hardening and functional build gate.

## Pass termination judgement

Every finding is `RESOLVED` or `addressed`. No `open`, `REGRESSION`, `blocked`,
or `INCOMPLETE` item remains, so spec 09 §2.3 is satisfied.

**Aggregate verdict: Approve.** The design may proceed to implementation
planning.

## Residual risks

1. A compromised upstream/GitHub release can pass shape and version checks.
2. Cached builds may retain an older release until a full no-cache rebuild.
3. Static tests do not execute network redirects or adversarial archives; the
   image build remains the functional acceptance gate.
