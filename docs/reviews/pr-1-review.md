# PR Review: #1 — feat: add Bitwarden secret management (spec 13) + runtime bw-login

**Reviewed**: 2026-06-29
**Author**: kkiyama117
**Branch**: develop → main
**Decision**: COMMENT (self-review; GitHub blocks self-approve/self-request-changes)

## Summary

仕様面・実装面ともに整合しており、ビルド時シークレット機構の撤去とランタイム
`BW_SESSION` ベースへの移行は十分に説明されている。CRITICAL/HIGH な問題はない。
MEDIUM 2 件は「Makefile の `bw-login` が spec 13 §4 の記述と微妙にずれる」点と
「`make apply` が仕様で参照されているがターゲットが存在しない」点。LOW 3 件は
コメント整形・改行・stdout の細かい所。マージ前に MEDIUM を解決するか、または
spec 側を実装に合わせて緩める判断をすると整合する。

## Findings

### CRITICAL

None.

### HIGH

None.

### MEDIUM

#### M1. `make bw-login` と spec 13 §4 の不整合

- **場所**: `Makefile:35,72-75`, `docs/specifications/13-secret-management.md:54-65`
- **内容**: spec 13 §4 step 3 は `bw unlock --raw` で session key を捕捉し、
  `export BW_SESSION="$(bw unlock --raw)"` を実行するフローを規定している。
  一方 `Makefile` の `bw-login` ターゲットは `--raw` 無しの `bw unlock`
  （対話・マスターパスワード入力）を呼ぶだけなので、出力は eval 可能な
  単一行ではなく `bw` のヘルプテキスト（中に `export BW_SESSION=...` 行が
  含まれるが、ユーザーが手動でコピー & 貼り付ける必要がある）になる。
- **影響**:
  - `make help` の説明文 `"prints 'export BW_SESSION=...'"` が
    eval ストリーム的に読めるため、ユーザーが `eval $(make bw-login)`
    を試して機能しないと混乱する可能性。
  - spec 13 §4 の手順を機械的に追えない。
- **修正案**: 以下のどちらかで整合させる:
  - (a) Makefile を spec に合わせる:
    ```makefile
    bw-login:
        @test -n "$$BW_CLIENTID" && test -n "$$BW_CLIENTSECRET" || { echo "..." >&2; exit 1; }
        @bw login --check >/dev/null 2>&1 || bw login --apikey
        @printf 'export BW_SESSION=%s\n' "$$(bw unlock --raw)"
    ```
    こうすれば `eval $(make bw-login)` がそのまま使える。
  - (b) spec 13 §4 step 3 を「`bw unlock`（対話）を実行し、表示される
    `export BW_SESSION=...` 行を自分のシェルに貼り付ける」に書き換え、
    Makefile help 文言も「prints a hint line」に変える。

#### M2. `make apply` が仕様で参照されているが Makefile に存在しない

- **場所**: `docs/specifications/08-automations.md:16,36`, `docs/specifications/13-secret-management.md:64,103`
- **内容**: 4 箇所で `make apply` が現役のターゲットのように記述されているが、
  `Makefile` に該当ターゲットは無い。spec 08 表の Status 列が `planned` に
  なっているため誤読は避けられるが、spec 13 §4 の本文は
  「`make bw-login` automates steps 2–3; `make apply` runs `chezmoi apply` ...」
  と並列で書かれており、両方とも実装済みのように読める。
- **影響**: 仕様だけ読んだ利用者・後続レビュワーが存在しないターゲットを
  実行しようとする恐れ。
- **修正案**: spec 13 §4 と §7 の `make apply` に `(planned)` または
  `(future, see Out of scope)` を付記する。PR 本文の "Out of scope (follow-up)"
  にも該当項目があるので、仕様側でも同等の注釈を付けるのが自然。

### LOW

#### L1. Containerfile に意図不明の空行追加

- **場所**: `container/Containerfile:23-25`
- **内容**: Layer 1-2 の説明コメントブロック内に空行が挿入され、
  `"... install the"` と `"Layer 1 pacman package set ..."` の間が分断されて
  文として読めなくなった。本文は変わらないが偶発的な編集に見える。
- **修正案**: 空行を削除して 1 段落に戻す。

#### L2. `docs/specifications/13-secret-management.md` に末尾改行が無い

- **場所**: ファイル末尾
- **内容**: `Deferred.` で終端しているが末尾改行が無い（`\ No newline at end of file`）。
  POSIX text-file の慣習に反するため、後続の sed/cat 連結や `git diff`
  表示で軽微な違和感が生じる。
- **修正案**: 末尾に `\n` を追加。

#### L3. `bw login --check` の stdout が抑止されていない

- **場所**: `Makefile:74`
- **内容**: `bw login --check 2>/dev/null || bw login --apikey` は stderr のみ
  リダイレクトしている。`bw login --check` はログイン済みの場合
  `"You are logged in as ..."` を **stdout** に出すため、help からの呼び出しでも
  常に余計な行が出る。
- **修正案**: `bw login --check >/dev/null 2>&1 || bw login --apikey` に変更。

## Validation Results

| Check | Result | Notes |
|---|---|---|
| Type check | Skipped | Makefile / Markdown / TOML のみ。型なし |
| Lint | Skipped | リンタ未設定 |
| Tests | Skipped | テストスイート未設定 |
| Build | Pass (partial) | `make help` 解析 OK; `make build` は PR 本文で著者が exit 0 を確認済み |
| Idempotency: `make gen-deps` | Pass | 再実行で `txt_written=0 doc_updated=False`、PR diff と一致 |
| Stale refs in `docs/specifications/` | Pass | `BW_ID` / `rbw` の残存はすべて「removed / not used」の文脈のみ |

## Files Reviewed

- Modified: `Makefile`
- Modified: `container/Containerfile`
- Modified: `dependencies/layer_1/pacman.txt` (auto-generated)
- Modified: `dependencies/packages.toml`
- Modified: `docs/specifications/01-file-structures.md`
- Modified: `docs/specifications/02-installed-programs.md` (auto-generated block)
- Modified: `docs/specifications/03-makefile.md`
- Modified: `docs/specifications/08-automations.md`
- Modified: `docs/specifications/11-pre-required-env-values.md`
- Modified: `docs/specifications/12-quickstart.md`
- Added:    `docs/specifications/13-secret-management.md`
- Modified: `docs/specifications/20-container-rules.md`
- Modified: `docs/specifications/21-container-build-flow.md`
- Modified: `docs/specifications/22-container-build-pre-required-envs.md`
- Modified: `docs/specifications/README.md`

## Notes

- セルフレビューのため GitHub 上では `--approve` / `--request-changes` を
  使えず `--comment` で投稿。マージ判定は別途別レビュワーが必要。
- `docs/references/` 配下（`host_config_list.md` や comparative-survey）には
  まだ `rbw` 言及が多数残るが、これらは過去状態を述べる調査ドキュメントで
  本 PR スコープ外。`host_config_list.md:51` の `"rbw → bitwarden 移行と整合確認"`
  は今後別 PR で更新するとよい。
