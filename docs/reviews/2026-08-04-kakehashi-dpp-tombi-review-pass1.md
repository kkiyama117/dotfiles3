# kakehashi-dpp-tombi — Review pass-1 (aggregate)

**Date:** 2026-08-04
**Subject:** [Global kakehashi configuration design](../specifications/implementations/2026-08-04-kakehashi-dpp-tombi-design.md)
**Per-letter review:**
[A-factual](2026-08-04-kakehashi-dpp-tombi-review-pass1-A-factual.md)

## Verdict

**Approved.** Reviewer A returned "Request changes" with 7 findings (4
HIGH, 1 MEDIUM, 2 LOW). All findings are addressed in the revised design
(§8 response table, IDs quoted verbatim); no finding remains `open` /
`REGRESSION` / `blocked`. The two factual corrections (A-F2 `MultipleHook`
shape, A-F4 syntax description) were independently re-verified against
source.

## Findings disposition

| ID | Severity | Status | Disposition |
|---|---|---|---|
| A-F1 | HIGH | addressed | S1–S5 criteria, staging breakdown, Q1–Q3 section added |
| A-F2 | HIGH | addressed | `MultipleHook` = plugins required + 4 optional hooks; verified against `dpp.vim/denops/dpp/base/config.ts` |
| A-F3 | MEDIUM | addressed | `dummy_mappings` minItems/maxItems 2 |
| A-F4 | LOW | addressed | syntax() described as manual Vim embedding with nvim tree-sitter guard |
| A-F5 | LOW | addressed | `/etc/tombi/config.toml` system level + stop-at-first-hit semantics + `.tombi.toml` shadowing |
| A-F6 | HIGH | addressed | issue gains Context/Notes, design link, no premature result-log link |
| A-F7 | HIGH | addressed | §5 is verification plan; exploratory evidence noted with lifecycle exception; plan/result-log re-execution |

## Verified premises (post-revision)

- P1: real deps files (8) lint clean with the fixed schema; broken
  variant fails CLI and LSP (3 schema errors); positive control clean.
- P2: `MultipleHook` source shape confirmed (minified `n` type in local
  cache, fields as the reviewer stated).
- P3: `/etc/tombi/config.toml` system-level discovery confirmed in
  `rust/serde_tombi/src/config.rs`.
- P4: tombi LSP pulls schema diagnostics through kakehashi with only the
  user config.

## Open questions

None remaining.
