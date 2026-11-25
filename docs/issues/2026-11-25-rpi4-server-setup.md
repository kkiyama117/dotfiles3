# Raspberry Pi 4 headless server setup (Arch Linux ARM)

**Date:** 2026-11-25
**Status:** in-progress
**Related:** [result-log](2026-11-25-phase-rpi4-server-setup.md), [design](../specifications/implementations/2026-11-25-rpi4-server-setup-design.md), [plan](../plans/2026-11-25-rpi4-server-setup-impl.md)

## Context

- 手元の Raspberry Pi 4 をサーバー（headless, desktop 不要）として再セットアップしたい
- 既存 SD カード（64GB, USB カードリーダー経由で host の `/dev/sdc`）には
  2023-01-31 install / 2023-11-26 最終起動の Manjaro ARM（hostname `colored`,
  kernel `6.1.62-1-MANJARO-RPI4`）が残っている。データ保持は不要
  （2026-11-25 に read-only mount で確認、ユーザー確認済み）
- ネットワークは有線メイン、無線も別途使えるようにしたい

## Problem

- OS 選定（Manjaro ARM / Arch Linux ARM）と、SD カード作成〜初回起動〜初期設定の
  手順を再現可能な形で残す

## Acceptance criteria

- SD カード作成手順が script + doc として repo に残っている
- Pi 4 が有線 DHCP で起動し、host から公開鍵で SSH ログインできる
- 無線 (wlan0) を有線と併用可能な設定手順が doc にある
- 結果を result-log に残す

## Notes

- OS 比較・決定は design §2 を参照
