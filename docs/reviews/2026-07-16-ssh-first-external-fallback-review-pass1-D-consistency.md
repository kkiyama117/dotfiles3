# ssh-first-external-fallback — Review pass-1 (Letter D: consistency)

**Date:** 2026-07-16
**Reviewer:** Cursor general-purpose reviewer
**Subject:** [SSH-first external repository fallback design](../specifications/implementations/2026-07-16-ssh-first-external-fallback-design.md)
**Pass:** 1
**Status:** done

## Verdict

Approve with one documented incomplete lifecycle item. The revised design
aligns new and existing checkout behavior, forwards overrides, and includes
both affected normative specifications.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| D-F1 | HIGH | RESOLVED | `§1 S1`, `§3 I8`, `§5` | Selected transport is enforced on existing managed checkouts. |
| D-F2 | HIGH | RESOLVED | `§1 S6`, `§3 I10`, `§4` | The supported `make up` path forwards URL/ref overrides. |
| D-F3 | MEDIUM | RESOLVED | `§4` | Specs 11 and 21 are both included in synchronization scope. |
| D-F4 | MEDIUM | INCOMPLETE | `§7` | Lifecycle drift in prior pi/nvim designs is deferred to named design documents. |
| D-F5 | MEDIUM | RESOLVED | `§3 I6a`, `§5`, `§6` | Signal-safe parent-shell selection and regression coverage are specified. |

### D-F1 details

The maintainer chose to enforce the selected transport on existing checkouts.
Remote migration is required before apply and failure is fatal.

### D-F2 details

The design now covers all four URL/ref environment variables in `make up`.

### D-F3 details

Spec 21 synchronization must update the runtime entrypoint description, the
obsolete direct-clone notes, and acceptance criterion 19.

### D-F4 details

Prior design lifecycle drift predates this transport fix and does not change
its behavior. Follow-up targets are
[`2026-07-14-pi-config-direct-clone-design.md`](../specifications/implementations/2026-07-14-pi-config-direct-clone-design.md)
and
[`2026-07-09-nvim-external-config-design.md`](../specifications/implementations/2026-07-09-nvim-external-config-design.md).

### D-F5 details

The selector must not run in command substitution. The planned signal test
guards this invariant.

## Verified premises

- The issue/design/review slug and links follow spec 00.
- The design has required S/I/Q labels and required A+B+D review.
- `.chezmoi.toml.tmpl` already contains both SSH defaults.
- Spec 21 contains obsolete pi direct-clone and HTTPS-default text that this
  implementation must update.

## Open questions

- Q1: None.
