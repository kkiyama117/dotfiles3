# ssh-first-external-fallback — Review pass-1 (Letter A: correctness)

**Date:** 2026-07-16
**Reviewer:** Cursor general-purpose reviewer
**Subject:** [SSH-first external repository fallback design](../specifications/implementations/2026-07-16-ssh-first-external-fallback-design.md)
**Pass:** 1
**Status:** done

## Verdict

Approve with conditions. The revised design resolves the factual, timeout,
integration-test, override-semantics, and signal-forwarding findings.
Implementation and verification remain pending.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| A-F1 | HIGH | RESOLVED | `§1 S3/S6`, `§3 I10`, `§4` | `make up` now forwards all four URL/ref overrides. |
| A-F2 | HIGH | RESOLVED | `§3 I6`, `§5`, `§6` | The complete probe has a ten-second deadline and two-second forced-kill grace. |
| A-F3 | MEDIUM | RESOLVED | `§4`, `§6` | A fake-chezmoi integration test covers the render boundary. |
| A-F4 | LOW | RESOLVED | `§3 I5`, `§5` | Overrides are explicitly non-empty; empty values behave as unset. |
| A-F5 | HIGH | RESOLVED | `§3 I6a`, `§5`, `§6` | Parent-shell result assignment preserves signal forwarding during probes. |

### A-F1 details

The revised scope forwards `PI_CONFIG_URL`, `PI_CONFIG_REF`,
`NVIM_CONFIG_URL`, and `NVIM_CONFIG_REF` through the documented `make up`
path and requires a regression test.

### A-F2 details

The revised design supplements OpenSSH's connection timeout with an outer
wall-clock deadline and forced-kill grace around the complete
`git ls-remote`.

### A-F3 details

The test plan requires a fake `chezmoi` to observe the independently selected
render environment, preventing selector-only tests from missing integration
wiring errors.

### A-F4 details

The design aligns override semantics with the template's treatment of empty
environment values.

### A-F5 details

The selector assigns `SELECTED_EXTERNAL_URL` in the parent shell rather than
using command substitution. The planned SIGTERM regression test verifies
child termination and status 143.

## Verified premises

- Both committed config defaults are the required GitHub SSH URLs.
- The current entrypoint unconditionally replaces both defaults with HTTPS.
- The two externals consume their URL fields independently.
- Existing managed checkouts require remote migration for the selected
  transport to affect pulls.
- Fake executables on `PATH` can test selection without contacting GitHub.

## Open questions

- Q1: None.
