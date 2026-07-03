# ssh-container-setup — Review pass-1 (Letter D: consistency / cross-doc)

**Date:** 2026-07-03
**Reviewer:** letter-D consistency reviewer (subagent)
**Subject:** [`docs/specifications/implementations/2026-07-03-ssh-container-setup-design.md`](../specifications/implementations/2026-07-03-ssh-container-setup-design.md)
**Pass:** 1
**Status:** done (findings addressed in design revise)

## Verdict

**Approve with conditions.** 命名・issue 1:1 対応は良好。spec 21 採番、spec 20 セクション所属、spec 03 sync 漏れ、§2/§6 の "Approach B" glyph 衝突を revise で解消。

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| D-F1 | HIGH | addressed | design §5.5 vs spec 21 #17 | acceptance **#18–#21** に修正 |
| D-F2 | MEDIUM | addressed | design §5.5 vs spec 20 §Build | I-SSH1..5 は **Build (Containerfile)** セクション（I-GPG* 並列）に配置 |
| D-F3 | MEDIUM | addressed | design §5.5 vs spec 03 | `03-makefile.md` を sync 対象に追加（`SSH_VOLUME` + 既存 `GNUPG_VOLUME` 欠落も埋める） |
| D-F4 | MEDIUM | addressed | design §2 B vs §6 Approach B | §6 に spec 23 "Approach B" と §2 Alternative B は無関係である注記を追加 |
| D-F5 | LOW | addressed | design §4 item 2 | help/clean 文言は GPG + SSH を包括的に更新 |
| D-F6 | LOW | open | spec 00 §2 vs §3 | `implementation/` vs `implementations/` — 本 design 起因ではない pre-existing |

## Required actions

design revise で D-F1..D-F5 を反映。D-F6 は別 cleanup issue。
