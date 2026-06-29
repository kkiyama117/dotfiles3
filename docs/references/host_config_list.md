# Host dotfiles inventory (`~/.local/share/chezmoi`)

ホスト側の chezmoi ソース (`~/.local/share/chezmoi`) で管理されているターゲット一覧。
新リポジトリ `/data/dotfiles2` への移植判断用。

- 取得日: 2026-06-28
- 取得方法: `chezmoi managed`（ホスト chezmoi の出力 176 件）
- 参照: ホスト source dir = `~/.local/share/chezmoi`

## 凡例

- ✅ — 新リポジトリ (`/data/dotfiles2`) に対応ソースが既にある
- ⚠ — 機微情報を含む。直接コピーせずテンプレ化 / シークレット参照に置き換え
- — (空欄) — 新リポジトリには未移植

---

## 1. シェル基盤 (zsh)

### エントリポイント

| Target | New repo | Note |
|---|---|---|
| `~/.zshenv` | ✅ `dot_zshenv` | 新側は素ファイル、ホストは `.tmpl` |
| `~/.config/zsh/.zprofile` | — | |
| `~/.config/zsh/.zshrc` | ✅ `dot_zshrc`（新側はトップに置く方針差あり） | |
| `~/.config/zsh/abbreviations` | — | |

### 補完スタブ (`~/.config/zsh/.zfunc/`)

| Target | Note |
|---|---|
| `_btm` `_cargo` `_chezmoi` `_deno` `_mise` `_paru` `_poetry` `_pueue` `_rustup` `_rye` `_sheldon` `_starship` `_volta` | 14 ファイル。ツールごとの動的補完出力をキャッシュ。`mise`/`paru`/`chezmoi` 等は新リポジトリでも実体導入されるので要追従 |

### 設定シャード (`~/.config/zsh/rc/`)

| Target | Note |
|---|---|
| `aliases.zsh` | |
| `bindkey.zsh` | |
| `completion.zsh` | |
| `for_development.zsh` | |
| `options.zsh` | |
| `secrets.zsh` ⚠ | 機密。テンプレ化必須 |

### 関数 (`~/.config/zsh/rc/functions/`)

| Target | Note |
|---|---|
| `branch-out.zsh` | |
| `bw_session.zsh` ⚠ | Bitwarden セッション取得関数。新側 rbw → bitwarden 移行と整合確認 |
| `osc_133.zsh` | |

### ツール統合 (`~/.config/zsh/rc/integrations/`) — 17 ファイル

`bat.zsh` `delta.zsh` `fd.zsh` `gamess.zsh` `lsd.zsh` `navi.zsh` `neovim.zsh`
`onefetch.zsh` `ripgrep.zsh` `rofi.zsh` `skim.zsh` `tealdeer.zsh` `topgrade.zsh`
`zoxide.zsh` `zsh-autocompletions_atinit.zsh` `zsh-autosuggestions_atload.zsh`

### 独自プラグイン (`~/.config/zsh/rc/my_plugins/`)

`.keep` `README.md` `magic_ctrl_z.zsh` `manjaro.zsh` `pandapdf.zsh`
`rec-screen.zsh` `tmux.zsh`

### テーマ

| Target | Note |
|---|---|
| `~/.config/zsh/theme/index.zsh` | |

---

## 2. プロンプト / プロンプト周辺

| Target | New repo | Note |
|---|---|---|
| `~/.config/starship.toml` | — | 現行 |
| `~/.config/starship/starship_old.toml` | — | 旧版バックアップ |

---

## 3. ターミナル / マルチプレクサ / TUI

### tmux

| Target | Note |
|---|---|
| `~/.config/tmux/tmux.conf` | エントリ |
| `~/.config/tmux/conf/{bindings,claude,options,plugins,status}.conf` | シャード 5 ファイル |
| `~/.config/tmux/scripts/dmux-really-quit.sh` | |
| `~/.config/tmux/scripts/tpm-bootstrap.sh` | TPM 起動補助 |

### dmux

