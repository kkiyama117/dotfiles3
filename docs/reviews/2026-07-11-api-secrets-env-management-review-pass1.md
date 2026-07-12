# api-secrets-env-management — Review pass-1 (aggregate)

**Date:** 2026-07-12
**Reviewer:** parent orchestrator (aggregate of pi-subagent letters A, B, D)
**Subject:** [`docs/specifications/implementations/2026-07-11-api-secrets-env-management-design.md`](../specifications/implementations/2026-07-11-api-secrets-env-management-design.md) + commits `fd7f4f3`…`cdec48e`
**Pass:** 1
**Status:** in-review

## Verdict

**Request changes.** Build-mode guard, sheldon wiring, D1–D4, scrub boundary,
and cross-spec updates are sound. One shared **HIGH** finding blocks approval:
`# chezmoi:mode=600` is not a chezmoi permission mechanism; without a `private_`
source prefix (or `run_after_chmod`), rendered `~/.config/zsh/rc/secrets.zsh`
will be `0644`, violating S4/I4. Pass 1 does **not** terminate until A-F1/B-F1
are RESOLVED.

## Per-letter reviews

| Letter | Topic | Verdict | Reviewer | File |
|---|---|---|---|---|
| A | factual / correctness | Request changes | pi-subagent reviewer (Letter A) | [pass1-A-factual](2026-07-11-api-secrets-env-management-review-pass1-A-factual.md) |
| B | security | Request changes | pi-subagent reviewer (Letter B) | [pass1-B-security](2026-07-11-api-secrets-env-management-review-pass1-B-security.md) |
| D | consistency / cross-doc | Approve with conditions | pi-subagent reviewer (Letter D) | [pass1-D-consistency](2026-07-11-api-secrets-env-management-review-pass1-D-consistency.md) |

## Deduplicated findings

| ID | Letter | Severity | Status | Summary |
|---|---|---|---|---|
| AB-F1 | A+B | HIGH | open | `# chezmoi:mode=600` inert; rendered `secrets.zsh` ~`0644` not `0600` (S4/I4) — rename to `private_secrets.zsh.tmpl` or add chmod step |
| B-F2 | B | MEDIUM | open | Static test asserts inert comment string, not real mode — false S4 assurance |
| A-F2 | A | LOW | addressed | Build-mode guard "tail" assertion near-vacuous; body check is meaningful |
| B-F3 | B | LOW | open | Inert mode comment emitted into rendered file (cosmetic; fixed by AB-F1) |
| B-F4 | B | LOW | open | `bw_session` exports empty `BW_SESSION` on unlock failure (robustness) |
| D1 | D | MEDIUM | addressed | A7 process gap: implementation pre-review; tracked via open issue + design §12 |
| D2 | D | LOW | open | `host_config_list.md` notes target path but not "port complete" vs design §9 |
| D3 | D | LOW | open | Spec 11 TODO says "enumerated above" but table is below |
| D4 | D | LOW | addressed | Design §6 YAML mode snippet vs inline comment — doc drift only |

## Required fixes before pass-1 close

1. **AB-F1 (HIGH):** Rename `dot_config/zsh/rc/secrets.zsh.tmpl` →
   `dot_config/zsh/rc/private_secrets.zsh.tmpl` (target stays
   `~/.config/zsh/rc/secrets.zsh` at mode `0600`). Remove the inert
   `# chezmoi:mode=600` line. Update static tests and spec/doc references.
2. **B-F2 (MEDIUM):** Replace mode comment assertion with source-attribute
   check (e.g. assert `private_secrets.zsh.tmpl` exists).
3. **Runtime evidence (operator):** After item IDs filled, run plan Phase 4
   Step 7 (`stat`, `printenv`, `podman inspect`) and update result-log.

## Design responses (pending)

- **AB-F1:** Not yet addressed — implementation fix required.
- **B-F2:** Not yet addressed — test fix follows AB-F1.
- **D1:** Addressed by keeping issue open until reviews complete and findings
  resolve; re-word A7 at close time.
- **D2/D3:** Optional doc nits; no functional block.

## Pass termination (spec 09 §2.3)

- Letters A, B, D filed.
- **Open HIGH finding AB-F1** — pass 1 does **not** terminate.
- Design status remains **in-review** (not Approved).
- Issue must stay **open** until AB-F1/B-F2 resolved and runtime checks run.

## Open questions (non-blocking)

- Q1 (B): Is `~/.config/zsh/rc/` single-user only, or should the directory
  also be `private_`?
- Q2 (B): Document all-or-nothing `chezmoi apply` blast radius when one
  placeholder item ID remains?
- Q3 (D): Re-word A7 at issue close to reflect post-implementation review?
