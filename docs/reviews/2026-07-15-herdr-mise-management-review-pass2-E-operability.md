# herdr-mise-management — Review pass-2 (Letter E: operability / runtime)

**Date:** 2026-07-15
**Reviewer:** Cursor parent agent (Pi review capacity exhausted)
**Subject:** [`../specifications/implementations/2026-07-15-herdr-mise-management-design.md`](../specifications/implementations/2026-07-15-herdr-mise-management-design.md)
**Implementation evidence:** [`../issues/2026-07-15-phase-herdr-mise-management.md`](../issues/2026-07-15-phase-herdr-mise-management.md)
**Pass:** 2
**Status:** done

## Verdict

**Approve.** The build, one-time volume rollout, runtime discovery, restart
persistence, and regression checks all completed successfully. No operational
finding remains open.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| E1-I | LOW | RESOLVED | `docs/specifications/21-container-build-flow.md:215-227` | The manual mise-volume rollout is documented in executable order and was completed successfully |
| E2-I | MEDIUM | RESOLVED | `docs/issues/2026-07-15-phase-herdr-mise-management.md:28-36,62-69` | The mandatory build/runtime gate passed without recurrence of the aqua backend failure |

### E1-I details

The implementation used the documented sequence: build the replacement image,
stop the container, remove only `dotfiles_mise`, then start the container.
Volume evidence confirms the mise volume was recreated while the SSH, cargo,
rustup, and GnuPG volume timestamps remained unchanged.

**Verification:** result-log Phase 5.1–5.3 and volume-isolation rows.

### E2-I details

The initial cold-ish build exceeded the first worker's 20-minute process
budget during AUR work, not at mise. A cached retry completed with
`BUILD_EXIT=0`; Herdr resolved as aqua-managed version 0.7.3 and executed
successfully. The old 2026-07-09 aqua failure did not recur.

**Verification:** result-log build, mise/aqua, runtime, and regression rows.

## Verified premises

- P1: The final image was committed and tagged after a successful five-stage
  build; no Layer 3-8 Herdr step ran.
- P2: After recreating only `dotfiles_mise`, `herdr --version` succeeded,
  `which herdr` resolved to the mise shim, and `mise ls` reported aqua Herdr
  0.7.3.
- P3: Both rendered runtime config variants contain stable channel semantics
  and disabled update checks.
- P4: `make down && make up` preserved Herdr through the named mise volume.
- P5: Go, Node, and pi version checks succeeded after the migration.
- P6: Routine upgrades use
  `mise upgrade aqua:ogulcancelik/herdr`; rollback rebuilds the old install
  path and reseeds the mise volume as documented.
- P7: Cold builds may exceed 20 minutes because of unrelated AUR Layer 4
  work; this is recorded as an operational duration risk, not a Herdr failure.

## Open questions

- None.
