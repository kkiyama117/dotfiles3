We use `chezmoi` to manage the dotfiles. Below are the commands we use mainly.
For details, see the [chezmoi documentation](https://www.chezmoi.io/docs/).

| Command | Purpose |
| --- | --- |
| `chezmoi init <repo>` | Initialise the source directory from this repository. |
| `chezmoi apply` | Apply the managed dotfiles to `$HOME`. |
| `chezmoi diff` | Show the diff between the source state and the destination. |
| `chezmoi status` | List files whose state differs between source and destination. |
| `chezmoi add <path>` | Add an existing file under `$HOME` to the source directory. |
| `chezmoi edit <path>` | Edit a managed file via its source representation. |
| `chezmoi cd` | Open a shell in the source directory. |
| `chezmoi update` | `git pull` the source and `chezmoi apply` in one step. |


## Auto-commit via pi CLI hooks

After `chezmoi add` or `chezmoi edit`, a post-hook delegates commit message
writing to pi print mode (`pi -p`, model `cursor/composer-2.5:fast`). The
hook pattern is adapted from
<https://ikuma-t.com/blog/commit-chezmoi-diff-automaticaly-by-claude/>.

- `autoCommit = false` / `autoPush = false` — chezmoi itself does not commit;
  pi reviews diffs, stages changes, and creates the commit via bash tools.
- The `[git]` and `[hooks]` sections are gated to **host runtime only** via
  template conditionals in `.chezmoi.toml.tmpl`. They are omitted entirely
  when `DOTFILES_RUNTIME=container` or `BUILD_MODE=true`, so the hook never
  fires inside the container or during the build-prepass.
- The wrapper script lives at `programs/chezmoi_pi_commit.sh`.
- The commit prompt is in `.pi/prompts/commit.md` (repo-local, not deployed
  by chezmoi). Override the model with `PI_COMMIT_MODEL` if needed.

## chezmoi with bitwarden

https://www.chezmoi.io/user-guide/password-managers/bitwarden/#bitwarden-cli
