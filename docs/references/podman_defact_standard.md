# Podman デファクトスタンダード：イメージビルド設定と運用管理

> 前提：Podman はインストール済み。「インストール方法」ではなく「管理方法・プロジェクトのフォルダ構成ベストプラクティス」をまとめたもの。

---

## 1. プロジェクトのフォルダ構成（デファクト）

Podman コミュニティ / Red Hat 公式ガイドでよく見られる、整理された単一プロジェクトのレイアウトは以下のようになります。

```
myapp/
├── Containerfile              # ルート直下なら名前は「Containerfile」か「Dockerfile」
├── .containerignore           # ビルドコンテキスト除外定義（.dockerignore と同文法）
├── compose.yaml               # Podman Compose / Docker Compose 定義
├── Makefile                   # ビルド・実行コマンドをラップ（推奨）
├── .env                       # 環境変数（gitignore対象。機密以外）
├── envs/
│   ├── common.env             # 全サービス共通の環境変数
│   └── web.env                # サービス固有の環境変数
├── Containerfiles/            # 複数環境用 Containerfile を置く場合（Red Hat 推奨パターン）
│   ├── Containerfile.dev
│   ├── Containerfile.prod
│   └── scripts/               # ビルド後スクリプトなど
├── containers/                # （Quadlet を使う場合）systemd ユニット群
│   ├── myapp.container
│   └── myapp.kube
├── config/                    # 設定ファイル類をボリュームマウント用に分離
│   ├── prometheus/prometheus.yml
│   └── grafana/provisioning/
├── data/                      # 永続データ（ボリュームのバインド先）
│   ├── prometheus/
│   └── grafana/
└── src/                       # アプリケーション本体ソース
    └── app.py
```

ポイント:
- **設定(YAML/設定ファイル)と永続データ(data/)を分離する**のが定石。バックアップや別ホストへの移植が容易になります。
- データを `/opt/data`、compose を `/opt/compose` のように別々に置く人もいますが、1サービス=1ディレクトリツリー（ZFS などのスナップショット単位）にまとめる方が運用しやすいという意見が多数派です。

---

## 2. イメージ定義ファイルの命名規則

| 名前 | 役割 |
|------|------|
| `Containerfile` | Podman/Buildah ネイティブの名前。ルート直下なら `podman build .` で自動検出される |
| `Dockerfile` | フォールバック名。Docker 互換。両方ある場合は `Containerfile` が優先 |

複数のイメージや環境を作る場合は **拡張子/サフィックス方式**が一般的です：

```
Containerfile.dev
Containerfile.prod
Containerfile.api
Containerfile.frontend
```

ビルド時は `-f` で明示指定します。このとき**ビルドコンテキストと Containerfile の場所は独立**であることに注意：

```bash
# Containerfile は Containerfiles/、コンテキストは services/api/
podman build -f Containerfiles/Containerfile.api -t myorg/api:latest services/api/
```

---

## 3. `.containerignore`（ビルドコンテキストの最適化）

これが無いと `.git` や `node_modules`、`__pycache__` までコンテキストに送られ、ビルド時間とイメージサイズが肥大化します。ルート直下に配置し、`.dockerignore` と同じ文法です：

```gitignore
# 版管理
.git
.gitignore

# 依存・ビルド成果物
node_modules
__pycache__
dist
build
*.pyc

# 開発・CI 関連
.vscode
.idea
.github
.env
.env.*

# コンテナ定義自体（イメージに入れない）
Containerfile
Dockerfile
compose*.yaml
.containerignore
```

より安全なのは**「全除外→必要だけ許可」の allowlist 方式**：

```gitignore
*
!src/
!src/**
!package.json
!requirements.txt
```

どちらでも、本当に何が入るかは以下で検証できます：

```bash
cat > Containerfile.debug << 'EOF'
FROM alpine
COPY . /ctx
RUN find /ctx -type f | sort
EOF
podman build -f Containerfile.debug -t dbg .
podman run --rm dbg find /ctx -type f | sort
```

---

## 4. 複数コンテナのオーケストレーション：`compose.yaml`

Podman では2系統ありますが、現在のデファクトは **`podman compose`（サブコマンド版）** です。`podman-compose`（別パッケージの Python スクリプト）は補完的な位置づけになりつつあります。compose.yaml は docker-compose とほぼ同一文法：

```yaml
name: myapp                     # プロジェクト名を明示（pod名衝突を防ぐ）
services:
  web:
    build:
      context: .
      dockerfile: Containerfiles/Containerfile.prod
    image: myapp/web:1.0.0
    env_file:
      - envs/common.env
      - envs/web.env
    volumes:
      - ./data/web:/data:Z      # :Z で SELinux ラベル付与
    ports:
      - "8080:8080"
    restart: always
  db:
    image: docker.io/library/postgres:16
    volumes:
      - pgdata:/var/lib/postgresql/data:Z
    restart: always
volumes:
  pgdata:
networks:
  default:
```

