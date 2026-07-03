# ssh-container-setup — Review pass-1 (Letter C: architecture / senior engineering)

**Date:** 2026-07-03
**Reviewer:** ecc:architect (subagent)
**Subject:** [`docs/specifications/implementations/2026-07-03-ssh-container-setup-design.md`](../specifications/implementations/2026-07-03-ssh-container-setup-design.md)
**Pass:** 1
**Status:** in-review

## Verdict

**Approve with conditions.** GPG 配管（`gnupg-container-setup` → 手動 import → deferred Bitwarden/config）との三層スコープ分割は一貫しており、named volume + owner-correct mountpoint という既存パターンの自然な拡張である。`.chezmoiignore` の部分 ignore と Layer 1-7 採番も妥当。条件は二点：(a) spec 25 の全面 defer が GPG の spec 23 先例とずれ、手動 import 手順が design 一時文書に留まる運用上のギャップを生む、(b) I-SSH 不変条件群が I-GPG と対称ではなく、agent 非配線・ignore パターン完全性・ロールアウト記述の置き場所をもう一段整理すべき。

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| F1 | MEDIUM | open | design §1 S9, §4, §7 Q4; issue AC #8; [`23-container-gnupg-management.md`](../specifications/23-container-gnupg-management.md) §1–3 | spec 25 全面 defer は GPG の spec 23（配管直後に runtime lifecycle 規範化）先例と非対称；手動 import が design §6 のみに留まり normative 化されない |
| F2 | MEDIUM | open | design §3 I-SSH* vs I-GPG3; §7 Q1 | I-GPG3 は agent セマンティクスを不変条件で固定するが、SSH 側に「plumbing 段階で ssh-agent を配線しない」相当の不変条件がない |
| F3 | MEDIUM | open | design §5.4; config issue AC #6; I-SSH4 | 部分 ignore は将来 config と整合するが、パターン列挙が OpenSSH の全秘密鍵命名を網羅していない可能性（カスタム名 PEM 等） |
| F4 | LOW | open | design §3 I-SSH5; spec 21 acceptance #16 | ロールアウト安全（targeted `podman volume rm`）を I-SSH5 に載せるのは GPG 側（I-GPG* には無く spec 21 #16）と置き場所が非対称 |
| F5 | LOW | open | design §5.6; §6 step 4 | 検証計画が `ssh-add -l` を前提とするが Q1 で agent は defer — `-i` スモークを第一検証にすべき |
| F6 | LOW | open | design §5.1; [`02-installed-programs.md`](../specifications/02-installed-programs.md) | `openssh` の `has_configs = true` が未実現のまま；GPG plumbing は `has_configs = false` で整合していた |

### F1 details

> **Quote (design §1 S9 / §7 Q4):** 「full normative spec **25** is deferred to the config issue; this design delivers only the plumbing + operator procedure」「Full normative spec 25 lands with the config issue. This design's §6 is copied/adapted into spec 25 §manual-import at that time」

> **Quote (GPG 先例 — spec 23 §1):** plumbing issue が empty keyring を配管した時点で、**runtime key lifecycle** を spec 23 として normative 化。Bitwarden 自動化と gpg-agent 設定は §7 future work に defer。

GPG トラックは **plumbing 完了 → spec 23（baseline + 手動 import）→ 別 issue で Bitwarden / agent 設定** という段階的 normative 化を採っている。SSH design は plumbing 段階の手動 import を design §6 に置き、**spec 25 全体**（config layout / GPG SSH tier / fragment Include / manual import）を config issue まで一括 defer している（[`2026-07-03-ssh-container-config-setup.md`](../issues/2026-07-03-ssh-container-config-setup.md) AC #7）。

この分割は YAGNI 的には理解できるが、アーキテクチャ上の帰結は次の通り。

- plumbing クローズ後、オペレータが参照すべき **normative 手順**が spec 20/21/22 の不変条件と design DRAFT §6 だけになる（result-log リンクに依存）。
- config issue  pickup 時、spec 25 が **配管 baseline + 手動 import + config + GPG tier** を一度に背負い、スコープとレビュー面（security A+B+D 必須）が膨らむ。
- parent issue AC #8 は「result-log **or** lightweight spec 25 §manual」と許容しているが、design は後者を明示的に却下している。

**Suggested fix:** GPG の spec 23 と同型に、plumbing 実装完了時点で **spec 25 のスケルトン**（§1 scope/relationships、§2 delivered baseline = I-SSH1..5 + empty volume、§3 manual import = design §6 移植）だけを normative 化し、config / GPG SSH tier / fragment Include は config issue で §4+ として追加 defer。design §7 Q4 と §4「Explicitly out of scope」の spec 25 行を「full spec 25 → config issue；**plumbing baseline spec 25 §1–3 → plumbing result-log 時**」に書き換える。**Verification:** spec 25 草案が spec 23 の章立てと grep 追跡可能な対応関係を持つこと；config issue AC #7 が「§4+ 追記」に縮小されること。

