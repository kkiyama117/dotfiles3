# ssh-container-setup — Review pass-1 (Letter A: factual / correctness)

**Date:** 2026-07-03
**Reviewer:** review subagent (Letter A — factual / correctness)
**Subject:** [`docs/specifications/implementations/2026-07-03-ssh-container-setup-design.md`](../specifications/implementations/2026-07-03-ssh-container-setup-design.md)
**Pass:** 1
**Status:** done (findings addressed in design revise)

## Verdict

**Approve with conditions.** Design が引用する既存コードは実ファイルと一致。false premise なし。spec 21 acceptance 採番衝突、Containerfile/spec 21 コメント更新の抜け、§4/§5.2 フラグ順序、`.pub` も ignore する副作用の未記載を revise で解消する。

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| A-F1 | MEDIUM | addressed | design §5.5; spec 21 acceptance #17 | 新規 acceptance を `#17–#20` としていたが #17 は cargo signed-prebuilt 基準が占有 → **#18–#21** に修正 |
| A-F2 | MEDIUM | addressed | design §5.2, §5.5; spec 21 Notes | "four named volumes" → "five" に加え "five runtime mounts" → "six" と spec 21 Notes 更新が必要 |
| A-F3 | LOW | addressed | design §4 vs §5.2 | `install -d` フラグ順序が §4 と §5.2 で不一致 → Layer 1-6 先例に揃える |
| A-F4 | MEDIUM | addressed | design §5.4, I-SSH4 | `.ssh/id_*` 等は `.pub` 公開鍵にも一致する — 「private key のみ」主張と齟齬 → 副作用を明記 |

## Required actions

1. design §5.5: acceptance **#18–#21**
2. design §5.2 + spec 21 Notes: runtime mount 総数更新
3. design §4: フラグ順序を §5.2 と一致
4. design §5.4: `.pub` も ignore される旨を追記
