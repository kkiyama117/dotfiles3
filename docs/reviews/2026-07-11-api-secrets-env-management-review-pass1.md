# api-secrets-env-management — Review pass-1 (aggregate)

**Date:** 2026-07-12
**Reviewer:** parent orchestrator (aggregate of pi-subagent letters A, B, D)
**Subject:** [`docs/specifications/implementations/2026-07-11-api-secrets-env-management-design.md`](../specifications/implementations/2026-07-11-api-secrets-env-management-design.md) + commits `fd7f4f3`…`e6b01db`
**Pass:** 1
**Status:** done

## Verdict

**Approve with conditions.** Build-mode guard, sheldon wiring, D1–D4, scrub boundary,
and cross-spec updates are sound. AB-F1/B-F2/B-F3 **RESOLVED** in `e6b01db`
(`private_secrets.zsh.tmpl` rename + static test). Pass 1 terminates for
implementation findings; runtime verification (`stat`, `printenv`, `podman inspect`)
remains operator-deferred before issue close.

## Per-letter reviews

| Letter | Topic | Verdict | Reviewer | File |
|---|---|---|---|---|
| A | factual / correctness | Approve with conditions | pi-subagent reviewer (Letter A) | [pass1-A-factual](2026-07-11-api-secrets-env-management-review-pass1-A-factual.md) |
| B | security | Approve with conditions | pi-subagent reviewer (Letter B) | [pass1-B-security](2026-07-11-api-secrets-env-management-review-pass1-B-security.md) |
| D | consistency / cross-doc | Approve with conditions | pi-subagent reviewer (Letter D) | [pass1-D-consistency](2026-07-11-api-secrets-env-management-review-pass1-D-consistency.md) |

## Deduplicated findings

| ID | Letter | Severity | Status | Summary |
|---|---|---|---|---|
| AB-F1 | A+B | HIGH | RESOLVED | `private_secrets.zsh.tmpl` rename enforces `0600` (`e6b01db`) |
| B-F2 | B | MEDIUM | RESOLVED | Static test asserts `private_` source (`e6b01db`) |
| A-F2 | A | LOW | addressed | Build-mode guard "tail" assertion near-vacuous; body check is meaningful |
| B-F3 | B | LOW | RESOLVED | Inert mode comment removed (`e6b01db`) |
| B-F4 | B | LOW | open | `bw_session` exports empty `BW_SESSION` on unlock failure (robustness) |
| D1 | D | MEDIUM | addressed | A7 process gap: implementation pre-review; tracked via open issue + design §12 |
| D2 | D | LOW | open | `host_config_list.md` notes target path but not "port complete" vs design §9 |
| D3 | D | LOW | open | Spec 11 TODO says "enumerated above" but table is below |
| D4 | D | LOW | addressed | Design §6 YAML mode snippet vs inline comment — doc drift only |

## Resolved fixes (`e6b01db`)

1. **AB-F1 (HIGH):** `dot_config/zsh/rc/private_secrets.zsh.tmpl` — `private_`
   prefix enforces `0600` on target `~/.config/zsh/rc/secrets.zsh`.
2. **B-F2 (MEDIUM):** `test_secrets_template_uses_private_source_for_mode_0600`
   replaces inert comment assertion.

## Remaining before issue close

1. **Runtime evidence (operator):** Fill Bitwarden item IDs; run plan Phase 4
   Step 7 (`stat`, `printenv`, `podman inspect`); update result-log.
2. **Optional nits:** D2/D3 doc wording; B-F4 `bw_session` robustness.

## Design responses

- **AB-F1 / B-F2 / B-F3:** Resolved in `e6b01db`.
- **D1:** Addressed — pass-1 reviews filed post-implementation; issue stays
  open until runtime checks complete.
- **D2/D3:** Optional doc nits; no functional block.

## Pass termination (spec 09 §2.3)

- Letters A, B, D filed and updated post-fix (`e6b01db`).
- No open CRITICAL/HIGH findings.
- Pass 1 **terminates** for implementation scope.
- Design status → **Approved** (runtime verification deferred to operator).
- Issue stays **open** until runtime checks evidenced in result-log.

## Open questions (non-blocking)
  also be `private_`?
- Q2 (B): Document all-or-nothing `chezmoi apply` blast radius when one
  placeholder item ID remains?
- Q3 (D): Re-word A7 at issue close to reflect post-implementation review?