### F2 details

> **Quote (I-GPG3):** 「`gpg-agent` / `pinentry` are runtime, on-demand only. No agent is baked into the image entrypoint」

> **Quote (design §7 Q1):** 「Deferred. OpenSSH can use keys directly via `IdentityFile` / `-i` without a long-running agent」

GPG plumbing は agent 挙動を **不変条件 I-GPG3** で固定し、将来の chezmoi `gpg-agent.conf` 追加の前提を spec 20 に明示している。SSH plumbing は agent 非配線を Q1 に defer するのみで、I-SSH1..5 に相当記述がない。config issue が `SSH_AUTH_SOCK` / gpg-agent SSH socket を追加する際、**plumbing 段階の「agent なしが正常」**が spec 20 から読み取れない。

**Suggested fix:** I-SSH6（または I-SSH3 を分割せず新設）例：「plumbing 段階では entrypoint / zshenv に ssh-agent を配線しない。file key は `IdentityFile` / `ssh -i` で直接使用する。agent 配線は config issue に defer。」Q1 を RESOLVED（方針固定）にし、defer は **実装**のみに限定。**Verification:** spec 20 の I-SSH ブロックだけで「container 起動直後に agent 必須ではない」が判別できること。

### F3 details

> **Quote (design §5.4 / I-SSH4):** `.ssh/id_*`, `.ssh/*_ed25519`, `.ssh/*_rsa`, `.ssh/*_ecdsa`, sk variants — **whole `.ssh` tree is NOT ignored**

> **Quote (config issue frozen layout):** `~/.ssh/id_*` volume-only；fragment Include で config は chezmoi 管理

部分 ignore は **GPG の tree 全 ignore（I-GPG5）と意図的に非対称**であり、将来の `private_dot_ssh/config.tmpl` + `config.d/chezmoi/` と整合する正しいアーキテクチャ判断である（design §3 I-SSH4 の rationale は妥当）。

一方、パターン列挙方式の保守コストと漏れリスクがある。

- `id_*` / `*_ed25519` 等は OpenSSH 慣習名をカバーするが、**任意ファイル名**（例：`~/.ssh/my_vps_key`）やレガシー `*_dsa`、PEM 単体（拡張子なし）は漏れる。
- 漏れた秘密鍵が chezmoi source bind に `chezmoi apply` で書き込まれると、**volume 秘密と repo 秘密の二重化**および spec 13 I-S4 違反リスク（bind mount は chezmoi source root）。

**Suggested fix:** (1) design §5.4 に「パターンは OpenSSH 慣習名の最小集合；カスタム名鍵は operator 責任で `.chezmoiignore` 追記または慣習名へリネーム」と明記。(2) config issue pickup 時に spec 25 §chezmoiignore で `.ssh/config.d/local/` を volume-only ignore 追加（config issue layout と一致）。plumbing 段階では optional LOW として `.ssh/known_hosts` を ignore しない方針（volume-local state）を §7 Q2 と整合確認済みとして §5.4 に一文追加してよい。**Verification:** 慣习外ファイル名を volume に置いた場合 chezmoi が触らないことは **設計上保証しない**ことが文書化されていること。

### F4 details

> **Quote (I-SSH5):** 「`make clean` removes `dotfiles_ssh` … **Rollout / reset:** `podman volume rm dotfiles_ssh` (NOT `make clean` …)」

