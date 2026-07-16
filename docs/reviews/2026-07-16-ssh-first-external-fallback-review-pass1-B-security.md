# ssh-first-external-fallback — Review pass-1 (Letter B: security)

**Date:** 2026-07-16
**Reviewer:** Cursor general-purpose reviewer
**Subject:** [SSH-first external repository fallback design](../specifications/implementations/2026-07-16-ssh-first-external-fallback-design.md)
**Pass:** 1
**Status:** done

## Verdict

Approve with conditions. The revised design preserves SSH host-key checking,
uses fixed HTTPS fallbacks, bounds probe execution, quotes external data, and
rejects credential-bearing HTTP(S) overrides.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| B-F1 | HIGH | RESOLVED | `§3 I6`, `§5`, `§6` | The complete probe is bounded, including a forced-kill grace. |
| B-F2 | MEDIUM | RESOLVED | `§3 I9`, `§4`, `§6` | URL/ref values are quoted at the final TOML sink. |
| B-F3 | MEDIUM | RESOLVED | `§3 I7`, `§5` | Host-key checks remain enabled and fallback URLs are fixed constants. |
| B-F4 | MEDIUM | RESOLVED | `§3 I5/I11`, `§5`, `§6` | Credential-bearing overrides are rejected without logging their values. |
| B-F5 | MEDIUM | RESOLVED | `§3 I6a`, `§5`, `§6` | Selection remains in the parent shell so signal traps can reach the probe. |

### B-F1 details

`ConnectTimeout` alone does not bound a connected but stalled Git server. The
revised design wraps the full probe in a ten-second timeout with a two-second
forced-kill grace.

### B-F2 details

Environment-derived URL/ref data must be quoted where
`.chezmoiexternal.toml.tmpl` emits TOML, with metacharacter regression tests.

### B-F3 details

The probe does not weaken host-key policy. Unknown or changed keys count as a
failed SSH probe and select the repository's hardcoded public HTTPS URL.

### B-F4 details

URL overrides are non-secret configuration. HTTP(S) userinfo is rejected, and
warnings do not print arbitrary override values.

### B-F5 details

Parent-shell output assignment preserves the entrypoint's `child_pid`, and a
SIGTERM-during-probe test is required.

## Verified premises

- `BatchMode=yes` suppresses credential prompts without disabling host-key
  checking.
- The persistent SSH volume can retain config, keys, and known hosts.
- Default SSH and fallback HTTPS URLs contain no credentials.
- Selection occurs before Bitwarden authentication and does not expose
  Bitwarden values.

## Open questions

- Q1: None.
