# AGENTS.md

Common protocol for AI agents and human maintainers performing review, design,
and implementation in this repository. Document placement and lifecycle
themselves are defined in
[`docs/specifications/00-document-management.md`](docs/specifications/00-document-management.md)
(the SoT). This file complements it with **role definitions** and **output
schemas**.

---

## §1 Scope

- Target repository: `dotfiles3` (chezmoi source + Podman container)
- Applies to: every action that produces a design / plan / review / result-log
- Out of scope for this file:
  - Document placement & naming → [`00-document-management.md`](docs/specifications/00-document-management.md)
  - Coding standards → `~/.config/claude/rules/ecc/common/coding-style.md`
  - Secret management → [`docs/specifications/11-pre-required-env-values.md`](docs/specifications/11-pre-required-env-values.md)

---

## §2 Review protocol

### 2.1 Pass / Letter model

Reviews are tracked on two axes: **pass-N** (iteration count) × **letter**
(perspective). File names follow
`YYYY-MM-DD-<slug>-review-passN-<letter>-<topic>.md`.

| Letter | Perspective | Primary agent | Reads | Expected output |
|---|---|---|---|---|
| A | factual / correctness | any reviewer agent | target design + cited sources | mismatches between claims and citations, false premises, logical gaps |
| B | security | `ecc:security-reviewer` | target design + secret / network / privilege paths | OWASP-class issues, secret leakage, privilege escalation, rootless violations |
| C | architecture / senior engineering | `ecc:architect` or `ecc:code-architect` | target design + neighboring specs | design coherence, alternatives, complexity, maintainability |
| D | consistency / cross-doc | any reviewer agent | target design + all `specifications/` + existing designs | naming, link, section-number, and contradictions vs. prior specs |
| E | operability / runtime | any reviewer agent | target design + `Makefile` + `Containerfile` + `dependencies/` | feasibility of build / apply / rollback, alignment with Make targets |

> **NOTE**: the specific A-E assignments above are **provisional**.
> `00-document-management.md` did not define them, so the table follows the
> "split role" convention from `common/agents.md`
> (factual / senior eng / security / consistency). If the operational
> mapping differs, rewrite this table only — other specs reference the
> letter glyphs, not their semantics.

### 2.2 Required letters

| Design class | Required letters |
|---|---|
| touches secret / auth / network / privilege | **A + B + D** |
| changes Containerfile / Makefile / build flow | **A + C + E** |
| changes docs conventions / repository structure | **A + D** |
| any other ordinary design | **A** (minimum) |

### 2.3 Pass termination conditions

- Every finding is in one of: `RESOLVED` / `addressed` / `INCOMPLETE` (with stated reason)
- A single remaining `open` / `REGRESSION` / `blocked` mandates another pass
- Once the design side has acknowledged every per-letter finding, the author (or an agent) produces an aggregate review (`-passN.md`, no letter suffix) and hands it back

---

## §3 Common output schema

Every review (per-letter or aggregate) consists of the following five blocks.

```markdown
# <slug> — Review pass-<N> (Letter <letter>: <topic>)

**Date:** YYYY-MM-DD
**Reviewer:** <agent name or human>
**Subject:** [<relative path to design>](...)
**Pass:** <N>
**Status:** in-review | done

## Verdict
<Approve / Approve with conditions / Request changes / Block> + 1-3 line summary

## Findings
| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| F1 | CRITICAL/HIGH/MEDIUM/LOW | open/RESOLVED/REGRESSION/INCOMPLETE/addressed/blocked | `path:line` or `§N.M` | <one line> |

### F<n> details
<quote + suggested fix + verification steps>

## Verified premises
- P1: <a fact the design assumes implicitly that the reviewer has confirmed>

## Open questions
- Q1: <question for the design author; must be answered before the next revise>
```

### 3.1 Severity

| Severity | Meaning | Effect on pass termination |
|---|---|---|
| CRITICAL | data loss / secret leak / build broken | **MUST be RESOLVED** before moving to the next phase |
| HIGH | spec violation / serious bug / missing required review item | RESOLVED by default; explicit defer requires INCOMPLETE with a reason |
| MEDIUM | maintainability degradation / duplication / naming inconsistency | may stay `addressed` and carry to the next pass |
| LOW | style nits / minor comments | `addressed` or batched into a later pass |

### 3.2 Status

Same vocabulary as
[`00-document-management.md` §5](docs/specifications/00-document-management.md):
`open` / `RESOLVED` / `REGRESSION` / `INCOMPLETE` / `addressed` / `blocked`.

| Status | When to use |
|---|---|
| open | just filed by the reviewer |
| RESOLVED | the design applied the fix and the reviewer re-confirmed it |
| REGRESSION | once RESOLVED, then re-introduced by a later revise |
| INCOMPLETE | the design explicitly deferred it in this pass; reason and follow-up target are mandatory |
| addressed | the design responded but not necessarily resolved (used to close out LOW/MEDIUM items) |
| blocked | waiting on another design or external factor; the blocker must be named |

---

## §4 Aggregate review

After the per-letter reviews land, the author (or an agent) produces an
aggregate version. File name:
`YYYY-MM-DD-<slug>-review-passN.md` (no letter suffix).

Minimum contents:
- Link table to every per-letter review
- Deduplicated finding list across letters
- Prioritized list of findings to address in the next revise
- Pass termination judgement (whether §2.3 is satisfied)

---

## §5 Response obligations on the design / plan / issue side

- Once a review pass arrives, the design author must **quote finding IDs verbatim** when describing the response in the next revise
- Example: `F2 (B-security, CRITICAL): RESOLVED — rewrote §4.2 to assume rootless (commit abc1234)`
- For items marked INCOMPLETE, the **follow-up design / plan path must be cited**

---

## §6 Revision procedure

This file is itself one of the specs. To revise:

1. File an issue in `docs/issues/` describing the reason
2. For large changes, go through `docs/specifications/implementation/<slug>-agents-rev-design.md`
3. Edit this file; include the issue path in the commit message
4. Synchronize cross-referencing files (e.g. `00-document-management.md`) in the same commit
