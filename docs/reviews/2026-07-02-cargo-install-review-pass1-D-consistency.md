# cargo-install — Review pass-1 (Letter D: consistency / cross-doc)

**Date:** 2026-07-02
**Reviewer:** pi subagent (letter-D consistency reviewer)
**Subject:** [`docs/specifications/implementations/2026-07-02-cargo-install-design.md`](../specifications/implementations/2026-07-02-cargo-install-design.md)
**Pass:** 1
**Status:** in-review

## Verdict

Request changes. デザインの内部構造・命名・ファイル配置は概ね仕様セットと整合するが、cross-doc 整合性の観点で **1 件の HIGH** (spec 02 mise バレットの Layer 3-5 → 3-4 更新漏れ) と **2 件の MEDIUM** (I-CARGO vs I-CARGO1 表記揺れ、spec 02 `layer` 契約記述の layer=6 非互換) がある。これらは design の §5.5 spec 更新手立てに明示的に追加すれば解決する。

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| F1 | HIGH | open | `02-installed-programs.md:32` / design §5.5 | mise manager バレットが "Layer 3-5" を参照したままで、design が 3-4 への移動をカバーしていない → 移行後に spec 02 と spec 21 が矛盾 |
| F2 | MEDIUM | open | design §1 S8 (L69), issue #8 (L107) vs §3 I2 (L138), §5.5 (L393) | 不変量グリフが `I-CARGO`(無番号) と `I-CARGO1`(有番号) で揺れている。spec 20 の I-GPG1/I-GIT1/I-AUR1 パターンは番号必須 |
| F3 | MEDIUM | open | `02-installed-programs.md` Contract table (`layer` row) / design §5.5 | `layer` 契約が "Containerfile layer index" と定義されているが、layer=6 は明示的に Containerfile stage ではない。契約記述の更新が design の spec 02 編集候補に載っていない |
| F4 | LOW | open | design §3 I2 (L138) | "mirrors how rustup/mise are documented as curl-bootstrapped infra" とあるが、spec 20 に I-RUSTUP / I-MISE の各不変量は存在せず、spec 21 stage table の prose でしか記述されていない。前置きの表現が実際の仕様セットとずれる |
| F5 | LOW | open | `20-container-rules.md:78` (I-GIT3) | 既存の dangling reference: `I-GPG9` が参照されているが定義は I-GPG1..5 のみ。本 design 起因ではないが cross-doc 整合性スキャンで検出 |
| F6 | LOW | open | design §5.5 (spec 21 bullet) / §5.4 (spec 24 outline) | spec 21 → spec 24 へのリンク、および spec 24 → spec 02/21 への逆リンクが design の編集指示に明示されていない (spec 02→24, spec 20→24, spec 24→20 は明示あり) |

### F1 details

> `docs/specifications/02-installed-programs.md` line 32:
> "`mise`: ... installed in the `toolchain` stage (Layer 3-5). Bare `mise install <tool>` reads a `mise.toml` ..."

