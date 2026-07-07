# docs 相対リンクの機械検査スクリプトを導入する

**Date:** 2026-07-06
**Status:** open
**Related:** [00-document-management.md §7](../specifications/00-document-management.md), [docs-dream findings](2026-07-06-docs-dream-findings.md)

## Context

2026-07-06 の docs consolidation で、素朴な grep ベースのリンク検査は
コードフェンス／インラインコード内の「他ファイルへ移植する引用ペイロード」を
broken link と誤検知した（当初18件検出 → 真の破損は7件）。
ファイルごとに相対パスを解決し、フェンスとインラインコードを除外する検査で
誤検知1件（許容済み）まで収束した。

## Problem

docs の相対リンク切れを検出する再現可能な機械検査が repo に無く、
consolidation のたびに ad-hoc スクリプトを書いている。

## Acceptance criteria

- `make docs-lint`（または `scripts/` 配下のスクリプト）として以下を満たす検査が入る:
  - 各 `.md` のディレクトリ基準で相対リンクを解決する
  - フェンスされたコードブロックとインラインコードスパン内のリンクを無視する
  - 絶対パス・`~/`・`file://` リンクを違反として報告する（§7）
- 現行ツリーに対して誤検知ゼロで走る
- [08-automations.md](../specifications/08-automations.md) に target を記載する

## Notes

検証済みロジック（Python）:

```python
import os, re, glob
link_re = re.compile(r'\]\(([^)#\s]+\.md)(#[^)]*)?\)')
fence_re = re.compile(r'^\s*(```|````)')
code_span = re.compile(r'`[^`]*`')
for f in sorted(glob.glob('docs/**/*.md', recursive=True)) + ['AGENTS.md']:
    dirn = os.path.dirname(f) or '.'
    in_fence = False
    for i, line in enumerate(open(f), 1):
        if fence_re.match(line):
            in_fence = not in_fence; continue
        if in_fence: continue
        for m in link_re.finditer(code_span.sub('', line)):
            p = m.group(1)
            if p.startswith(('http','/','~')) or not os.path.exists(os.path.join(dirn, p)):
                print(f'BAD {f}:{i} -> {p}')
```

既知の許容項目: `docs/specifications/implementations/2026-07-02-cargo-install-design.md`
の spec 02 向け引用 prose note 内 `(24-rust-packages-rule.md)`
（移植先基準の相対パス。[引用フェンス規約](2026-07-06-quoted-payload-fencing-rule.md)
が入れば構造的に解消される）。
