# Raspberry Pi 4 headless server setup (Arch Linux ARM) — Design

**Status:** DRAFT
**Date opened:** 2026-11-25
**Issue:** [2026-11-25-rpi4-server-setup](../../issues/2026-11-25-rpi4-server-setup.md)
**Plan:** [2026-11-25-rpi4-server-setup-impl](../../plans/2026-11-25-rpi4-server-setup-impl.md)
**Author:** kiyama

## §1 Context & success criteria

Raspberry Pi 4 を headless server として再構築する。SD カードは host 上で作成し、
初回起動後は SSH のみで操作する。

- **S1**: host 上の 1 コマンド（`programs/rpi4_setup/flash-alarm-sd.sh`）で
  SD カードを作成できる
- **S2**: 初回起動時点で有線 (DHCP) に接続し、host から公開鍵で
  `ssh alarm@<host>` できる。パスワード SSH は無効
- **S3**: 無線 (wlan0) を有線と併用でき、有線が優先される（route metric）
- **S4**: Wi-Fi 認証情報・パスワードなど secret は repo / script 引数に残らない
- **S5**: 手順が本 design と plan で再現できる

## §2 Alternatives considered

| 候補 | 評価 |
|---|---|
| **Arch Linux ARM `rpi-aarch64`** (採用) | 公式 tarball が 2026 時点でも更新継続。headless 前提で sshd + systemd-networkd(DHCP) が初期有効。host (Manjaro) と同じ pacman 系 |
| Manjaro ARM minimal | 2026 時点のメンテ状況が不明瞭。minimal で Wi-Fi 不可 / root autologin 不可の報告あり。stable branch 遅延は server 用途で利点が薄い |
| 既存 Manjaro ARM (2023) を更新 | 約 3 年放置で更新破損リスク大。データ保持不要のため却下 |
| Raspberry Pi OS / Ubuntu Server | ユーザー要望 (Manjaro or Arch) 外 |

参照 (2026-11-25 取得):
- <https://archlinuxarm.org/platforms/armv8/broadcom/raspberry-pi-4>
- <https://archlinuxarm.org/about/downloads>
- <https://manjaro.org/products/download/arm>

## §3 Architecture / Invariants

- **I1**: flash script は破壊的操作の前に対象を検証する — whole disk / removable
  (`RM=1`) / 256 GiB 以下 / 未マウント。`--yes` が無ければデバイスパス入力で確認。
  デバイスは `/dev/disk/by-id/...` で指定することを推奨
- **I2**: 起動が `mmcblk0` / `mmcblk1` の命名に依存しない。`/etc/fstab` の
  `/boot` は `UUID=`、`cmdline.txt` が存在する場合 `root=PARTUUID=` に書き換える。
  （公式手順の `sed s/mmcblk0/mmcblk1/` は kernel 種別によって正誤が変わるため採用しない）
  2026-11-25 取得の tarball は mainline `linux-aarch64` 7.1.6 + `uboot-raspberrypi`
  で、root は `boot.txt` 内で既に `root=PARTUUID=${uuid}`、`cmdline.txt` は無い。
  よって実際に効くのは fstab の書き換えのみ
- **I3**: 初回起動前に hostname と `alarm` ユーザーの `authorized_keys` を配置し、
  `sshd_config.d/10-hardening.conf` で `PasswordAuthentication no` /
  `PermitRootLogin no` にする。default password (`alarm`/`root`) は SSH から使えない
- **I4**: Wi-Fi は初回起動後に Pi 上で設定する（secret を host 側 script に渡さない, S4）
- **I5**: 有線 `RouteMetric` < 無線 `RouteMetric`（有線優先, S3）

## §4 Scope / staging

1. **Stage A (host)**: tarball 取得 + md5 検証 → `flash-alarm-sd.sh`
2. **Stage B (Pi, 有線)**: pacman keyring 初期化、`-Syu`、password 変更、
   作業ユーザー作成
3. **Stage C (Pi)**: Wi-Fi (iwd + systemd-networkd)
4. Out of scope: サービス構築（用途確定後に別 issue）、chezmoi による Pi の
   dotfiles 管理（aarch64 で container 前提の構成が使えるかは別途検討, Q2）

## §5 Stage A — SD card (host)

```sh
# 取得先は scratchpad 等の一時ディレクトリでよい
curl -LO http://os.archlinuxarm.org/os/ArchLinuxARM-rpi-aarch64-latest.tar.gz
curl -LO http://os.archlinuxarm.org/os/ArchLinuxARM-rpi-aarch64-latest.tar.gz.md5
md5sum -c ArchLinuxARM-rpi-aarch64-latest.tar.gz.md5

lsblk -o NAME,SIZE,TRAN,RM,MODEL,LABEL      # 対象を確認
ls -l /dev/disk/by-id/ | grep usb

sudo programs/rpi4_setup/flash-alarm-sd.sh \
  --device /dev/disk/by-id/usb-<reader>-0:0 \
  --tarball ./ArchLinuxARM-rpi-aarch64-latest.tar.gz \
  --hostname <name> --ssh-pubkey ~/.ssh/main.pub
```

script の処理: 検証 (I1) → `wipefs` → `sfdisk` (dos, p1=512MiB FAT32 /
p2=ext4 残り) → mkfs → root/boot を mount → `bsdtar -xpf` → I2 → I3。

## §6 Stage B — first boot (Pi, wired)

