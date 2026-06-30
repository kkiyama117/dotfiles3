#!/usr/bin/env bash
#
# Container entrypoint — runtime chezmoi apply against the host-bound source.
#
# The container is started by `make up` with the repo root bind-mounted at
# ~/.local/share/chezmoi. This script:
#   1. Verifies the bind is in place (the source root has .git).
#   2. Re-renders ~/.config/chezmoi/chezmoi.toml with build_mode = false
#      (the build-time toml was removed in Stage 4).
#   3. Authenticates Bitwarden when the bw_* podman secrets are mounted
#      (login-if-needed + `bw unlock --passwordfile`), then runs
#      `chezmoi apply --no-tty --force` so the real $HOME picks up the
#      latest dotfiles and resolves `bitwarden*` templates. Skipped
#      when /run/secrets/bw_password is absent (no-secret startup).
#   4. Execs CMD.
set -euo pipefail

CHEZMOI_SOURCE="${HOME}/.local/share/chezmoi"
RUNTIME_CONFIG="${HOME}/.config/chezmoi/chezmoi.toml"

if [[ ! -d "$CHEZMOI_SOURCE/.git" ]]; then
  echo "entrypoint: $CHEZMOI_SOURCE is not a chezmoi source (no .git)." >&2
  echo "entrypoint: did make up bind the repo root into ~/.local/share/chezmoi?" >&2
  exit 1
fi

mkdir -p "$(dirname "$RUNTIME_CONFIG")"
cat > "$RUNTIME_CONFIG" <<'TOML'
[data]
build_mode = false
TOML

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
  export BW_SESSION="$(bw unlock --passwordfile /run/secrets/bw_password --raw)"
fi

chezmoi apply --no-tty --force

# Scrub the Bitwarden credentials from this process's environment before
# exec'ing CMD. BW_SESSION was only needed for `chezmoi apply` (done); the
# client pair is no longer needed. This prevents the credentials from
# riding into PID 1 (e.g. `sleep infinity`) via /proc/1/environ for the
# container's lifetime. The master password was never in env (read via
# --passwordfile); nothing to scrub for it.
if [ -n "${BW_SESSION:-}" ]; then
  unset BW_CLIENTID BW_CLIENTSECRET BW_SESSION
fi

exec "$@"
