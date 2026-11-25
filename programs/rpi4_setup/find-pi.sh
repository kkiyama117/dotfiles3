#!/usr/bin/env bash
# Find Raspberry Pi devices on the local IPv4 subnet(s) of the machine it runs on.
# Design: docs/specifications/implementations/2026-11-25-rpi4-server-setup-design.md §6.2
#
# Usage:
#   programs/rpi4_setup/find-pi.sh                       # on this machine
#   ssh <jump-host> 'bash -s' < programs/rpi4_setup/find-pi.sh   # on a remote LAN
#
# Ping-sweeps each directly connected subnet (prefix >= /22 only), then matches
# the neighbour table against Raspberry Pi Ltd / Foundation MAC OUIs and probes TCP 22.
set -uo pipefail

PI_OUI='^(b8:27:eb|dc:a6:32|e4:5f:01|d8:3a:dd|28:cd:c1|2c:cf:67|88:a2:9e)'

ip2int() { local IFS=.; read -r a b c d <<<"$1"; echo $(( (a<<24)|(b<<16)|(c<<8)|d )); }
int2ip() { echo "$(( $1>>24&255 )).$(( $1>>16&255 )).$(( $1>>8&255 )).$(( $1&255 ))"; }

# Directly connected, non-loopback, non-tailscale subnets
while read -r dev cidr; do
  ip=${cidr%/*} len=${cidr#*/}
  if (( len < 22 )); then echo "skip $dev $cidr (too large)" >&2; continue; fi
  n=$(ip2int "$ip"); mask=$(( (0xffffffff << (32-len)) & 0xffffffff ))
  net=$(( n & mask )); bcast=$(( net | (~mask & 0xffffffff) ))
  echo "sweeping $dev $(int2ip $net)/$len" >&2
  for (( h=net+1; h<bcast; h++ )); do
    ping -c1 -W1 -I "$dev" "$(int2ip $h)" >/dev/null 2>&1 &
    (( (h - net) % 64 == 0 )) && wait
  done
  wait
done < <(ip -4 -o addr show scope global | awk '$2 !~ /^(lo|tailscale|docker|podman|virbr|veth)/ {print $2, $4}')

found=0
while read -r addr _ dev _ mac _; do
  [[ ${mac,,} =~ $PI_OUI ]] || continue
  found=1
  if timeout 2 bash -c "</dev/tcp/$addr/22" 2>/dev/null; then ssh=open; else ssh=closed; fi
  echo "PI  $addr  $mac  dev=$dev  ssh=$ssh"
done < <(ip -4 neigh show | awk '$4=="lladdr" {print $1, "dev", $3, "lladdr", $5, $6}')

(( found )) || echo "no Raspberry Pi MAC found" >&2
