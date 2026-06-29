# 00 — Document management spec

このリポジトリ (`/data/dotfiles2`) における文書の置き場所、命名、ライフサイクル、形式を定義する。[`AGENTS.md`](../../AGENTS.md) §2 から参照される。

すべての AI エージェント / 人間メンテナはこの仕様に従う。


## 1. 目的

- 既に運用されているパターン（6 月時点で `docs/` 配下 50+ ファイル）を成文化する
- 新規 doc を起こすときに「**どこに / 何の名前で / どの形式で**」迷わないようにする
- 過去ドキュメントを同じ shape で読み書きできるようにする

## 2. ディレクトリ構成

```
docs/
├── README.md                       # 本仕様への索引のみ
├── issues/                         # 課題 (GitHub Issues の代替) + result-log
├── plans/                          # 実装計画 (-impl)
├── references/                     # 外部 / ホスト状態の参照資料
├── reviews/                        # レビュー (pass-N / letter 別 / aggregate / prompt)
└── specifications/
    ├── 00-document-management.md   # ← This file
    ├── api.md                      # 全体 API 仕様
    ├── installed_programs.md       # ツール一覧仕様
    └── implementation/             # 個別実装の design draft
        └── YYYY-MM-DD-<slug>-design.md
```

## 3. ファイル種別と命名

すべての文書は下記 7 種別のいずれか。新種別を追加するときは本仕様の改訂を経る。

| Type | Path | 命名 | 役割 |
|------|------|------|------|
| `issue` | `docs/issues/` | `YYYY-MM-DD-<slug>.md` | 課題提起 |
| `result-log` | `docs/issues/` | `YYYY-MM-DD-<phase>-<topic>.md` | Phase 完了の証拠（no-PR 環境のため） |
| `design` | `docs/specifications/implementation/` | `YYYY-MM-DD-<slug>-design.md` | 実装方針設計（DRAFT → Approved） |
| `plan` | `docs/plans/` | `YYYY-MM-DD-<slug>-impl.md` | Approved design 後の mechanical checklist |
| `review` | `docs/reviews/` | `YYYY-MM-DD-<slug>-review[-passN][-<letter>-<topic>][-prompt].md` | レビュー本体 / aggregate / prompt |
| `reference` | `docs/references/` | `<topic>.md` | 外部 / ホスト状態の参照 |
| `spec` | `docs/specifications/` | `NN-<topic>.md` (規範系) または `<topic>.md` (機能系) | プロジェクト全体の規範 |

### 3.1 slug

- 半角小文字、`-` 区切り、ASCII のみ
- 該当 issue の slug を継承する。同一 slug で `issue → design → plan → review → result-log` が grep で追える
- 例:
  - `docs/issues/2026-06-27-container-two-stage.md`
  - `docs/specifications/implementation/2026-06-27-container-two-stage-design.md`
  - `docs/reviews/2026-06-27-container-two-stage-review-pass2-B-security.md`
  - `docs/plans/2026-06-27-container-two-stage-impl.md`
  - `docs/issues/2026-06-28-phase7-smoke-matrix.md` (result-log)

### 3.2 日付

- ファイル先頭の `YYYY-MM-DD` は**当該文書を起こした日**
- 改訂しても日付は据え置く（探索性のため）
- 文書本文中で「来週」「明日」等の相対日付は禁止。常に絶対日付

## 4. Lifecycle

```
issue (open)
   │
   ▼
design (DRAFT)
   │
   ▼ レビュー依頼
review prompt → review pass-N (letter A-E)
   │
   ▼  集約 → design revise
design (DRAFT / in-review …)
   │
   ▼ 全 finding が RESOLVED / addressed
design (Approved)
   │
   ▼
plan (pending → executing)
   │
   ▼ 実行完了
result-log (docs/issues/)
   │
   ▼
issue (closed)
```

- design は review pass を経るたび `DRAFT → in-review → Approved` と status を上げる
- security に触れる design は最低 letter A + B + D を経ること（[AGENTS.md](../../AGENTS.md) §2）
- plan が走り切ったら **acceptance を満たした証拠** を `docs/issues/` に result-log として残す（PR description が無い環境のため）

## 5. Status 語彙

### 文書 status (design / plan / issue)

`DRAFT` / `awaiting reviewers` / `in-review` / `Approved` / `pending` / `executing` / `executed` / `closed` / `superseded`

### review finding status (`AGENTS.md` §3 と同じ)

`open` / `RESOLVED` / `REGRESSION` / `INCOMPLETE` / `addressed` / `blocked`

## 6. 各種文書の最低要件

### 6.1 issue

