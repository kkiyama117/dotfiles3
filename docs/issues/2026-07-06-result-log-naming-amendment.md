# spec 00 §3 改訂案 — result-log 命名を実態 (`YYYY-MM-DD-phase-<slug>.md`) に合わせる

**Date:** 2026-07-06
**Status:** open
**Related:** [00-document-management.md §3](../specifications/00-document-management.md), [docs-dream findings](2026-07-06-docs-dream-findings.md)

## Context

spec 00 §3 は result-log を `YYYY-MM-DD-<phase>-<topic>.md`
（例: `2026-06-28-phase7-smoke-matrix.md`、`<phase>` = phase 番号入り）と定めるが、
実在する result-log は全件 literal `phase`（例:
`2026-06-30-phase-bitwarden-auto-auth.md`、形式 `YYYY-MM-DD-phase-<slug>.md`）で
一貫している。

## Problem

spec と実態が乖離しており、どちらが正か判断できない。
実態側が全件一貫しているため、spec を実態に合わせるのが低コスト。

## Acceptance criteria

- `00-document-management.md` §3 の result-log 行が
  `YYYY-MM-DD-phase-<slug>.md`（slug は親 issue から継承）に改訂され、
  §3.1 の例も実在ファイルに差し替えられる
- 既存ファイルの rename は不要（実態は既に準拠）

## Notes

改訂は spec 00 §10 の手順に従う。本 issue がその起票にあたる。
