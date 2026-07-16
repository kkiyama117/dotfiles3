#!/usr/bin/env zsh
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
#   3. Migrates any existing managed external checkouts (`~/.pi`,
#      `~/.config/nvim`) to the selected transport URL so this startup's
#      `chezmoi apply` pulls over the same transport.
#   4. Authenticates Bitwarden when the bw_* podman secrets are mounted
#      (login-if-needed + `bw unlock --passwordfile`), then runs
#      `chezmoi apply --no-tty --force` so the real $HOME picks up the
#      latest dotfiles and resolves `bitwarden*` templates. Skipped
#      when /run/secrets/bw_password is absent (no-secret startup).
#   5. Seeds zoxide with first-run container paths.
#   6. Execs CMD.
set -euo pipefail

CHEZMOI_SOURCE="${HOME}/.local/share/chezmoi"
RUNTIME_CONFIG="${HOME}/.config/chezmoi/chezmoi.toml"
PI_CONFIG_SSH_URL="git@github.com:kkiyama117/pi-config.git"
PI_CONFIG_HTTPS_URL="https://github.com/kkiyama117/pi-config.git"
NVIM_CONFIG_SSH_URL="git@github.com:kkiyama117/nvim_config.git"
NVIM_CONFIG_HTTPS_URL="https://github.com/kkiyama117/nvim_config.git"
SELECTED_EXTERNAL_URL=""
# Readiness sentinel for `make up`'s wait loop. Written ONLY after
# `chezmoi apply` succeeds (so any `make exec` started after the sentinel
# exists is guaranteed a fully applied $HOME: ~/.zshrc, sheldon, starship,
# etc.). Removed at start so a container restart cannot satisfy the wait
# with a stale flag from a previous apply. Lives in /tmp — ephemeral per
# container, fresh on each `make up --replace`, NOT the chezmoi bind mount
# and NOT a named volume. See spec 20 I-RUN2 and
# docs/issues/2026-07-06-make-up-races-chezmoi-apply.md.
READINESS_SENTINEL="/tmp/chezmoi-applied"
rm -f "$READINESS_SENTINEL"
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
  local rc
  if wait "$child_pid"; then
    rc=0
  else
    rc=$?
  fi
  child_pid=""
  return "$rc"
}

validate_external_url() {
  local url="$1"
  case "$url" in
    http://*@*|https://*@*)
      echo "entrypoint: URL overrides must not contain HTTP(S) userinfo." >&2
      return 1
      ;;
  esac
}

select_external_url() {
  local override="$1"
  local ssh_url="$2"
  local https_url="$3"

  if [[ -n "$override" ]]; then
    validate_external_url "$override"
    SELECTED_EXTERNAL_URL="$override"
    return 0
  fi

  if run_interruptible timeout --signal=TERM --kill-after=2s 10s \
      env GIT_TERMINAL_PROMPT=0 \
      GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=5 -o ConnectionAttempts=1" \
      git ls-remote "$ssh_url" HEAD >/dev/null 2>&1; then
    SELECTED_EXTERNAL_URL="$ssh_url"
  else
    echo "entrypoint: warning: SSH unavailable for a managed external; using HTTPS fallback." >&2
    SELECTED_EXTERNAL_URL="$https_url"
  fi
}

set_external_remote_url() {
  local checkout="$1"
  local selected_url="$2"
  [[ -e "$checkout/.git" ]] || return 0

  if ! git -C "$checkout" remote get-url origin >/dev/null 2>&1; then
    echo "entrypoint: existing managed external has no origin remote." >&2
    return 1
  fi
  git -C "$checkout" remote set-url origin "$selected_url"
}

# ===========================================================================
# Zoxide setup functions
# ===========================================================================
resolve_zoxide_bin() {
  local zoxide_bin
  zoxide_bin="$(command -v zoxide 2>/dev/null || true)"
  if [[ -n "$zoxide_bin" && -x "$zoxide_bin" ]]; then
    print -r -- "$zoxide_bin"
    return 0
  fi

  local candidate
  for candidate in /usr/bin/zoxide /usr/sbin/zoxide; do
    if [[ -x "$candidate" ]]; then
      print -r -- "$candidate"
      return 0
    fi
  done

  return 1
}

seed_zoxide_paths() {
  local zoxide_bin
  if ! zoxide_bin="$(resolve_zoxide_bin)"; then
    return 0
  fi

  local path
  for path in "$CHEZMOI_SOURCE"; do
    if [[ -d "$path" ]]; then
      "$zoxide_bin" add -- "$path" || echo "entrypoint: warning: failed to seed zoxide path: $path" >&2
    fi
  done
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

# Resolve the transport for managed externals.  The SSH probe is
# interruptible and falls back to HTTPS so the first apply can succeed
# before the runtime SSH config / Bitwarden-backed key are installed.
select_external_url "${PI_CONFIG_URL:-}" "$PI_CONFIG_SSH_URL" "$PI_CONFIG_HTTPS_URL"
selected_pi_config_url="$SELECTED_EXTERNAL_URL"
select_external_url "${NVIM_CONFIG_URL:-}" "$NVIM_CONFIG_SSH_URL" "$NVIM_CONFIG_HTTPS_URL"
selected_nvim_config_url="$SELECTED_EXTERNAL_URL"

# Keep this render in the foreground: background jobs in non-interactive shell
# read redirected stdin from /dev/null, which would create an empty config.
PI_CONFIG_URL="$selected_pi_config_url" \
NVIM_CONFIG_URL="$selected_nvim_config_url" \
chezmoi execute-template --init \
  < "$CONFIG_TEMPLATE" \
  > "$RUNTIME_CONFIG"

# Ensure existing managed externals already point at the selected transport
# URL before this startup's `chezmoi apply` pulls them. Migration failure is
# fatal so the operator cannot silently stay on the old transport.
set_external_remote_url "$HOME/.pi" "$selected_pi_config_url"
set_external_remote_url "$HOME/.config/nvim" "$selected_nvim_config_url"

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

seed_zoxide_paths

# `chezmoi apply` succeeded: publish the readiness sentinel so `make up`
# (which polls for this file) can return. `set -e` above exits before this
# line if apply failed, so the sentinel is never written on failure —
# `make up` then sees the container exit and surfaces `podman logs`.
touch "$READINESS_SENTINEL"

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
