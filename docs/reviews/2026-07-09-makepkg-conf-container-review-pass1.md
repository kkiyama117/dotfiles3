# makepkg-conf-container — Review pass-1 (aggregate)

**Date:** 2026-07-09
**Reviewer:** parent orchestrator (aggregate of pi-subagent letters A, C, E)
**Subject:** [`docs/specifications/implementations/2026-07-09-makepkg-conf-container-design.md`](../specifications/implementations/2026-07-09-makepkg-conf-container-design.md) + commit `c2da9af`
**Pass:** 1
**Status:** done

## Verdict

**Approve.** Implementation in `c2da9af` satisfies acceptance criteria. Letter C
F1 (false `.d` bypass premise) was **RESOLVED** by revising design §4 and spec 20
`I-MAKEPKG1`. No CRITICAL or open HIGH findings remain. F2 (full-file vs
drop-in maintainability) and E-F2 (test pins exact `PKGEXT`) are optional
follow-ups.

## Per-letter reviews

| Letter | Topic | Verdict | File |
|---|---|---|---|
| A | factual / correctness | Approve | [pass1-A-factual](2026-07-09-makepkg-conf-container-review-pass1-A-factual.md) |
| C | architecture | Approve with conditions (F1 addressed) | [pass1-C-architecture](2026-07-09-makepkg-conf-container-review-pass1-C-architecture.md) |
| E | operability / runtime | Approve with conditions | [pass1-E-operability](2026-07-09-makepkg-conf-container-review-pass1-E-operability.md) |

## Deduplicated findings

| ID | Letter | Severity | Status | Summary |
|---|---|---|---|---|
| C-F1 | C | HIGH | RESOLVED | `.d` bypass premise false; design §4 + `I-MAKEPKG1` corrected |
| C-F2 | C | MEDIUM | addressed | Full 146-line copy vs idiomatic `.d` drop-in — deferred; conscious choice |
| C-F3 | C | LOW | addressed | "Before pacman -Syu" over-specifies; harmless anchor |
| C-F4 | C | LOW | blocked | S1 byte-identity vs host file unverifiable (host-only) |
| E-F1 | E | LOW | addressed | `_verify_image_fresh` won't detect makepkg rollout — documented in #24 |
| E-F2 | E | LOW | open | Test/#24 pin exact `PKGEXT`; tension with S4 toggle story |
| E-F3 | E | LOW | superseded | Incorrect "snippets no longer applied" — superseded by C-F1 fix |
| A6 | A | LOW | Note | Issue AC#2 wording imprecise but harmless |
| A7 | A | LOW | Note | Base-image default column not re-verified |

## Design responses

- **C-F1 (HIGH): RESOLVED** — design §4 retitled "interaction"; states `makepkg`
  sources `.d` after curated file; container verified `fortran.conf`/`rust.conf`
  are comment-only. `I-MAKEPKG1` updated to match.
- **C-F2 (MEDIUM): addressed** — full-file copy retained; mirrorlist precedent
  and frozen self-contained file accepted; revisit only if upstream drift becomes
  painful.
- **E-F2 (LOW): open** — if `PKGEXT` toggle becomes routine, relax test to assert
  `PKGEXT=` presence rather than exact value; not required for pass termination.

## Pass termination (spec 09 §2.3)

- No CRITICAL findings.
- No open HIGH findings (C-F1 RESOLVED).
- Letters A, C, E complete.
- **Pass 1 terminates.** Issue may close with result log.

## Open questions (non-blocking)

- Q1 (C): Re-verify `.d/` contents on `manjarolinux/base` upgrades.
- Q2 (E): Canonical default vs toggle-friendly test assertions for `PKGEXT`.
