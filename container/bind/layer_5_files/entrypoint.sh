#!/usr/bin/env bash
#
# Container entrypoint — runtime chezmoi apply against the host-bound source.
#
# The container is started by `make up` with the repo root bind-mounted at
# ~/.local/share/chezmoi. This script:
#   1. Verifies the bind is in place (the source root has .git).
#   2. Renders ~/.config/chezmoi/chezmoi.toml from the source-root template
#      (.chezmoi.toml.tmpl) via `chezmoi execute-template --init`
#      (build_mode = false; BUILD_MODE unset at runtime). The build-prepass
#      toml is stripped in the runtime cleanup (Layer 5-3), so this creates
#      it fresh as ${USERNAME}.
#   3. Authenticates Bitwarden when the bw_* podman secrets are mounted
#      (login-if-needed + `bw unlock --passwordfile`), then runs
#      `chezmoi apply --no-tty --force` so the real $HOME picks up the
#      latest dotfiles and resolves `bitwarden*` templates. Skipped
#      when /run/secrets/bw_password is absent (no-secret startup).
#   4. Execs CMD.
set -euo pipefail

CHEZMOI_SOURCE="${HOME}/.local/share/chezmoi"
RUNTIME_CONFIG="${HOME}/.config/chezmoi/chezmoi.toml"
child_pid=""

terminate() {
  trap - TERM INT
  if [[ -n "$child_pid" ]]; then
    kill -TERM "$child_pid" 2>/dev/null || true
  fi
  exit 143
}

run_interruptible() {
  "$@" &
  child_pid=$!
  if wait "$child_pid"; then
    child_pid=""
    return 0
  fi
  local rc=$?
  child_pid=""
  return "$rc"
}

trap terminate TERM INT

if [[ ! -e "$CHEZMOI_SOURCE/.git" ]]; then
  echo "entrypoint: $CHEZMOI_SOURCE is not a chezmoi source (no .git)." >&2
  echo "entrypoint: did make up bind the repo root into ~/.local/share/chezmoi?" >&2
  exit 1
fi

mkdir -p "$(dirname "$RUNTIME_CONFIG")"
# Render the chezmoi config from the source-root template (.chezmoi.toml.tmpl)
# via `chezmoi execute-template --init`. build_mode is driven by BUILD_MODE env
# (unset here -> false, the runtime value). The config content lives in the
# dotfiles, not hardcoded in this script. Fail loudly if the template is
# missing (an older/incomplete source bind) — the entrypoint cannot produce a
# valid config without it.
CONFIG_TEMPLATE="${CHEZMOI_SOURCE}/.chezmoi.toml.tmpl"
if [[ ! -f "$CONFIG_TEMPLATE" ]]; then
  echo "entrypoint: $CONFIG_TEMPLATE is missing — cannot render chezmoi.toml." >&2
  echo "entrypoint: did make up bind the repo root (with .chezmoi.toml.tmpl) into ~/.local/share/chezmoi?" >&2
  exit 1
fi
# Mark this chezmoi apply as running inside the container. build_mode is
# already false here (BUILD_MODE unset at runtime); DOTFILES_RUNTIME
# distinguishes container runtime from host runtime for settings that must
# not appear in the container (e.g. credential.helper=libsecret — the
# container has no keyring daemon; see dot_config/git/config.tmpl I-GIT3).
export DOTFILES_RUNTIME=container
run_interruptible chezmoi execute-template --init \
  < "$CONFIG_TEMPLATE" \
  > "$RUNTIME_CONFIG"

# Bitwarden auto-auth (optional). When the three podman secrets are
# mounted (make up mounts each only if it exists), log in with the API
# key and unlock the vault so `chezmoi apply` can resolve `bitwarden*`
# templates. The master password is read straight from
# /run/secrets/bw_password via `bw unlock --passwordfile` — it never
# enters an environment variable. BW_CLIENTID / BW_CLIENTSECRET are
# exported only in this process (not on the image / -e flags, so they do
# not appear in `podman inspect`). If the secrets are absent, skip auth
# and let `chezmoi apply` run without BW_SESSION (no-secret startup).
if [ -f /run/secrets/bw_password ]; then
  export BW_CLIENTID="$(cat /run/secrets/bw_clientid)"
  export BW_CLIENTSECRET="$(cat /run/secrets/bw_clientsecret)"
  if ! bw login --check >/dev/null 2>&1; then
    bw login --apikey
  fi
  bw sync >/dev/null 2>&1 || true
  # `bw unlock --passwordfile --raw` can transiently return an empty
  # session if the vault data is not yet local / the server is not ready.
  # Retry a few times; if it stays empty, fail LOUDLY (exit) so the
  # operator knows auth failed instead of silently running with no
  # session (which would leave `bitwarden*` templates unresolvable).
  for _ in 1 2 3; do
    BW_SESSION="$(bw unlock --passwordfile /run/secrets/bw_password --raw 2>/dev/null || true)"
    if [ -n "$BW_SESSION" ]; then
      break
    fi
    sleep 2
  done
  if [ -z "$BW_SESSION" ]; then
    echo "entrypoint: bw unlock returned an empty session after retries." >&2
    echo "entrypoint: check the bw_password podman secret (master password) and network." >&2
    exit 1
  fi
  export BW_SESSION
fi

run_interruptible chezmoi apply --no-tty --force

# Scrub the Bitwarden credentials from this process's environment before
# exec'ing CMD — unconditionally within the auth-ran path (gated on the
# secret file, NOT on BW_SESSION being non-empty, so a transient empty
# session still gets the client pair scrubbed). BW_SESSION was only
# needed for `chezmoi apply` (done); the client pair is no longer
# needed. This prevents credentials from riding into PID 1 (e.g.
# `sleep infinity`) via /proc/1/environ for the container's lifetime.
# The master password was never in env (read via --passwordfile).
if [ -f /run/secrets/bw_password ]; then
  unset BW_CLIENTID BW_CLIENTSECRET BW_SESSION
fi

exec "$@"
