#!/usr/bin/env bash
#
# Container entrypoint — runtime chezmoi apply against the host-bound source.
#
# The container is started by `make up` with the repo root bind-mounted at
# ~/.local/share/chezmoi. This script:
#   1. Verifies the bind is in place (the source root has .git).
#   2. Re-renders ~/.config/chezmoi/chezmoi.toml with build_mode = false
#      (the build-time toml was removed in Stage 4).
#   3. Runs `chezmoi apply --no-tty --force` so the real $HOME picks up the
#      latest dotfiles, optionally resolving Bitwarden secrets when the
#      operator exported BW_SESSION before `make up`.
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

chezmoi apply --no-tty --force

exec "$@"
