# kakehashi-container-install — Review pass-1 (Letter E: operability / runtime)

**Date:** 2026-07-16
**Reviewer:** reviewer (E-operability)
**Subject:** [../specifications/implementations/2026-07-16-kakehashi-container-install-design.md](../specifications/implementations/2026-07-16-kakehashi-container-install-design.md)
**Pass:** 1
**Status:** done

## Verdict

**Approve.** The revised design is executable against the current Makefile,
Containerfile, entrypoint, and test layout. It now documents the refresh cost,
scratch cleanup, test boundary, and zsh-safe tag check.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| E-F1 | MEDIUM | addressed | S5 / I-KAKEHASHI3 / §5.4 | The no-cache refresh had no exact command or cost disclosure |
| E-F2 | LOW | addressed | §5.1–§5.2 / §6 | Extraction scratch could survive into the final image |
| E-F3 | MEDIUM | addressed | §5.3–§5.4 | Inventory coverage and the static-versus-functional test boundary were incomplete |
| E-F4 | LOW | addressed | §5.1 | Effective-URL extraction and zsh tag validation were underspecified |

### E-F1 details

The design now provides the full `podman build --no-cache` invocation, states
that it rebuilds every layer, and records that neither the Makefile nor Podman
offers a per-layer shortcut.

### E-F2 details

Private staging now has exit cleanup on both success and failure.

### E-F3 details

Static tests now include the custom inventory contract and are explicitly
classified as regression guards. The uncached build and runtime commands are
the functional acceptance gates.

### E-F4 details

The design gives a zsh-safe `v<->.<->.<->` whole-value check and curl
`%{url_effective}` capture. The pattern was locally exercised against stable,
prerelease, truncated, and invalid tags.

## Verified premises

- P1: `install -D` creates `~/.local/bin`, satisfying the conditional PATH
  entry in `.zshenv`.
- P2: No named volume overlays `~/.local/bin`; the binary survives at runtime.
- P3: The GNU asset matches the Manjaro glibc base.
- P4: `make up` and entrypoint freshness checks require no change.
- P5: Rollback removes only the custom inventory entry, generated inventory
  output, Layer 3-8, focused tests, and synchronized specs.

## Open questions

- None.