有線を挿して電源投入。IP は router の DHCP lease で確認する
（固定したい場合は router 側で DHCP reservation を推奨）。

```sh
ssh alarm@<ip>
su -                                   # root / root
passwd                                 # root password 変更
passwd alarm
pacman-key --init
pacman-key --populate archlinuxarm
# 2026-11-25: 既定の geo-redirect (mirror.archlinuxarm.org) が同期遅れの mirror に
# 振り分け 404 になったため、同期済みの近傍 mirror を先頭に固定する
sed -i '1i Server = http://tw.mirror.archlinuxarm.org/$arch/$repo\nServer = http://tw2.mirror.archlinuxarm.org/$arch/$repo' /etc/pacman.d/mirrorlist
pacman -Syyu
pacman -S sudo
# 作業ユーザーを作る場合
useradd -m -G wheel <user>
install -d -m700 -o <user> -g <user> /home/<user>/.ssh
install -m600 -o <user> -g <user> /home/alarm/.ssh/authorized_keys /home/<user>/.ssh/
EDITOR=vi visudo                       # %wheel ALL=(ALL:ALL) ALL を有効化
timedatectl set-timezone Asia/Tokyo
reboot
```

### §6.1 Remote access (openssh + Tailscale)

遠隔地へ持ち出して操作するため、手元 (同一 LAN) にあるうちに Tailscale を設定する。

- **I6**: openssh は tarball で `sshd.service` が既に enabled。鍵認証のみ (I3) のまま
  tailnet 経由でも同じ sshd を使う（Tailscale SSH は使わない）
- **I7**: Tailscale の認証はブラウザ login URL で行い、auth key を Pi や repo に残さない (S4)

```sh
pacman -S tailscale
systemctl enable --now tailscaled
systemctl is-enabled sshd               # enabled であること
tailscale up --hostname=colored         # 表示される URL を host のブラウザで開いて承認
tailscale ip -4
```

- Tailscale admin console で `colored` の **Disable key expiry** を設定する
  （既定の key expiry で遠隔地から到達不能になるのを防ぐ）
- 持ち出し前に host から `ssh alarm@colored`（MagicDNS）または `ssh alarm@<100.x>`
  で接続できることを確認する
- 遠隔地が Wi-Fi のみの場合は、持ち出し前に §7 で当地の SSID を登録しておく

### §6.2 Finding the Pi on another LAN (via jump host)

Pi を host と別の LAN（例: 既存 ssh 先 `polaris` のいる LAN）で起動する場合、
その LAN 上のマシンで `programs/rpi4_setup/find-pi.sh` を実行して IP を探す。

- **I8**: 依存は `bash` / `iproute2` / `ping` のみ（nmap 等を jump host に要求しない）。
  直結 subnet（/22 以下の大きさ）だけを ping sweep し、neighbour table の MAC を
  Raspberry Pi の OUI (`b8:27:eb`, `dc:a6:32`, `e4:5f:01`, `d8:3a:dd`, `28:cd:c1`,
  `2c:cf:67`, `88:a2:9e`) と照合して TCP 22 を probe する

```sh
ssh polaris 'bash -s' < programs/rpi4_setup/find-pi.sh
# => PI  10.x.x.x  dc:a6:32:..  dev=enp5s0  ssh=open
ssh -J polaris -i ~/.ssh/main -o IdentitiesOnly=yes alarm@10.x.x.x   # §6 / §6.1 を実施
```

- `~/.ssh/main` は default identity ではないため `-i` 必須（無いと `Permission denied (publickey)`）
- 2026-11-25 実機確認: 有線 IF 名は `end0`（`en.network` の `en*` に match）、
  SD は `mmcblk1` として認識され `/boot` は UUID 指定 (I2) で正常 mount。
  `pacman -Syu` で kernel 7.1.6 → 7.3.6 に更新・再起動後は `mmcblk0` に変わった
  （公式手順の固定 `sed` では kernel 更新で起動失敗し得たことの実例、I2 の根拠）

Tailscale 設定 (§6.1) 後は jump host 不要（`ssh alarm@colored`）。

## §7 Stage C — Wi-Fi (Pi)

ALARM は systemd-networkd 構成。無線は iwd で認証のみ行い、IP は networkd に任せる。

```sh
pacman -S iwd
systemctl enable --now iwd
```

（tarball には `wpa_supplicant` が同梱されているが、networkd との組み合わせが
簡潔な iwd を採用する。iwd は有線経由で導入する）

`/etc/systemd/network/` に以下を置く。有線は tarball 同梱の `en.network` と
`eth.network`（いずれも `DHCP=yes`）の両方に `RouteMetric` を追記する:

```ini
# /etc/systemd/network/en.network と eth.network に追記
[DHCPv4]
RouteMetric=100

# /etc/systemd/network/wlan.network
[Match]
Name=wlan*

[Network]
DHCP=yes

[DHCPv4]
RouteMetric=600
```

```sh
systemctl restart systemd-networkd
iwctl station wlan0 connect <SSID>     # passphrase は対話入力 (I4)
networkctl status; ip route            # 有線 default route の metric が小さいこと
```

## §8 Open questions

- **Q1**: 固定 IP を Pi 側 (networkd `Address=`) で持つか router reservation にするか
- **Q2**: Pi 上の dotfiles を chezmoi で管理するか（本 repo は container 前提のため
  aarch64 host 向けの subset が必要）
- **Q3**: Pi の用途（どのサービスを載せるか）。確定後に別 issue
