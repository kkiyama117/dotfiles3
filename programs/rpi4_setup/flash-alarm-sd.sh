#!/usr/bin/env bash
# Flash Arch Linux ARM (rpi-aarch64) onto an SD card for a headless Raspberry Pi 4.
# Design: docs/specifications/implementations/2026-11-25-rpi4-server-setup-design.md
#
# Usage (as root):
#   flash-alarm-sd.sh --device /dev/disk/by-id/usb-... \
#                     --tarball ArchLinuxARM-rpi-aarch64-latest.tar.gz \
#                     --hostname <name> --ssh-pubkey ~/.ssh/main.pub --yes
#
# The device is WIPED. Wi-Fi credentials are never taken here (configure after boot).
set -euo pipefail

die() { echo "error: $*" >&2; exit 1; }
log() { echo "==> $*"; }

DEVICE="" TARBALL="" HOSTNAME_="" PUBKEY="" YES=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --device) DEVICE="$2"; shift 2 ;;
    --tarball) TARBALL="$2"; shift 2 ;;
    --hostname) HOSTNAME_="$2"; shift 2 ;;
    --ssh-pubkey) PUBKEY="$2"; shift 2 ;;
    --yes) YES=1; shift ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

[[ $EUID -eq 0 ]] || die "run as root"
[[ -n $DEVICE && -n $TARBALL && -n $HOSTNAME_ && -n $PUBKEY ]] || die "missing arguments (see --help)"
[[ -f $TARBALL ]] || die "tarball not found: $TARBALL"
[[ -f $PUBKEY ]] || die "ssh pubkey not found: $PUBKEY"
[[ $HOSTNAME_ =~ ^[a-z0-9-]{1,63}$ ]] || die "invalid hostname: $HOSTNAME_"

# Integrity check (md5 file published next to the tarball).
if [[ -f $TARBALL.md5 ]]; then
  log "verifying md5"
  (cd "$(dirname "$TARBALL")" && md5sum -c "$(basename "$TARBALL").md5") || die "md5 mismatch"
else
  echo "warning: $TARBALL.md5 not found, skipping integrity check" >&2
fi

# --- Safety checks on the target device (I1) ---
DEV=$(readlink -f "$DEVICE")
[[ -b $DEV ]] || die "not a block device: $DEV"
[[ $(lsblk -dno TYPE "$DEV") == disk ]] || die "$DEV is not a whole disk"
[[ $(lsblk -dno RM "$DEV" | tr -d ' ') == 1 ]] || die "$DEV is not removable; refusing"
size=$(lsblk -dbno SIZE "$DEV")
(( size <= 256 * 1024**3 )) || die "$DEV is larger than 256 GiB; refusing"
if lsblk -no MOUNTPOINTS "$DEV" | grep -q .; then
  die "$DEV has mounted partitions; unmount first"
fi

lsblk -o NAME,SIZE,TRAN,RM,MODEL,FSTYPE,LABEL "$DEV"
if [[ $YES -ne 1 ]]; then
  read -r -p "WIPE $DEV ? type the device path ($DEV) to continue: " ans
  [[ $ans == "$DEV" ]] || die "aborted"
fi

# Partition name suffix: mmcblk0 -> mmcblk0p1, sdc -> sdc1
p=""; [[ $DEV =~ [0-9]$ ]] && p="p"
BOOT_PART="${DEV}${p}1" ROOT_PART="${DEV}${p}2"

# --- Partition & format ---
log "partitioning $DEV"
wipefs -a "$DEV"
sfdisk "$DEV" <<'EOF'
label: dos
size=512MiB, type=c
type=83
EOF
partprobe "$DEV" 2>/dev/null || true
udevadm settle

log "formatting"
mkfs.vfat -F 32 -n ALARMBOOT "$BOOT_PART"
mkfs.ext4 -F -q -L ALARMROOT "$ROOT_PART"

# --- Extract ---
MNT=$(mktemp -d /tmp/alarm-sd.XXXXXX)
cleanup() { sync; umount -R "$MNT" 2>/dev/null || true; rmdir "$MNT" 2>/dev/null || true; }
trap cleanup EXIT

mount "$ROOT_PART" "$MNT"
mkdir -p "$MNT/boot"
mount "$BOOT_PART" "$MNT/boot"
log "extracting rootfs (takes a while)"
bsdtar -xpf "$TARBALL" -C "$MNT"
sync

# --- Make boot independent of mmcblk0/mmcblk1 naming (I2) ---
BOOT_UUID=$(blkid -s UUID -o value "$BOOT_PART")
ROOT_PARTUUID=$(blkid -s PARTUUID -o value "$ROOT_PART")
log "fstab: /boot -> UUID=$BOOT_UUID"
sed -i -E "s#^/dev/mmcblk[0-9]+p1([[:space:]])#UUID=${BOOT_UUID}\1#" "$MNT/etc/fstab"
grep -q "UUID=${BOOT_UUID}" "$MNT/etc/fstab" \
  || echo "UUID=${BOOT_UUID}  /boot  vfat  defaults  0  0" >> "$MNT/etc/fstab"
if [[ -f $MNT/boot/cmdline.txt ]]; then
  log "cmdline.txt: root -> PARTUUID=$ROOT_PARTUUID"
  sed -i -E "s#root=[^ ]+#root=PARTUUID=${ROOT_PARTUUID}#" "$MNT/boot/cmdline.txt"
fi

# --- Host identity & SSH (I3) ---
log "hostname: $HOSTNAME_"
echo "$HOSTNAME_" > "$MNT/etc/hostname"

ALARM_HOME="$MNT/home/alarm"
[[ -d $ALARM_HOME ]] || die "/home/alarm not found in rootfs"
uid=$(stat -c %u "$ALARM_HOME") gid=$(stat -c %g "$ALARM_HOME")
install -d -m 700 -o "$uid" -g "$gid" "$ALARM_HOME/.ssh"
install -m 600 -o "$uid" -g "$gid" "$PUBKEY" "$ALARM_HOME/.ssh/authorized_keys"

if grep -qE '^[[:space:]]*Include[[:space:]]+/etc/ssh/sshd_config.d/' "$MNT/etc/ssh/sshd_config"; then
  log "sshd: disable password auth"
  install -d "$MNT/etc/ssh/sshd_config.d"
  cat > "$MNT/etc/ssh/sshd_config.d/10-hardening.conf" <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
EOF
else
  echo "warning: sshd_config has no sshd_config.d Include; password auth left as default" >&2
fi

log "done. fstab:"
cat "$MNT/etc/fstab"
