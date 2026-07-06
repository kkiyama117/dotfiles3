# spec 00 §7 改訂案 — 他ファイルへ移植する引用ペイロードはコードフェンス必須

**Date:** 2026-07-06
**Status:** open
**Related:** [00-document-management.md §7](../specifications/00-document-management.md), [link-check script](2026-07-06-docs-link-check-script.md)

## Context

plan / design は「別ファイルへ書き込むべき内容」（issue の Status 行の置換文、
spec への追記 prose など）を本文中に引用する。引用内の相対リンクは
**移植先ファイル基準**で解決されるため、引用元ファイル基準のリンク検査では
broken 扱いになる。`2026-07-01-mise-managed-languages-impl.md` のように
コードフェンスで囲めば、検査から機械的に除外できる。

## Problem

引用ペイロードの書式が統一されておらず（インライン prose / インラインコード /
フェンス混在）、リンク検査の誤検知源になっている。

## Acceptance criteria

- `00-document-management.md` §7 に次趣旨の規約が追記される:
  「他ファイルへ書き込む内容を引用するときは fenced code block
  （```` ```markdown ````）で囲む。引用内のリンクは移植先基準の相対パスで書く」
- 既存文書は §9（破壊的書き換えしない）に従い据え置き。新規文書から適用

## Notes

改訂は AGENTS.md §2 / spec 00 §10 の手順（issue → 必要なら design → 直接編集 +
commit log に issue path）に従う。本 issue がその起票にあたる。
