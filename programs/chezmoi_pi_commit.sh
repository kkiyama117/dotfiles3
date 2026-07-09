#!/usr/bin/env bash
# chezmoi post-hook: delegate commit message writing to pi CLI (print mode).
# Invoked after `chezmoi add` or `chezmoi edit` on host runtime only.
# Gating to host is done in .chezmoi.toml.tmpl — the [hooks] section is
# omitted entirely when DOTFILES_RUNTIME=container or BUILD_MODE=true.
#
# Adapted from https://ikuma-t.com/blog/commit-chezmoi-diff-automaticaly-by-claude/
set -euo pipefail

src_dir="${CHEZMOI_SOURCE:-$(chezmoi source-path 2>/dev/null || echo "$HOME/.local/share/chezmoi")}"
cd "$src_dir"

if ! command -v pi &>/dev/null; then
  echo "chezmoi commit hook: pi CLI not found — skipping auto-commit." >&2
  exit 0
fi

# Only invoke pi if there are uncommitted changes.
if git diff --quiet 2>/dev/null && git diff --cached --quiet 2>/dev/null && \
   [ -z "$(git ls-files --others --exclude-standard)" ]; then
  exit 0
fi

prompt_candidates=(
  "${PI_COMMIT_PROMPT_FILE:-}"
  "$HOME/.pi/agent/prompts/commit.md"
  "$HOME/.local/share/pi-config/agent/prompts/commit.md"
)

prompt_file=""
for candidate in "${prompt_candidates[@]}"; do
  if [ -n "$candidate" ] && [ -f "$candidate" ]; then
    prompt_file="$candidate"
    break
  fi
done

if [ -z "$prompt_file" ]; then
  echo "chezmoi commit hook: missing pi commit prompt — skipping auto-commit." >&2
  exit 0
fi

prompt="$(sed '/^---$/,/^---$/d' "$prompt_file")"

if ! pi -p \
  --no-session \
  --no-approve \
  --no-extensions \
  --no-skills \
  --no-prompt-templates \
  --tools bash,read \
  --model "${PI_COMMIT_MODEL:-cursor/composer-2.5:fast}" \
  "$prompt"; then
  echo "chezmoi commit hook: pi commit failed — leaving changes uncommitted." >&2
  exit 0
fi
