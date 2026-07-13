# api-secrets-env-management — Review pass-1 (Letter D: consistency / cross-doc)

**Date:** 2026-07-12
**Reviewer:** pi-subagent reviewer (Letter D)
**Subject:** [`docs/specifications/implementations/2026-07-11-api-secrets-env-management-design.md`](../specifications/implementations/2026-07-11-api-secrets-env-management-design.md)
**Pass:** 1
**Status:** done

## Verdict

**Approve with conditions.** Cross-spec consistency is strong: specs 11 / 13 /
08 / 01 all carry matching, non-contradictory entries; committed artifacts match
the design snippets (§5–§8) closely; slug/traceability across issue → plan →
result-log → commits is coherent. Conditions are (1) the **A7 process gap** —
implementation landed on `develop` before the required review letters completed —
must stay tracked (issue must not close until A+B+D land and findings resolve),
and (2) three LOW documentation-wording nits should be tidied. No cross-doc
contradiction rises to CRITICAL/HIGH.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| D1 | MEDIUM | addressed | `docs/issues/2026-07-11-api-secrets-env-management.md` A7 · design §12 | Implementation (fd7f4f3…cdec48e) landed on `develop` before required review letters A+B+D — process/ordering gap vs issue A7 |
| D2 | LOW | open | `docs/references/host_config_list.md:44,51` · design §9 | Port entries note the chezmoi target path but are not marked "port complete" (still ⚠); §18 confidential list unchanged — divergence from design §9 wording |
| D3 | LOW | open | `docs/specifications/11-pre-required-env-values.md:41-43` | "Bitwarden items" TODO note says API items are "enumerated **above**", but they are listed in the table **below** the note |
| D4 | LOW | addressed | design §6 vs `dot_config/zsh/rc/secrets.zsh.tmpl:1` | Design §6 shows a `.chezmoi.yaml.tmpl` `mode: 0600` YAML snippet; implementation uses the inline `# chezmoi:mode=600` directive (both valid; design's "file-level directive" phrasing covers it) |

### D1 details (A7 process gap — implementation pre-approval)

Issue acceptance criterion **A7** requires:

> **A7:** Design passes review letters A + B + D **before implementation**.

The result-log records all four implementation phases already committed to
`develop`:

```11:14:docs/issues/2026-07-11-phase-api-secrets-env-management.md
| 1 | fd7f4f3 | Add api_secrets data and secrets.zsh chezmoi template. |
| 2 | 83e1ade | Wire secrets.zsh into sheldon and add bw_session helper. |
| 3 | 7163b34 | Add static tests for API secrets env management. |
| 4 | cdec48e | Document API secrets env management and record phase result-log. |
```

The design **acknowledges** the inversion explicitly, so this is a documented,
not hidden, gap:

```349:350:docs/specifications/implementations/2026-07-11-api-secrets-env-management-design.md
> Implementation landed on `develop` before pass-1 reviews completed;
> reviewers MUST evaluate both design and committed artifacts.
```

Consistency impact: A7 cannot be satisfied in its literal "before
implementation" sense retroactively. It is coherently downgraded to a
close-gate: the issue is still `Status: open`, and the result-log defers closure
to "Complete review letters A + B + D per design §12 before closing issue"
(`docs/issues/2026-07-11-phase-api-secrets-env-management.md:42`).

**Suggested resolution:** Keep the issue open until A+B+D are filed and every
CRITICAL/HIGH finding is RESOLVED. When closing, re-word A7 in the issue to
reflect that review completed post-implementation on landed artifacts (per
design §12), rather than silently checking A7 as-written. **Verification:** issue
close commit references all three letter files and the aggregate `-pass1.md`.

### D2 details (host_config_list port status vs design §9)

Design §9 spec-update table promises:

```305:305:docs/specifications/implementations/2026-07-11-api-secrets-env-management-design.md
| [`host_config_list.md`](../../references/host_config_list.md) | Mark `secrets.zsh` / `bw_session.zsh` port complete |
```

What landed (commit cdec48e) only updates the *note* to cite the target path;
the rows keep the ⚠ "not-yet-ported / confidential" glyph and §18's confidential
list is unchanged:

```44:44:docs/references/host_config_list.md
| `secrets.zsh` ⚠ | 機密。chezmoi 移植先: `dot_config/zsh/rc/secrets.zsh.tmpl` |
```

The plan itself already softened §9's "mark port complete" to "note chezmoi port
target paths" (plan Phase 4 Step 5), so plan↔implementation are internally
consistent; the divergence is design §9 ↔ landed doc. This is defensible (the
port is code-complete but runtime-unverified / operator IDs unfilled, so ⚠ is
arguably accurate), but design §9 and the file disagree on wording.

**Suggested resolution:** Either (a) update design §9 to say "note port target
path (leave ⚠ until runtime-verified)", or (b) change the legend usage once
runtime verification lands. No functional impact. (Pre-existing, out-of-scope:
the file header still references `/data/dotfiles2` at lines 4–8; not introduced
by this change.)

### D3 details (spec 11 "enumerated above" wording)

```41:43:docs/specifications/11-pre-required-env-values.md
> TODO: reconcile any remaining host secret survey entries under
> `host_config_list.md` with this table. API provider items are enumerated
> above; SSH import item is listed separately.
```

The four `api_secrets` rows are in the table **immediately below** this note
(lines 48–51), not above it. Minor self-inconsistency in directionality.

**Suggested resolution:** Change "enumerated above" → "enumerated below (this
table)". **Verification:** re-read note in context of the table.