| Target | Note |
|---|---|
| `~/.config/dmux/settings.json` | dmux 本体設定 |

### TUI ユーティリティ

| Target | Note |
|---|---|
| `~/.config/bottom/bottom.toml` | btm |

### ターミナルエミュレータ

| Target | Note |
|---|---|
| `~/.config/kitty/kitty.conf` | |
| `~/.config/wezterm/wezterm.lua` | |
| `~/.config/ghostty/config` | |

---

## 4. エディタ

| Target | Note |
|---|---|
| `~/.config/nvim/rc/secrets.vim` ⚠ | nvim の他ファイルは管理外。secrets のみ独立管理 |

---

## 5. Git / フォージ系

| Target | New repo | Note |
|---|---|---|
| `~/.config/git/config` | ✅ `dot_config/git/config.tmpl` | テンプレ化済み（新側） |
| `~/.config/git/ignore` | — | |
| `~/.config/gh/config.yml` | — | hosts.yml は新側 `gh-hosts.sh.tmpl` で生成 |
| `~/.config/lazygit/config.yml` | — | |

---

## 6. インプットメソッド (IME)

| Target | Note |
|---|---|
| `~/.config/fcitx5/config` | 本体設定 |
| `~/.config/fcitx5/conf/skk.conf` | SKK アドオン設定 |
| `~/.config/mozc/.gitkeep` | placeholder（mozc 実体は home に生成） |
| `~/.config/yaskkserv2/yaskkserv2.conf` | SKK サーバ |
| `~/.config/environment.d/fcitx5.conf` | systemd-user 環境変数 |

---

## 7. デスクトップ / ウィンドウ / 表示

| Target | Note |
|---|---|
| `~/.config/X11/xinitrc` | |
| `~/.config/rofi/config.rasi` | |
| `~/.config/wired/wired.ron` | 通知 |
| `~/.config/gtk-3.0/settings.ini` | |

---

## 8. パッケージマネージャ / OS

| Target | Note |
|---|---|
| `~/.config/pacman/makepkg.conf` | |
| `~/.config/topgrade.toml` | |
| `~/.config/aria2/aria2.conf` | |
| `~/.config/dircolors` | |

---

## 9. 開発ツール

| Target | New repo | Note |
|---|---|---|
| `~/.config/mise/config.toml` | ✅ `dot_config/mise/config.toml` | コンテナ Phase 4 で実体導入済み |
| `~/.config/mise/shorthands.toml` | — | |
| `~/.config/sheldon/plugins.toml` | ✅ `dot_config/sheldon/plugins.toml` | |
| `~/.config/npm/npmrc.old` | — | 旧版 |
| `~/.config/nushell/{config.nu,env.nu,mise.nu}` | — | |
| `~/.config/python/python_startup.py` | — | `PYTHONSTARTUP` |
| `~/.config/navi/config.yaml` | — | |
| `~/.config/navi/cheats/{chezmoi.cheat,git.cheat}` | — | |
| `~/.config/tealdeer/config.toml` | — | |
| `~/.config/pueue/{pueue.yaml,pueue.yml}` | — | 両方管理（移行残り？） |
| `~/.config/syncthing/config.xml` ⚠ | — | デバイス ID 等が入る可能性 |
| `~/.config/pki/.gitkeep` | — | 証明書保管 placeholder |
| `~/.local/share/cargo/config.toml` | — | レジストリ / target dir 等 |
| `~/.local/share/rye/config.toml` | — | |
| `~/.local/share/zsh/.keep` | — | placeholder |

---

## 10. Claude / AI エージェント

| Target | Note |
|---|---|
| `~/.config/claude/CLAUDE.md` | グローバル指示 |
| `~/.config/claude/settings.json` ⚠ | API キー類が混入する可能性。要レビュー |

---

## 11. systemd user units (`~/.config/systemd/user/`)

| Target | Note |
|---|---|
| `claude-notify-cleanup.service` / `.timer` | claude 通知クリーンアップ |
| `claude-notifyd.service` / `.socket` | claude 通知デーモン |
| `wired.service` | 通知デーモン |
| `yaskkserv2.service` | SKK サーバ |