> **Quote (GPG — spec 21 acceptance #16 / cargo rollout):** 同趣旨の targeted volume rm は **acceptance criterion** と spec 21 Notes に記載；I-GPG1..5 には rollout 文言なし。

ロールアウト安全の知識を不変条件 I-SSH5 に含めるのは **運用上有用**だが、GPG/cargo 先例では spec 21 acceptance に置いている。I-SSH5 が「clean 時の削除」と「reset 手順」の二義を担い、I-GPG1（volume 存在）と粒度が揃わない。

**Suggested fix:** I-SSH5 は I-GPG1 同型に「`dotfiles_ssh` named volume @ `~/.ssh`；image に鍵なし」に限定し、targeted reset は spec 21 acceptance #17–#20（design §5.5 案）側に集約。I-SSH5 の rollout 段落は spec 21 へ移すか cross-ref のみに。**Verification:** spec 20 の I-SSH ブロックが I-GPG ブロックと同じ抽象度（永続化・権限・secret-free・ignore）に揃うこと。

### F5 details

> **Quote (§5.6 / §6 step 4):** `ssh-add -l` lists key；Q1 は agent defer

`ssh-add` は **ssh-agent** が必要。plumbing 段階で agent を起動しない方針（Q1）と検証計画が矛盾し、implementer が agent を ad-hoc 起動するか、検証をスキップするかの判断を迫る。

**Suggested fix:** 第一検証を `stat` + `ssh -i ~/.ssh/id_ed25519 -o BatchMode=yes -o ConnectTimeout=5 user@host true`（operator 提供 Host）に変更。`ssh-add -l` は optional / config または Bitwarden issue 後。**Verification:** §5.6 が agent 非依存で S5 persistence を検証できること。

### F6 details

> **Quote (§5.1):** `openssh` … `has_configs = true` …「this phase does not add chezmoi SSH config sources」

GPG plumbing は `gnupg` / `pinentry` を `has_configs = false` とし、spec 02 の宣言と chezmoi 実体が一致していた。`openssh` は既存 entry が `has_configs = true` のため、**宣言上は config 対象だが実体なし**の期間が plumbing クローズ後も続く（config issue まで）。

アーキテクチャ上 fatal ではない（generator 変更なし）が、spec 02 の「has_configs = chezmoi 管理 config あり」の契義とずれる。

**Suggested fix:** design §5.1 に「`has_configs = true` は config issue で実現；plumbing 段階では spec 02 AUTO-GEN 注記のみ（spec 20 I-SSH ブロックで unrealized と明記）」を追加。`has_configs` を false に落とす選択肢は **却下理由**（将来 flip コスト）を一行でよい。**Verification:** spec 20 更新案に「openssh config unrealized until spec 25 §config」注記があること。

## Verified premises

- **P1:** 現行 Containerfile は Layer 1-5（0755 XDG toolchain）、Layer 1-6（0700 gnupg）まで実装済み。SSH design の Layer **1-7**（0700 `~/.ssh`）は 1-6 の直列拡張として一貫（`~/.ssh` を Layer 1-5 XDG ブロックに混ぜない判断は正しい）。
- **P2:** Makefile は `GNUPG_VOLUME` まで定義済み；`SSH_VOLUME` 追加は GPG と同一機械パターン（verified: `Makefile:18-21`, `73-84`）。
- **P3:** `.chezmoiignore` は `.local/share/gnupg` を tree 全 ignore（I-GPG5 実体）；SSH 部分 ignore は未追加（design §5.4 は新規 subsection 想定）。
- **P4:** `openssh` は `dependencies/packages.toml` に layer 1 登録済み；design S1「gen-deps 変更不要」は正確。
- **P5:** deferred config issue（[`2026-07-03-ssh-container-config-setup.md`](../issues/2026-07-03-ssh-container-config-setup.md)）は sibling plumbing 完了後 pickup と明記；Include + fragment モデル（YAML manifest 却下）は architect review 2026-07-03 と一致；chezmoiignore 部分 ignore 要件（AC #6）は design §5.4 と同一パターン列。
- **P6:** deferred Bitwarden issue（[`2026-07-03-ssh-bitwarden-import.md`](../issues/2026-07-03-ssh-bitwarden-import.md)）は parent plumbing 依存・`run_after_install-ssh-keys.sh.tmpl`・spec 13 §5a ゲートを GPG sibling（[`2026-07-01-gnupg-bitwarden-import.md`](../issues/2026-07-01-gnupg-bitwarden-import.md)）と同型で記述。
- **P7:** host bind mount 却下理由（agent socket / lock / permission coupling）は spec 23 §3 と同根で、design §2 B / §6 脚注と整合。
- **P8:** spec 21 Notes は現状「four named volumes (cargo/rustup/mise/gnupg)」；design §5.2 の Layer 1 コメント更新（five volumes + ssh）は spec 21 表・Notes 更新とセットで必要。

## Open questions

- **Q-C1:** plumbing クローズ時に spec 25 §1–3 の **軽量 normative 化**（F1 提案）を採るか、issue AC #8 の「result-log のみ」で足りるとみなすか。採否は design author の判断だが、GPG 先例との長期保守性で前者を推奨。
- **Q-C2:** config issue 実装時、chezmoi が `~/.ssh/config` を volume 上に作成すると **初回 apply で volume 内に config が出現**する。plumbing 段階の hand-edit config と fragment 移行の rollout は config design 側で扱う想定か（plumbing design では触れない — 了解だが spec 25 §rollout に残すべき）。
- **Q-C3:** Tier 1 GPG SSH auth 有効化後も file key（Tier 2）が VPS 用に必要（config issue Notes / Bitwarden issue Notes 一致）。I-SSH1「file keys only」は plumbing のスコープラベルとして正しいが、spec 25 では **auth tier 表**へ昇格するタイミングを F1 と合わせて固定したい。