design §5 (S5) は toolchain sub-layer の並びを `3-2 rustup → 3-3 mise binary → 3-4 mise install languages (moved up from 3-5) → 3-5 cargo-binstall → 3-6 cargo tools` に変更する。design §5.5 の spec 02 編集候補は "cargo manager rule + layer-6 note" のみを記載し、**mise バレットの "Layer 3-5" を "Layer 3-4" に更新する手続きを含んでいない**。移行後、spec 02 は mise を Layer 3-5 と主張し spec 21 stage table は 3-4 と主張する矛盾が残る (letter D の核照査項目 #1)。

**suggested fix:** design §5.5 の spec 02 編集項に「mise manager バレットの `(Layer 3-5)` → `(Layer 3-4)` 更新」を 1 行追加する。`cargo` バレットも `cargo install --locked` → `cargo binstall -y` に書き換える点は既に design が意図しているので明文化すればよい。

**verification:** `grep -n "Layer 3-5" docs/specifications/02-installed-programs.md` が 0 件、`grep -n "Layer 3-4" docs/specifications/02-installed-programs.md` が mise バレットに 1 件。

### F2 details

> design §1 S8 (line 69): "spec 20 (a `I-CARGO` invariant if warranted, or a cross-ref to spec 24)"
> issue acceptance #8 (line 107): "a `I-CARGO` invariant if warranted"
> vs design §3 I2 (line 138): "A new `I-CARGO1` invariant records this (spec 20)"
> design §5.5 (line 393): "add `I-CARGO1`"

spec 20 の既存パターンは `I-GPG1..5`, `I-GIT1..7`, `I-AUR1..4` であり、**すべて番号付き** (grep で確認: I-GPG, I-GIT, I-AUR すべて `<TOPIC><n>`)。design の本文 §3/§5.5 は正しく `I-CARGO1` を使っているが、success-criteria S8 と issue acceptance #8 は `I-CARGO` (無番号) と書いている。同一 slug 内でグリフ表記が揺れているため grep 追跡性が損なわれる (00-doc-management §3.1 は slug 内の grep 追跡性を重視)。

**suggested fix:** S8 と issue #8 の `I-CARGO` を `I-CARGO1` に統一。

**verification:** `grep -rn "I-CARGO[^1]" docs/` が 0 件。

### F3 details

> `02-installed-programs.md` Contract table, `layer` row:
> "`layer` | yes | integer ≥ 1 (Containerfile layer index) |"

design §3 I3 / §1 S3 は `layer = 6` を「runtime-manual reference list (no Containerfile stage)」として導入する。これは `layer` が **Containerfile layer index** であるという契約定義と直接衝突する (stage 6 は存在しない; build stages は 0-5)。design §5.5 の spec 02 編集候補は "cargo manager rule + layer-6 note" のみで、Contract table の `layer` 欄の記述更新を含んでいない。移行後、契約 table は layer=6 を説明できない。

**suggested fix:** Contract table の `layer` 記述を例えば「integer ≥ 1; 1-5 = Containerfile stage index, 6 = runtime-manual reference (not build-installed, see spec 24)」のように拡張し、design §5.5 にその編集を明示する。

**verification:** spec 02 の Contract table が layer=6 を例外として明記していること。

### F4 details

> design §3 I2: "A new `I-CARGO1` invariant records this (spec 20), mirroring how rustup/mise are documented as curl-bootstrapped infra."

grep `I-(RUSTUP|MISE)` → 0 件。spec 20 に rustup/mise の I- 不変量は存在せず、それらは spec 21 stage table の prose (row 3, 3-5) でしか記述されていない。したがって "mirrors how rustup/mise are documented as ..." は実際の仕様セットに対して少し過大な表現。I-CARGO1 は実際には **新しいカテゴリの先例** になる。

**suggested fix:** §3 I2 の "mirroring how rustup/mise are documented as curl-bootstrapped infra" を "extending the same curl-bootstrap precedent as rustup (spec 21 row 3-2) / mise (spec 21 row 3-3), now formalized as an I- invariant" 程度に修正、あるいは rustup/mise も将来 I- 化する意図なら Q に明示する。

**verification:** design の根拠記述が spec 20/21 の実在する記述と一致すること。

### F5 details

> `20-container-rules.md:78` (I-GIT3): "The container has no keyring daemon (I-GPG9)"
> grep `I-GPG[6-9]` in `docs/specifications/` → 定義側は 0 件、参照側は spec 20:78 と git-config design:84 の 2 件。

I-GPG9 は定義されていない (I-GPG1..5 のみ)。本 cargo design 起因ではないが、letter D の cross-doc 整合性スキャンで検出されたため記録。design が spec 20 に I-CARGO1 を追加する際、同じく番号の飛び (I-GPG5 → I-GPG9) が既存することを踏まえ、I-CARGO の番号付けが I-AUR4 の直後で連続になるかの配置規約も暗黙に確認しておくとよい。

**suggested fix (out of scope):** 別 issue で I-GPG9 → 実在する番号 (I-GPG6 等) に修正、または I-GPG9 を定義追加。本 design では対処不要 (スコープ外)。

### F6 details

> design §5.5 spec 21 bullet: "update the Stage-3 rows ... add acceptance criteria" — spec 24 へのリンク言及なし
> design §5.4 spec 24 outline: §4 "Recorded as `I-CARGO1` in spec 20" — spec 02/21 への逆リンク言及なし

spec 02 → 24 (prose note), spec 20 → 24 (delegated rules row), spec 24 → 20 (I-CARGO1) は design に明示あり。しかし spec 21 → 24 (acceptance criteria からの参照) および spec 24 → 02/21 (layer 契約 / stage table への逆参照) が編集指示にない。00-doc-management §7 は双方向リンクの同期を求める。

**suggested fix:** spec 21 の新 acceptance criterion に spec 24 へのリンクを追加し、spec 24 §3/§5 から spec 02 (layer 契約) / spec 21 (stage table) への逆リンクを明示する。

**verification:** `grep -rn "24-rust-packages-rule" docs/specifications/{02,20,21}.md` が各 1 件以上; `grep -rn "02-installed-programs\|21-container-build-flow" docs/specifications/24-rust-packages-rule.md` が各 1 件以上。

## Verified premises

- P1: spec 24 は次空き番号。`ls docs/specifications/` で 00,01,02,03,08,09,11,12,13,20,21,22,23 を確認。24 は 23 の直後で空き。
- P2: slug `rust-packages-rule` は命名規約 (00-doc-management §3.1: 小文字・ハイフン・ASCII) に合致。既存 slug (`container-rules`, `gnupg-management`, `installed-programs`) と同じスタイル。
- P3: `I-<TOPIC><n>` パターンは I-GPG1..5 / I-GIT1..7 / I-AUR1..4 で確立 (grep で確認)。`I-CARGO1` のグリフ (大文字・略語・番号付き) はパターンに適合する。問題は無番号表記 `I-CARGO` との揺れのみ (F2)。
- P4: ファイル命名 3 点 (issue `docs/issues/2026-07-02-cargo-install.md`, design `docs/specifications/implementations/2026-07-02-cargo-install-design.md`, review `docs/reviews/2026-07-02-cargo-install-review-pass1-D-consistency.md`) はすべて 00-document-management §3 の命名規約 (YYYY-MM-DD-<slug>.md / ...-design.md / ...-review-passN-<letter>-<topic>.md) に合致。
- P5: design の S1-S9 と issue acceptance #1-#9 は 1:1 に対応 (cargo-binstall bootstrap / topgrade / layer-6 / runtime-manual set / sub-layer ordering / persistence / tests / specs / no-secret)。番号付けは整合。
- P6: mise design doc (`2026-07-01-mise-managed-languages-design.md`) は status DRAFT のままで historical 扱い。task 命題の通り、本 design はこれを更新対象に含めていない (正しい)。ただし result-log/plan (`2026-07-01-phase-mise-managed-languages.md`, `2026-07-01-mise-managed-languages-impl.md`) も historical であり、それらの "Layer 3-5" 参照は 00-doc-management §9 (既存 doc は破壊的書き換えしない) に従い更新不要。
- P7: design §1 S5 / §5.5 は spec 21 stage table の 3-2/3-3/3-4/3-5/3-6 行への更新を明示的にカバーしている。spec 21 側の更新漏れはなし (F1 は spec 02 側)。
- P8: layer=6 は spec 21 の stage 定義 (0-5) と直接矛盾しない — design は明示的に "no Containerfile stage 6" と定義 (§3 I3, §5.4 §5)。矛盾の可能性は spec 02 契約 table の `layer` 記述のみ (F3)。
- P9: design の §1-§8 構造は 00-doc-management §6.2 template (§1 context, §2 alternatives, §3 invariants, §4 scope, §5+ impl, open questions) に概ね適合。§7 Open questions / §8 Deferred の順序は template の "§N+1 Open questions" からやや逸脱するが、§8 Deferred は追加セクションとして妥当。

## Open questions

- Q1: F1 (spec 02 mise バレットの 3-5→3-4 更新) を design §5.5 の編集候補に追加してよいか。また `cargo` バレットの `cargo install --locked` → `cargo binstall -y` 書き換えも spec 02 編集項に明文化するか。
- Q2: F2 について、S8 / issue #8 の `I-CARGO` を `I-CARGO1` に統一してよいか。
- Q3: F3 について、spec 02 Contract table の `layer` 記述を layer=6 を含む形に拡張し、design §5.5 にその編集を追加してよいか。
- Q4: F5 (既存の I-GPG9 dangling reference) は本 design のスコープ外とみなして記録留めでよいか。それとも本 pass で対処すべきか。