ホスト側は `.chezmoiscripts/run_onchange_after_enable-claude-notify-cleanup.sh` 等で
`systemctl --user enable --now` を回している。

---

## 12. GPG (`~/.local/share/gnupg/`)

| Target | New repo | Note |
|---|---|---|
| `common.conf` | ✅ `dot_local/share/gnupg/` 配下（新側はテンプレ複数） | |
| `gpg-agent.conf` | ✅ `dot_local/share/gnupg/gpg-agent.conf.tmpl` | |
| `pinentry-auto.sh` ⚠ | — | TTY なし pinentry シム。コンテナで再利用するなら要移植 |

---

## 13. SSH

| Target | Note |
|---|---|
| `~/.ssh/authorized_keys` ⚠ | 公開鍵列。新側は `run_after_install-ssh-keys.sh.tmpl` で生成 |

---

## 14. ローカル bin

| Target | Note |
|---|---|
| `~/.local/bin/hermes-fusion` | カスタムスクリプト |

---

## 15. chezmoi run スクリプト (`.chezmoiscripts/`)

ホスト側で chezmoi apply 時に実行されるもの。

| Source | 概要 |
|---|---|
| `run_once_all_os.sh.cmd` | 全 OS 共通の初回処理 |
| `run_onchange_after_build-claude-tools.sh` | claude-tools ビルド |
| `run_onchange_after_enable-claude-notify-cleanup.sh` | systemd timer 有効化 |
| `run_onchange_after_enable-claude-notifyd.sh` | notifyd 有効化 |
| `run_onchange_after_enable-watchdog.sh` | watchdog 有効化 |

新リポジトリ側スクリプト (`.chezmoiscripts/run_after_install-*.sh.tmpl`):
`gh-hosts` / `git-credentials` / `gpg-signing` / `ssh-keys` — 役割が分かれており重複なし。

---

## 16. その他ホスト側ソースルート直下

source-tree 直下にはあるが `chezmoi managed` には出ない補助物：

| Path | 用途 |
|---|---|
| `.chezmoi.toml.tmpl` | chezmoi 設定テンプレ |
| `.chezmoiexternal.toml.tmpl` | 外部ソース取り込み |
| `.chezmoiignore` | 無視リスト |
| `.chezmoitemplates/{linux,windows}/` | OS 別テンプレ片 |
| `.dmux/`, `.dmux-hooks/`, `.hermes/`, `.vscode/`, `.worktrees/` | 開発補助 |
| `.executable_password_manager.sh`, `.password_manager.sh` | パスワードマネージャ抽象 |
| `AGENTS.md`, `CHANGELOG.md`, `README.md` | リポジトリメタ |
| `AppData/Roaming/` | Windows 用 |
| `chezmoi.code-workspace` | VSCode ワークスペース |
| `docs/` | ホスト dotfiles の独自ドキュメント |
| `programs/{claude-plugins,claude-tools}/` | ビルド対象ソース |
| `symlink_dot_claude` | `~/.claude` を別所に symlink |
| `test/` | dotfiles 自己テスト |

---

## 17. 既存重複サマリ

新リポジトリで既に対応ソースを持つもの：

- `~/.zshenv` → `dot_zshenv`
- `~/.config/git/config` → `dot_config/git/config.tmpl`
- `~/.config/mise/config.toml` → `dot_config/mise/config.toml`
- `~/.config/sheldon/plugins.toml` → `dot_config/sheldon/plugins.toml`
- `~/.local/share/gnupg/{common.conf, gpg-agent.conf}` → `dot_local/share/gnupg/*.tmpl`

新リポジトリ独自（ホストにない）：

- `dot_config/direnv/direnvrc`
- `dot_local/share/gnupg/gpg.conf.tmpl`
- `.chezmoidata/rbw.yaml`, `.chezmoidata.yaml`
- `.superpowers/sdd`, `containers/`, `templates/` 全般

