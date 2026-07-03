# ssh-container-setup — Review pass-1 (Letter B: security)

**Date:** 2026-07-03
**Reviewer:** ecc:security-reviewer (subagent, Letter B)
**Subject:** [`docs/specifications/implementations/2026-07-03-ssh-container-setup-design.md`](../specifications/implementations/2026-07-03-ssh-container-setup-design.md)
**Pass:** 1
**Status:** done (findings addressed in design revise)

## Verdict

**Approve with conditions.** named volume + 非 bind + image secret-free の主軸は妥当。列挙型 chezmoiignore の限界、手動 import の bind 経由禁止、spec 25 baseline normative 化を revise で補強。

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| B-F1 | MEDIUM | addressed | design §5.4, I-SSH4 | 慣習外ファイル名は ignore 対象外 — operator 責務と `.pub` 副作用を明記 |
| B-F2 | MEDIUM | addressed | design §6 | spec 23 I-GM2 対称の「chezmoi source bind / repo 経由禁止」を追加 |
| B-F3 | MEDIUM | addressed | design §1 S9, §7 Q4 | plumbing 時点で spec 25 §1–3 baseline を normative 化（GPG spec 23 先例） |

## Required actions

design revise で B-F1..B-F3 を反映。実装ブロッカーなし。
