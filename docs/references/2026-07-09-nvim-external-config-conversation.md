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

See §6 for reviewer verdict: same workflow for both tools; layout divergence is
accepted.

### 5. Container verification (2026-07-09)

Verified in running container `dotfiles-manjaro`:

| Path | `.git`? | Notes |
|---|---|---|
| `~/.pi` | No | pi runtime parent |
| `~/.pi/agent` | No | symlinks only |
| `~/.local/share/pi-config` | **Yes** | chezmoi external git root |

```
~/.pi/agent/prompts   → ~/.local/share/pi-config/agent/prompts
~/.pi/agent/skills    → ~/.local/share/pi-config/agent/skills
~/.pi/agent/extensions → ~/.local/share/pi-config/agent/extensions
~/.pi/agent/themes    → ~/.local/share/pi-config/agent/themes
```

- Editing via `~/.pi/agent/prompts/foo.md` works; `git status` must run in
  `~/.local/share/pi-config`
- `git -C ~/.pi/agent` → `fatal: not a git repository`
- Container push via HTTPS fails without credentials; clone/pull works

### 6. Reviewer verdict: unified workflow, divergent layout (2026-07-09)

**Question:** Should pi and nvim use the same chezmoi external *pattern* (paths)?

**Verdict (Option C):** Same **workflow**, different **layout** — both OK.

| What is unified | pi | nvim |
|---|---|---|
| Separate repo outside dotfiles3 | `/data/pi-config` | `/data/nvim_config` |
| dotfiles role | URL + pin only | URL + pin only |
| Update flow | edit → `git add` → `commit` → `push` | same |
| Not via chezmoi | no `chezmoi add` for config | same |
| Build gating | `BUILD_MODE=true` skips fetch | same |

| What differs (tool constraints) | pi | nvim |
|---|---|---|
| Why | `~/.pi/agent` mixes config + runtime | `~/.config/nvim` is config-only |
| External target | `~/.local/share/pi-config` | `~/.config/nvim` |
| Edit path | `~/.pi/agent/...` (symlinks) | `~/.config/nvim` (direct) |
| Git root | `~/.local/share/pi-config` | `~/.config/nvim` |
| `.git` at edit path? | **No** | **Yes** |

Forcing one structural pattern is rejected:

- **Direct external for pi** → risky (runtime files in git checkout)
- **Staging+symlinks for nvim** → unnecessary complexity

Reviewer artifact:
`.pi-subagents/artifacts/5aabfcc6-20b4-4488-b722-27858d8923ed_reviewer_output.md`

### 7. Migration notes (host)

- Host `~/.config/nvim` currently points to legacy remote `miyake-ken/vimrc.git`
- `/data/nvim_config` is empty; bootstrap from existing config before first
  external apply
- First `chezmoi apply` with nvim external requires backup/remove of existing
  `~/.config/nvim` or chezmoi will conflict

---

## Decisions recorded

1. **Mechanism:** chezmoi external (`type = "git-repo"`), not submodule
2. **Unified workflow:** edit → git add → commit → push in external repo; dotfiles
   only pins URL/ref; no `chezmoi add` for config files
3. **nvim layout:** direct external to `~/.config/nvim` (git root = edit path)
4. **pi layout:** staging at `~/.local/share/pi-config` + symlinks to
   `~/.pi/agent` (commit from pi-config root, not `~/.pi/agent`)
5. **Authoring checkouts:** `/data/nvim_config`, `/data/pi-config` on host
6. **Remotes:** `kkiyama117/nvim_config`, `kkiyama117/pi-config`
7. **No dotfiles overlay:** entire config trees come from external repos
8. **Build mode:** no external fetch when `BUILD_MODE=true`
9. **Refresh:** `refreshPeriod = "0"`; explicit `--refresh-externals` when needed
10. **Pattern divergence:** accepted as technically justified (reviewer Option C)

---

## Next steps (implementation)

See [design](../specifications/implementations/2026-07-09-nvim-external-config-design.md)
and [issue](../issues/2026-07-09-nvim-external-config.md).
