# kakehashi-container-install — Review pass-1 (Letter B: security)

**Date:** 2026-07-16
**Reviewer:** reviewer (B-security)
**Subject:** [../specifications/implementations/2026-07-16-kakehashi-container-install-design.md](../specifications/implementations/2026-07-16-kakehashi-container-install-design.md)
**Pass:** 1
**Status:** done

## Verdict

**Approve with conditions.** The revised design fails closed on malformed
redirects and archives and accurately discloses the accepted unpinned-release
trust boundary. Implementation must preserve these checks.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| B-F1 | MEDIUM | addressed | §5.1 / I-KAKEHASHI5 | The asset host and path prefix were not explicitly hardcoded |
| B-F2 | MEDIUM | addressed | §5.2 / I-KAKEHASHI4 | Member-name checks did not reject symlinks and other non-regular members |
| B-F3 | LOW | addressed | §5.1–§5.2 | Predictable `/tmp` staging and failure cleanup were unspecified |
| B-F4 | LOW | addressed | §5.1 | Whole-string tag validation and fail-closed curl capture were underspecified |

### B-F1 details

The asset URL now has a literal GitHub repository prefix. Only the validated
tag token is derived from the effective latest-release URL.

### B-F2 details

The revised extraction contract requires a regular, non-symlink file before
installation and ignores archived ownership and permissions.

### B-F3 details

The revised design requires a private `mktemp -d` staging directory and exit
cleanup on success or failure.

### B-F4 details

The design now specifies curl `%{url_effective}` capture under
`set -eo pipefail` and a concrete zsh whole-value numeric tag check.

## Verified premises

- P1: The install runs as the non-root container user and requires no sudo.
- P2: The build step reads no secrets and creates no runtime configuration.
- P3: HTTPS-only origin and redirect protocols with TLS 1.2 minimum prevent a
  plaintext downgrade.
- P4: The user explicitly accepted an unpinned latest-release policy. The
  design correctly states that GitHub/upstream release control is the
  supply-chain trust boundary and that archive/version checks do not provide
  cryptographic identity.

## Open questions

- None. Pinning a reviewed version and digest remains the documented mitigation
  if the accepted trust policy changes.
