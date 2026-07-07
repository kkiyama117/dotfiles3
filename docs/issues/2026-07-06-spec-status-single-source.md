# spec 状態の単一管理 — specs README の Status 列を `> Spec status:` 行から機械検証する

**Date:** 2026-07-06
**Status:** open
**Related:** [specs README](../specifications/README.md), [docs-dream findings](2026-07-06-docs-dream-findings.md)

## Context

spec の状態は各ファイル先頭の `> Spec status:` 行と
`docs/specifications/README.md` の Status 列で二重管理されており、
2026-07-06 の consolidation で4件のドリフト
（02: DRAFT→active、03: empty (stub)→DRAFT、08: DRAFT (stub)→DRAFT、
21: empty (stub)→active）を索引側の手動修正で解消した。

## Problem

手動二重管理は spec 追加・昇格のたびにドリフトを再発させる。

## Acceptance criteria

- `> Spec status:` 行を SoT と定める（spec 00 に1行追記）
- 索引の Status 列と各 spec の状態行の一致を機械検証する手段が入る
  （[docs-lint](2026-07-06-docs-link-check-script.md) への統合、
  または索引表の自動生成のいずれか）
- 現行ツリーで検証がパスする

## Notes

状態語彙は specs README の Status legend
（active / DRAFT / DRAFT (stub) / empty (stub)）を正とする。
`> Spec status:` 行の括弧付き修飾（例: `active (delivered baseline + manual flow)`）は
先頭トークンのみを照合対象とする。