---

## 18. 機密扱い注意リスト ⚠

直接コピーせず、テンプレ + シークレットマネージャ参照に置換すべきもの：

- `~/.config/zsh/rc/secrets.zsh`
- `~/.config/zsh/rc/functions/bw_session.zsh`
- `~/.config/nvim/rc/secrets.vim`
- `~/.config/claude/settings.json`
- `~/.config/syncthing/config.xml`
- `~/.ssh/authorized_keys`
- `~/.local/share/gnupg/pinentry-auto.sh`（機密ではないが TTY 環境前提）

新リポジトリ既存の `.chezmoiscripts/run_after_install-{gh-hosts,git-credentials,gpg-signing,ssh-keys}.sh.tmpl` と Bitwarden テンプレ規約に合わせて移植する。

---

## 19. ホスト管理外で移植候補となりうるプログラム設定

`chezmoi managed` には含まれていないが、ホスト `~/.config/` 等に実在する dev tool / shell 周辺の設定。
取得方法: `comm -23 <(ls ~/.config) <(chezmoi managed | grep '^.config/' | cut -d/ -f2 | sort -u)` の差分から
GUI アプリ・ゲーム・キャッシュ系を除外。

### 19-A. 優先度 高（現スタックの dev ツール）

| Path | サイズ感 | 内容 | 移植判断 |
|---|---|---|---|
| `~/.config/rbw/config.json` ⚠ | 213B | rbw（Bitwarden CLI）接続設定 | **要**。新リポジトリの rbw→bitwarden 移行と整合。`.chezmoidata/rbw.yaml` と連携検討 |
| `~/.config/zed/{settings.json,keymap.json}` ⚠ | 3.4KB | Zed エディタ設定。`settings.json` は AI 設定キー入り得 | **要**。settings は `.tmpl` 化 |
| `~/.config/zellij/config.kdl` | 13KB | zellij 設定 + layouts/ | tmux と並行運用なら **要** |
| `~/.config/zellij/layouts/` | dir | カスタムレイアウト | 上と同じく |
| `~/.config/yazi/` | (空) | TUI ファイラ。空なら無視可 | skip（実体なし） |
| `~/.config/htop/htoprc` | 1.6KB | htop の色／カラム | **要** |
| `~/.config/alacritty/alacritty.yml` | 12KB | Alacritty 設定（2022 以来更新なし、旧 yaml 形式） | 使ってないなら skip |
| `~/.config/yarn/config` | 164B | yarn classic 設定 | 必要なら |
| `~/.config/go/env` | 14B | `go env -w` で生成される env | **要**（小さいので） |
| `~/.config/flutter/custom_devices.json` | 1KB | Flutter カスタムデバイス | flutter 使うなら |
| `~/.config/pypoetry/{auth.toml,config.toml}` ⚠ | 計300B | poetry グローバル設定（auth.toml は API トークン入り得） | auth.toml は **テンプレ化必須**、config.toml は通常 |
| `~/.config/uv/uv-receipt.json` | 329B | uv インストーラ生成（auto-gen） | skip |

### 19-B. 優先度 中（XDG / システム周辺）

| Path | 内容 |
|---|---|
| `~/.config/user-dirs.dirs` | XDG_DOWNLOAD_DIR 等のローカライズ |
| `~/.config/user-dirs.locale` | XDG ロケール |
| `~/.config/mimeapps.list` | デフォルトアプリ関連付け |
| `~/.config/autostart/` | XDG autostart `.desktop` 群 |
| `~/.config/qt5ct/` | Qt5 テーマ統合 |
| `~/.config/pavucontrol.ini` | PulseAudio mixer GUI |
| `~/.config/screenkey.json` | screenkey 設定 |
| `~/.config/solaar/` | Logitech Unifying レシーバ |
| `~/.config/tlpui/` | TLP（省電力）GUI |
| `~/.config/rhq/` | リポジトリ workspace ツール |
| `~/.config/topgrade.d/` | topgrade 追加設定（`topgrade.toml` は管理済） |