```markdown
# <Title>

**Date:** YYYY-MM-DD
**Status:** open | in-progress | closed
**Related:** [design](...), [plan](...), [reviews](...)

## Context
<観測された事実>

## Problem
<解くべき問い>

## Acceptance criteria
<何が満たされれば close になるか>

## Notes
<参考メモ>
```

### 6.2 design (`specifications/implementation/*-design.md`)

```markdown
# <Title> — Design

**Status:** DRAFT | in-review | Approved | superseded
**Date opened:** YYYY-MM-DD
**Issue:** [...]
**Author:** kiyama

## §1 Context & success criteria (S1, S2, …)
## §2 Alternatives considered
## §3 Architecture / Invariants (I1, I2, …)
## §4 Scope / staging breakdown
## §5–§N Implementation detail
## §N+1 Open questions (Q1, Q2, …)
```

- success criteria に `S<n>` ラベル、invariants に `I<n>` ラベル、open questions に `Q<n>` ラベルを必ず付ける（レビュアーが参照できるよう）
- `superseded` 状態の design は冒頭で後継 design の path を明示

### 6.3 review prompt (`reviews/*-review-prompt[-passN].md`)

リファレンス: [`docs/reviews/2026-06-27-container-two-stage-review-prompt.md`](../reviews/2026-06-27-container-two-stage-review-prompt.md)

最低限の構造:

- subject の相対パス
- 共通出力フォーマット（[AGENTS.md](../../AGENTS.md) §3 への参照で可）
- 各 Reviewer-X の **役割 / 読むもの / 評価論点 / 期待する出力形式**

### 6.4 review (`reviews/*-review[-passN][-<letter>-<topic>].md`)

[AGENTS.md](../../AGENTS.md) §3 のスキーマに従う：ヘッダ + Verdict + Findings table + Verified premises + Open questions。

集約レビュー (`*-review-passN.md`、letter 接尾辞なし) は letter 別レビューを統合し、design author が次 revise に使う final view。

### 6.5 plan (`plans/*-impl.md`)

```markdown
# <Title> — Implementation Plan

**Status:** pending | executing | executed
**Spec:** [...]
**Parent issue:** [...]
**Review trail:** [...]

## Phases

### Phase N — <Name>
1. step
2. step

**Acceptance**: <検証手順>
**Rollback**: <切り戻し手順>
```

- 各 Phase は **単一 commit** が原則
- Phase の Acceptance を満たした時点で result-log を `docs/issues/` に書く

### 6.6 result-log (`issues/<phase>-<topic>.md`)

該当 plan の Acceptance を満たした証拠を表 / ログとして添える。リファレンス: [`docs/issues/2026-06-28-phase7-smoke-matrix.md`](../issues/2026-06-28-phase7-smoke-matrix.md)

### 6.7 reference

任意フォーマット。ただし:

- 外部リソース引用なら **URL と取得日**
- ホスト状態スナップショットなら **取得方法と取得日**
- 内容が時系列に変わる場合はファイル名先頭に `YYYY-MM-DD-` を付ける

## 7. リンク規約

- すべて **リポジトリ相対パス** で `[label](relative/path.md)` を使う
- 絶対パス・`~/`・`file://` 禁止
- 削除した doc を参照していたリンクは、削除コミットで参照側も同時に更新する
- 章番号への deep link は `[§3.2](...#32-...)` のように anchor を併記

## 8. これは docs に書かない

- 永続でない作業メモ → セッション scratchpad
- 再利用すべき教訓 → memory
- secret / token / vault entry → 仕様書中であっても禁止
- ホストの個人パス (`/home/kiyama/...`) → `~/` 表記または環境変数化

## 9. 既存ドキュメントの段階的合流

本仕様策定時点で `docs/` 配下に 50+ ファイル。以下のみ強制移行：

1. `docs/README.md` をインデックスのみに刷新（本仕様への 1 リンク + サブディレクトリ一覧）
2. 新規 doc は本仕様に **100% 準拠**
3. 既存 doc は破壊的書き換えしない。次回改訂時に小さく合流させる
4. 重複 / 古い doc を見つけた場合は `superseded` 状態に下げ、後継への link を冒頭に追加

## 10. 改訂手順

本仕様自身も spec のひとつ。改訂時は：

1. 改訂理由を `docs/issues/` に issue として起こす
2. 必要なら design (`docs/specifications/implementation/<slug>-doc-mgmt-rev-design.md`) を経る
3. 本ファイルを直接編集し、commit log に issue path を含める
4. 影響を受ける既存テンプレ (`AGENTS.md` 等) を同 commit で同期する
