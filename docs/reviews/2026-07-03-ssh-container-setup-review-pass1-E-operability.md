# ssh-container-setup — Review pass-1 (Letter E: operability / runtime)

**Date:** 2026-07-03
**Reviewer:** AI agent (Letter E — operability/runtime)
**Subject:** [`docs/specifications/implementations/2026-07-03-ssh-container-setup-design.md`](../specifications/implementations/2026-07-03-ssh-container-setup-design.md)
**Pass:** 1
**Status:** done (findings addressed in design revise)

## Verdict

**Approve with conditions.** Makefile/Containerfile パターンは GPG 同型で妥当。既存デプロイ rollout、手動 import 手順の `${USERNAME}` 罠、spec 03 sync、検証コマンド具体化を revise で解消。

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| E-F1 | MEDIUM | addressed | design §5.6; rollout | 旧イメージ + 新 volume だけでは root-owned mountpoint リスク — **make build 後 make up** を rollout 必須手順に明記 |
| E-F2 | MEDIUM | addressed | design §6 | `${USERNAME}` は operator shell に無い — `podman cp` 先を `dotfiles-manjaro:~/.ssh/` 形式に修正 |
| E-F3 | MEDIUM | addressed | design §5.5 | spec 03 を sync 対象に追加 |
| E-F4 | LOW | addressed | design §4; Makefile help | help/clean 説明を named volumes 包括表現に更新 |
| E-F5 | LOW | addressed | design §5.6 | build 後 inspect 具体コマンドを追加 |

## Required actions

design revise + spec 21 acceptance #21 (rollout) に build-first を記載。
