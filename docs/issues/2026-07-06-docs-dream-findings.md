# docs dream 2026-07-06 — out-of-scope findings (lifecycle / naming / rule amendments)

**Date:** 2026-07-06
**Status:** open
**Related:** [00-document-management.md](../specifications/00-document-management.md), [specs README](../specifications/README.md)

## Context

2026-07-06 の docs consolidation (dream) で、純粋な整合性修復（索引ドリフト・リンク切れ）は
直接 commit 済み。以下は spec の意味変更・lifecycle 修復を伴うため dream 単独では実施せず、
本 issue に集約する。

## Problem

1. **result-log 命名の spec と実態の乖離** — 専用 issue
   [2026-07-06-result-log-naming-amendment.md](2026-07-06-result-log-naming-amendment.md) で追跡。
2. **plan 命名違反** — `docs/plans/2026-06-29-chezmoi-apply-twice.md` に `-impl` 接尾辞が無い。
3. **slug 連鎖の断絶（孤児 plan）** — 対応する issue / design が存在しない:
   - `docs/plans/2026-07-03-host-main-ssh-key-container-impl.md`
   - `docs/plans/2026-07-04-container-locale-gen-impl.md`
   - `docs/plans/2026-07-05-cargo-config-container-impl.md`（design はあるが issue なし）
4. **構造外ディレクトリ** — `docs/superpowers/plans/2026-07-04-mise-config-source.md` は
   §2 のディレクトリ構成外。spec 00 にパスを追加するか、plan 生成先を `docs/plans/` に
   統一するかの判断が必要。
5. **review 命名違反** — `docs/reviews/pr-1-review.md` は
   `YYYY-MM-DD-<slug>-review...` 形式に合致しない（historical、§9 により据え置き中）。
6. **spec 状態の二重管理** — 専用 issue
   [2026-07-06-spec-status-single-source.md](2026-07-06-spec-status-single-source.md) で追跡。

## Acceptance criteria

- 1 と 6 について spec 00 / specs README の改訂 design（または軽微なら直接改訂）の判断が下る
- 2, 3, 5 の各ファイルについて rename / 追補 / 据え置き（superseded 注記）の判断が下る
- 4 の plan 生成先ポリシーが決まり、spec 00 §2 に反映される

## Notes

- 検出時の機械検査: fence / inline-code を除外した相対リンク検査で誤検知ゼロ化済み
  （引用ペイロード内リンクを broken 扱いしない）。残る既知の許容項目:
  `docs/specifications/implementations/2026-07-02-cargo-install-design.md` §「02 への prose note」内の
  `(24-rust-packages-rule.md)` は移植先 (`docs/specifications/`) 基準の相対パスであり修正不要。