### D4 details (mode directive snippet drift)

Design §6 presents the mode contract as a `.chezmoi.yaml.tmpl` YAML block:

```249:251:docs/specifications/implementations/2026-07-11-api-secrets-env-management-design.md
dot_config/zsh/rc/secrets.zsh.tmpl:
  mode: 0600
```

The landed file uses the inline attribute comment instead:

```1:2:dot_config/zsh/rc/secrets.zsh.tmpl
# chezmoi:mode=600
{{- if not .build_mode -}}
```

Both are legitimate chezmoi mode mechanisms, and design §6's own header
(`# .chezmoi.yaml.tmpl or file-level directive`) sanctions the inline form, so
this is `addressed`, not a defect. Noted only so a future reader isn't confused
by the design showing the YAML variant that was not used. Tests
(`container/tests/container/test_api_secrets.py:26`) and the result-log assert
the inline directive, keeping test↔artifact consistent.

## Verified premises

- **P1 — Spec 11 fully populated, no two-tier contradiction.** All four provider
  rows exist in the Bitwarden-items table (`11:48-51`) and in the API-provider
  env subsection (`11:69-76`). API keys are treated as vault items retrieved via
  templates, which matches spec 13 §2's two-tier model (Tier 1 = base key as
  podman secrets; "every other sensitive value is a vault item") — no
  contradiction. The prior `_(TBD)_` row referenced by plan Phase 4 Step 1 is
  gone.
- **P2 — Spec 13 consumer inventory + invariants consistent.** `secrets.zsh.tmpl`
  is listed as a `bitwardenFields`/`bitwarden` consumer (`13:62-63`); I-S1..I-S6
  are unchanged and the landed template complies (single `{{ if not .build_mode }}`
  guard wrapping every `bitwarden*` call, `dot_config/zsh/rc/secrets.zsh.tmpl:2-19`).
  Q1 remains open and consistently points at operator-filled item IDs (`13:219-222`),
  matching the DEFERRED rows in the result-log.
- **P3 — Specs 08 / 01 entries match real paths.** 08 automations row added
  (`08:19`) with correct inputs/outputs; 01 inventory lists
  `secrets.zsh.tmpl`, `functions/bw_session.zsh` (`01:37-38`) and
  `api_secrets.yaml` in `.chezmoidata/` (`01:46`). Paths resolve on disk.
- **P4 — Design §5–§8 snippets match committed files.** `api_secrets.yaml`
  (4 providers, `custom_field`/`api_key`/`runtime: both`, no `enabled` flag),
  `secrets.zsh.tmpl` loop, sheldon `[plugins.my_secrets]` block
  (`local`/`use`/`apply=["source"]`), and `bw_session.zsh` all match their design
  sections verbatim. Plugin order `my_conf_defered` → `my_secrets` → `my_functions`
  holds in `dot_config/sheldon/plugins.toml:105-121` (design §7).
- **P5 — `runtime:` filter is fully wired cross-doc.** The template's `$.runtime`
  (`secrets.zsh.tmpl:7`) resolves to `.chezmoi.toml.tmpl:13`
  (`runtime = env "DOTFILES_RUNTIME" | default "host"`); the entrypoint sets
  `export DOTFILES_RUNTIME=container` (`container/bind/layer_5_files/entrypoint.sh:118`).
  Design §6's `runtime: host|container|both` contract is therefore consistent and
  non-latent (all v1 entries use `both`).
- **P6 — Traceability / slug consistency.** Single slug
  `2026-07-11-api-secrets-env-management` (result-log uses `-phase-` variant per
  00-doc-mgmt); issue↔plan↔design↔review-prompt↔result-log links are mutual;
  all four phase SHAs in the result-log exist in `git log` (a follow-up commit
  d2aa46a corrected the Phase-4 SHA, and the recorded `cdec48e` now matches).
  Deferred runtime items are explicit in the result-log.
- **P7 — Required-letters and file-naming consistency.** 09-review §2.2
  (secret/auth → A+B+D) matches the design's declared letters and the review
  prompt; this file's name follows §2's
  `YYYY-MM-DD-<slug>-review-passN-<letter>-<topic>.md` pattern and the prompt's
  output-path table (sibling A-factual / B-security files present as untracked).

## Open questions

- **Q1:** Design §2 alternative A1 was rejected "for path parity", and A4 was
  chosen partly for the same reason. Given A4 landed with a *dedicated*
  synchronous `[plugins.my_secrets]` block (not the existing `my_conf_defered`
  glob), is the A4 justification still the intended rationale, or should §2 note
  that A4 accepts one extra sheldon block as the cost of synchronous load? (No
  change required; consistency confirmation only — the chosen wiring matches §7.)
- **Q2:** For D1, when the issue is eventually closed, will A7 be re-worded to
  reflect post-implementation review (per design §12), or checked as-written?
  This affects whether the acceptance record stays internally consistent.