### 19-C. 優先度 低 / 評価待ち

| Path | メモ |
|---|---|
| `~/.config/fish/` | fish shell（使っているか要確認） |
| `~/.config/mc/` | midnight commander |
| `~/.config/fontforge/` | フォント編集 |
| `~/.config/coc/` | coc.nvim（nvim 側を移植するなら連動） |
| `~/.config/obsidian/`, `~/.config/obs-studio/` | アプリ依存設定。アプリごと移行する場合のみ |
| `~/.config/voicevox/`, `~/.config/qalculate/`, `~/.config/calibre/`, `~/.config/lutris/` | デスクトップアプリ群 |

### 19-D. $HOME 直下のファイル

| Path | サイズ | 内容 |
|---|---|---|
| `~/.profile` | 35B | login シェル POSIX |
| `~/.yarnrc` | 116B | yarn classic グローバル |
| `~/.ideavimrc` | 29B | JetBrains IdeaVim |
| `~/.gitignore` | 7B | $HOME 直下 global gitignore（`~/.config/git/ignore` と重複疑い、要照合） |
| `~/.pypirc` ⚠ | 495B | PyPI publish 認証 |
| `~/.honcho/config.json` | 1KB | honcho 設定（同 dir の他ファイルは log/state なので除外） |
| `~/.skk-jisyo`, `~/.skkeleton`, `~/.eskk` | dir | SKK 辞書群（yaskkserv2 連動） |

### 19-E. 管理対象外でよいもの（参考）

GUI アプリのデータ／キャッシュ／OS 自動生成系：

- `BraveSoftware/`, `Slack/`, `Code/`, `Code - OSS/`, `JetBrains/`, `chromium/`, `Bitwarden/` (GUI), `Keybase/`, `discord/`, `firebase/`, `microsoft-edge/`, `google-chrome*/`, `opera/`, `vivaldi/`, `mozilla/`, `thunderbird/`, `zoom*`, `Slack/`
- `dconf/`, `gconf/`, `glib-2.0/`, `goa-1.0/`, `gtk-2.0/` (gtk-3.0 のみ管理)
- ゲーム: `Vampire_Survivors*/`, `SaltAndSanctuary/`, `bitburner/`, `paradox-launcher-v2/`, `ftb-app/`, `mtgatool-desktop/`, `unity3d/`, `lutris/`, `minecraft/`
- `evcxr/`（REPL history）, `procps/`, `pulse/`, `nvidia/`, `Kvantum/`, `nv/`, `monitors.xml`, `manjaro-hello.json`

---

## 20. ホスト管理外で注意すべき機密候補 ⚠

新リポジトリ取り込み時にテンプレ化必須：

| Path | 機密内容 |
|---|---|
| `~/.config/rbw/config.json` | Bitwarden サーバ URL / メールアドレス |
| `~/.config/zed/settings.json` | Zed AI/LLM API キーが入り得る |
| `~/.config/pypoetry/auth.toml` | PyPI / 私設 index トークン |
| `~/.pypirc` | PyPI publish トークン |
| `~/.config/rclone/` | リモートストレージ認証情報 |
| `~/.config/github-copilot/` | Copilot OAuth トークン |
| `~/.config/gh/hosts.yml`（managed 内の `config.yml` とは別） | GitHub OAuth トークン。`run_after_install-gh-hosts.sh.tmpl` で生成方針あり |

---

## 21. 監査メモ

- 監査スクリプト雛形:
  ```sh
  comm -23 \
    <(ls -1 ~/.config | sort -u) \
    <(chezmoi managed | awk -F/ '/^\.config\//{print $2}' | sort -u)
  ```
- 上記差分は GUI / ゲーム / OS 自動生成を多く含むので、機械的取り込みではなく
  本セクション 19-A → 19-B → 19-C の順に手動仕分けすること。
- 新リポジトリ取り込みは Phase 7+ を想定。Bitwarden テンプレ規約・コンテナ
  rehydrate と整合を取る。

