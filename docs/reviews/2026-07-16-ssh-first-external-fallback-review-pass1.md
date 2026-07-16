# ssh-first-external-fallback — Review pass-1 (aggregate)

**Date:** 2026-07-16
**Reviewer:** Cursor
**Subject:** [SSH-first external repository fallback design](../specifications/implementations/2026-07-16-ssh-first-external-fallback-design.md)
**Pass:** 1
**Status:** done

## Verdict

Approve. All transport-design findings are RESOLVED. D-F4 is INCOMPLETE with
a stated out-of-scope reason and named follow-up design paths, so the pass
termination conditions in spec 09 §2.3 are satisfied.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| A-F1 / D-F2 | HIGH | RESOLVED | `§1 S6`, `§3 I10`, `§4` | Forward all URL/ref overrides through `make up`. |
| A-F2 / B-F1 | HIGH | RESOLVED | `§3 I6`, `§5`, `§6` | Bound the complete probe and force-kill an unresponsive child. |
| A-F3 | MEDIUM | RESOLVED | `§6` | Test selected values at the chezmoi render boundary. |
| A-F4 | LOW | RESOLVED | `§3 I5`, `§5` | Treat only non-empty values as explicit overrides. |
| B-F2 | MEDIUM | RESOLVED | `§3 I9`, `§4`, `§6` | Quote URL/ref data at the final TOML sink. |
| B-F3 | MEDIUM | RESOLVED | `§3 I7`, `§5` | Preserve host-key checking and use fixed HTTPS fallbacks. |
| B-F4 | MEDIUM | RESOLVED | `§3 I5/I11`, `§5`, `§6` | Reject credential-bearing HTTP(S) overrides without logging values. |
| D-F1 | HIGH | RESOLVED | `§1 S1`, `§3 I8`, `§5` | Enforce selected transport on existing checkouts. |
| D-F3 | MEDIUM | RESOLVED | `§4` | Synchronize specs 11 and 21. |
| D-F4 | MEDIUM | INCOMPLETE | `§7` | Defer pre-existing lifecycle drift to named prior designs. |
| A-F5 / B-F5 / D-F5 | HIGH | RESOLVED | `§3 I6a`, `§5`, `§6` | Keep selection in the parent shell and test SIGTERM forwarding. |

### Finding details

The revised design incorporates every in-scope A, B, and D finding. The
implementation plan must preserve the exact timeout, validation, migration,
quoting, documentation, and regression-test requirements.

## Verified premises

- [Letter A review](2026-07-16-ssh-first-external-fallback-review-pass1-A-correctness.md)
- [Letter B review](2026-07-16-ssh-first-external-fallback-review-pass1-B-security.md)
- [Letter D review](2026-07-16-ssh-first-external-fallback-review-pass1-D-consistency.md)
- Required review letters A+B+D were completed.
- No `open`, `REGRESSION`, or `blocked` finding remains.

## Open questions

- Q1: None.
