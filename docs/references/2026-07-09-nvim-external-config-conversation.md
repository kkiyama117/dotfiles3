# Conversation log: nvim external config via chezmoi

**Date:** 2026-07-09  
**Status:** reference  
**Related:** [issue](../issues/2026-07-09-nvim-external-config.md), [design](../specifications/implementations/2026-07-09-nvim-external-config-design.md), [pi-config design](../specifications/implementations/2026-07-08-pi-agent-container-git-managed-config-design.md)

---

## Goal

Separate the Neovim configuration from `dotfiles3` while still deploying it to
`~/.config/nvim` on host and container via chezmoi.

| Location | Path |
|---|---|
| Host authoring checkout | `/data/nvim_config` |
| GitHub remote | `https://github.com/kkiyama117/nvim_config.git` |
| Deployed target (host + container) | `~/.config/nvim` |

---

## Discussion summary

### 1. Submodule vs chezmoi external

**Question:** For a separate nvim repo, should we use a git submodule or
`.chezmoiexternal.toml`?

**Conclusion:** Use **chezmoi external** (`type = "git-repo"`), matching the
existing pi-config pattern in this repository.

Reasons (same as pi-config design):

- Keeps nvim source out of the chezmoi source tree and Podman build context
- Avoids submodule init/update friction
- Allows `BUILD_MODE=true` gating so container image build does not fetch user
  config
- dotfiles3 only stores URL/pin; nvim repo keeps its own git history

Git submodule was rejected for the same reasons documented in the pi-config
design.

### 2. “Can I edit and commit external config?”

**Initial concern:** With chezmoi external, there is no `chezmoi add`. Files
under `~/.pi` or `~/.config/nvim` do not feel git-managed the way chezmoi
source files do.

**Clarification:** Chezmoi external **does** create a normal git working tree
(with `.git/`) at the external target. There is no `chezmoi add` because
externals are **consumed**, not authored through chezmoi.

| | chezmoi source files | chezmoi externals |
|---|---|---|
| Storage | chezmoi source dir | target path (e.g. `~/.config/nvim`) |
| Add files | `chezmoi add` | N/A |
| Edit | `chezmoi edit` | edit directly in the checkout |
| Commit | chezmoi hooks / auto-commit | normal `git` in the external repo |
| dotfiles role | full source of truth | URL + pin only |

### 3. Update workflow (the key insight)

**Old mental model (still valid for nvim):**

```bash
nvim ~/.config/nvim/init.lua
cd ~/.config/nvim
git add … && git commit && git push
```

**With chezmoi external targeting `~/.config/nvim`:** the workflow is **the
same**. Chezmoi only runs the initial `git clone` (and optional `git pull` on
refresh). Day-to-day edits use normal git in that directory.

```bash
# First time only (or on new machine):
chezmoi apply                    # clones external → ~/.config/nvim

# Daily workflow (unchanged):
nvim ~/.config/nvim/init.lua
cd ~/.config/nvim
git add init.lua
git commit -m "…"
git push
```

`chezmoi apply --refresh-externals=always` is for **pulling remote changes**
(e.g. after editing on another machine), not after every local commit.

**Optional host authoring checkout** (`/data/nvim_config`):

```bash
cd /data/nvim_config
# edit, git add, commit, push
chezmoi apply --refresh-externals=always   # updates ~/.config/nvim
```

### 4. pi-config vs nvim (why pi felt different)

pi uses a **staging dir + symlinks** pattern because `~/.pi/agent` mixes stable
config with runtime state (auth, sessions, npm cache):

```text
~/.local/share/pi-config/     ← git repo
~/.pi/agent/prompts/            ← symlink into pi-config
```

For nvim, **direct external to `~/.config/nvim`** is sufficient. Neovim runtime
state (`~/.local/share/nvim`, lazy.nvim cache, etc.) lives outside the config
tree.

### 5. secrets.vim

Per [host config inventory](host_config_list.md), only
`~/.config/nvim/rc/secrets.vim` is currently dotfiles-managed; the rest of nvim
config is outside dotfiles.

**Decision:** Keep secrets in dotfiles at a **separate path** so they do not
conflict with the external checkout:

```text
~/.config/nvim-secrets/secrets.vim   ← chezmoi-managed (dotfiles)
~/.config/nvim/                      ← chezmoi external (nvim_config repo)
```

The nvim repo's `init.lua` (or equivalent) sources the secrets file from the
separate path.

### 6. Oracle verification (2026-07-09)

An advisory review confirmed in the running container:

- `~/.local/share/pi-config/.git` exists and `git status` works
- External checkouts are editable; `chezmoi apply --refresh-externals` with
  uncommitted local changes preserves the working tree
- `pull.args = ["--ff-only"]` fails if local and remote diverge — push or rebase
  first

---

## Decisions recorded

1. **Mechanism:** chezmoi external (`type = "git-repo"`), not submodule
2. **Target path:** `~/.config/nvim` (direct external, Option A)
3. **Authoring checkout:** `/data/nvim_config` on host
4. **Remote:** `kkiyama117/nvim_config`
5. **Secrets:** separate `~/.config/nvim-secrets/` managed by dotfiles
6. **Build mode:** no external fetch when `BUILD_MODE=true`
7. **Refresh:** `refreshPeriod = "0"`; explicit `--refresh-externals` when needed

---

## Next steps (implementation)

See [design](../specifications/implementations/2026-07-09-nvim-external-config-design.md)
and [issue](../issues/2026-07-09-nvim-external-config.md).