**よくある落とし穴**: ディレクトリ名がプロジェクト名（=ポッド名）になるため、同じディレクトリで複数 compose を動かすと `pod_xxx is in use` 衝突が起きます。対策は↑のように `name:` を明示することです。

---

## 5. 本番運用：Quadlet + systemd（Podman 固有のデファクト）

コンテナを本番で安定稼働させるなら、`podman run` を手で叩くのではなく **Quadlet**（Podman 標準機能）で systemd ユニットを生成するのが現在のベストプラクティスです。`.container` / `.kube` / `.pod` / `.network` / `.volume` といった宣言ファイルを所定の場所に置くだけで、起動時に対応する systemd ユニットへ変換されます。

配置場所:
- rootful: `/etc/containers/systemd/`
- rootless: `~/.config/containers/systemd/`

例 `~/.config/containers/systemd/myapp.container`:

```ini
[Unit]
Description=MyApp container
After=network-online.target

[Container]
Image=myapp/web:1.0.0
ContainerName=myapp
PublishPort=8080:8080
Volume=%h/projects/myapp/data:/data:Z
EnvironmentFile=%h/projects/myapp/envs/web.env
AutoUpdate=registry
Exec=start

[Service]
Restart=always
TimeoutStartSec=180

[Install]
WantedBy=default.target
```

反映:
```bash
systemctl --user daemon-reload
systemctl --user start myapp.service
```

`AutoUpdate=registry` を付けると、systemd タイマー経由でイメージ自動更新も行われます（本番では `latest` タグを使わず固定タグ＋自動更新、が推奨）。

Compose と Quadlet の使い分け：
- **Compose**: 開発・簡易多コンテナ環境
- **Quadlet**: 本番・恒久運用（systemd で再起動・ログ・依存関係を一本化）

---

## 6. シークレット管理のベストプラクティス

Containerfile の `ARG` にシークレットを渡すと `podman history` で丸見えになるので NG。代わりに：

```bash
# ビルド時：--secret（最終イメージに残らない）
podman build --secret=id=npm_token,src=./secrets/npm_token.txt \
             -f Containerfiles/Containerfile.prod -t myapp:1.0.0 .
```

```dockerfile
# Containerfile 側
RUN --mount=type=secret,id=npm_token \
    NPM_TOKEN=$(cat /run/secrets/npm_token) npm ci
```

実行時は `--secret` 経由、または Quadlet の `Secret=`、Compose の `secrets:` を使います。`.env` は必ず `.gitignore` 対象にします。

---

## 7. イメージ管理のコマンド体系

```bash
# ビルド
podman build -t myapp/web:1.0.0 -f Containerfiles/Containerfile.prod .

# 履歴確認（シークレット漏洩チェックにも）
podman history myapp/web:1.0.0

# ローカル一覧・整理
podman images
podman image prune -f
podman rmi $(podman images -f dangling=true -q)

# レジストリへ Push（認証は podman login）
podman login registry.example.com
podman push myapp/web:1.0.0 registry.example.com/myapp/web:1.0.0

# マニフェストリストでマルチアーチ（要 qemu-user-static）
podman manifest create myapp:1.0.0
podman build --platform linux/amd64,linux/arm64 --manifest myapp:1.0.0 .
podman manifest push myapp:1.0.0 registry.example.com/myapp:1.0.0
```

---

## 8. Makefile でコマンドをラップ（小〜中規模プロジェクトの定石）

```makefile
IMAGE := myapp/web
TAG   := 1.0.0

.PHONY: build dev prod up down logs ps clean
build: ; podman build -t $(IMAGE):$(TAG) -f Containerfiles/Containerfile.prod .
dev:   ; podman build -t $(IMAGE):dev  -f Containerfiles/Containerfile.dev .
up:    ; podman compose up -d
down:  ; podman compose down
logs:  ; podman compose logs -f
ps:    ; podman compose ps
clean: ; podman compose down -v; podman image prune -f
```

---

## まとめ：管理上のチェックリスト

- [ ] 1サービス=1ディレクトリツリー（設定とデータを分離）
- [ ] 定義は `Containerfile`（互換なら `Dockerfile`）、複数環境はサフィックス
- [ ] `.containerignore` でコンテキスト最適化（allowlist 推奨）
- [ ] 多コンテナは `compose.yaml`、`name:` は明示
- [ ] 本番は **Quadlet + systemd**、イメージタグは固定＋`AutoUpdate`
- [ ] シークレットは `--secret` / `secrets:`、ARG には渡さない
- [ ] `podman history` で漏洩チェック、`podman image prune` で整理

この構成が、現在 Podman で「イメージのビルドから本番運用まで」を管理する上でのデファクトスタンダードとなっています。

---

## 参考リンク

- Red Hat 公式（dev container 構成例）: <https://developers.redhat.com/articles/2025/05/28/how-simplify-your-multi-repo-workflow-podman>
- `podman build` リファレンス: <https://docs.podman.io/en/stable/markdown/podman-build.1.html>
- Containerfile 仕様: <https://github.com/containers/common/blob/main/docs/Containerfile.5.md>
- Podman Compose: <https://github.com/containers/podman-compose/>