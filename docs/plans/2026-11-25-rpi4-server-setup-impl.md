# Raspberry Pi 4 headless server setup — Implementation Plan

**Status:** executing
**Spec:** [design](../specifications/implementations/2026-11-25-rpi4-server-setup-design.md)
**Parent issue:** [2026-11-25-rpi4-server-setup](../issues/2026-11-25-rpi4-server-setup.md)
**Review trail:** (none yet)

## Phases

### Phase 1 — Flash SD card (host)
1. tarball + `.md5` を取得し md5 検証（design §5）
2. `lsblk` / `/dev/disk/by-id` で SD カードを特定
3. `sudo programs/rpi4_setup/flash-alarm-sd.sh ...` を実行

**Acceptance**: script が `done.` まで完走し、表示された fstab の `/boot` が `UUID=` になっている
**Rollback**: 再度 script を実行（SD は毎回全消去）

### Phase 2 — First boot (Pi, wired)
1. 有線接続で起動、router で IP を確認
2. `ssh alarm@<ip>` が鍵で通り、パスワード SSH が拒否されることを確認
3. design §6 を実施

**Acceptance**: `pacman -Syu` 完了後に再起動して SSH 再接続できる
**Rollback**: Phase 1 からやり直し

### Phase 2.5 — Remote access (Pi, wired)
1. design §6.1 を実施（tailscale 導入・login・key expiry 無効化）

**Acceptance**: host から tailnet 経由 (`ssh alarm@colored`) で鍵ログインできる
**Rollback**: `tailscale logout && systemctl disable --now tailscaled`

### Phase 3 — Wi-Fi (Pi)
1. design §7 を実施

**Acceptance**: `networkctl` で有線・無線とも `routable`、`ip route` の default が有線優先
**Rollback**: `systemctl disable --now iwd` と `wlan.network` を削除

完了後、result-log を `docs/issues/2026-11-25-phase-rpi4-server-setup.md` に記録する。
