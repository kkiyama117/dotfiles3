# nvim External Config via chezmoi — Design

**Status:** DRAFT
**Date opened:** 2026-07-09
**Issue:** [`docs/issues/2026-07-09-nvim-external-config.md`](../../issues/2026-07-09-nvim-external-config.md)
**Conversation:** [`docs/references/2026-07-09-nvim-external-config-conversation.md`](../../references/2026-07-09-nvim-external-config-conversation.md)  
**Reviewer:** [`.pi-subagents/artifacts/5aabfcc6-…_reviewer_output.md`](../../../.pi-subagents/artifacts/5aabfcc6-20b4-4488-b722-27858d8923ed_reviewer_output.md)
**Author:** kiyama

## §1 Context & success criteria

Neovim configuration should be maintained in a separate git repository outside
`dotfiles3`, while chezmoi deploys it to the standard XDG path on host and
container.

| Role | Path |
|---|---|
| Host authoring checkout | `/data/nvim_config` |
| GitHub remote | `https://github.com/kkiyama117/nvim_config.git` |
| Deployed target (host + container) | `~/.config/nvim` |

Unlike pi-config, nvim does not require a staging directory and symlinks:
Neovim reads config from `~/.config/nvim` directly, and runtime/plugin state
(`~/.local/share/nvim`, lazy.nvim cache, etc.) lives outside that tree.

No dotfiles-managed nvim files. The entire `~/.config/nvim` tree comes from
the external repo.

### Unified workflow with pi-config (reviewer verdict 2026-07-09)

pi and nvim share the **same operational workflow** but use **different
directory layouts** (Option C — technically justified divergence):

| Unified (both tools) | pi | nvim |
|---|---|---|
| Separate repo | `/data/pi-config` → `kkiyama117/pi-config` | `/data/nvim_config` → `kkiyama117/nvim_config` |
| dotfiles role | URL + pin in `.chezmoiexternal.toml.tmpl` | same |
| Config edits | `git add` → `commit` → `push` in external repo | same |
| Not via chezmoi | no `chezmoi add` for config files | same |
| Build | `BUILD_MODE=true` skips external fetch | same |

| Layout (differs) | pi | nvim |
|---|---|---|
| External target | `~/.local/share/pi-config` | `~/.config/nvim` |
| Edit path | `~/.pi/agent/...` (symlinks) | `~/.config/nvim` (direct) |
| Git root | `~/.local/share/pi-config` | `~/.config/nvim` |
| Reason | `~/.pi/agent` mixes config + runtime state | `~/.config/nvim` is config-only |

**pi commit rule:** edits via `~/.pi/agent/prompts/` are visible to git, but
`git add/commit/push` must run from `~/.local/share/pi-config` (container
verified: `~/.pi/agent` has no `.git`).

**nvim commit rule:** edit path and git root are the same (`~/.config/nvim`).

- **S1:** After runtime `chezmoi apply`, `~/.config/nvim` exists as a git
  checkout of `kkiyama117/nvim_config` (`.git/` present, editable).
- **S2:** Host authoring checkout `/data/nvim_config` is the preferred edit
  location; deployed copy at `~/.config/nvim` is updated via push + refresh.
- **S3:** `dotfiles3` consumes nvim config through
  `.chezmoiexternal.toml.tmpl` with pinned GitHub remote/ref and optional
  `file:///data/nvim_config` override for local development.
- **S4:** `BUILD_MODE=true` renders no nvim external; container image build does
  not fetch user nvim config.
- **S5:** Runtime `chezmoi apply` in the container may fetch the external after
  bootstrap.
- **S6:** Edit workflow is documented: external files are committed with normal
  git in the nvim repo checkout, not via `chezmoi add`.
- **S7:** `make build` does not bake `/data/nvim_config` or `~/.config/nvim`
  into image layers.
- **S8:** Verification proves clone/refresh works on host and container, and
  neovim starts with the deployed config.

## §2 Alternatives considered

- **A1 — Separate `/data/nvim_config` repo + `.chezmoiexternal.toml.tmpl`
  direct to `~/.config/nvim` (chosen).** Matches user paths, keeps repo
  boundaries clean, and preserves the familiar edit → git commit → push workflow
  at the deployed path. Chezmoi only clones/pulls; no `chezmoi add` needed.
- **A2 — Git submodule inside `dotfiles3`.** Rejected. Places nvim tree inside
  chezmoi source; requires submodule init before build; pollutes build context
  unless heavily ignored. Same rejection rationale as pi-config design.
- **A3 — Staging dir + symlinks (pi-config pattern).** Rejected for nvim.
  `~/.config/nvim` has no mixed runtime state like `~/.pi/agent`; direct
  external is simpler and matches Neovim's expected config path. Reviewer
  (2026-07-09) confirmed: forcing pi's pattern onto nvim adds complexity with
  no benefit; forcing nvim's direct pattern onto pi is risky (runtime state in
  git checkout).
- **A4 — Manage `~/.config/nvim` entirely in dotfiles3 source.** Rejected.
  User explicitly wants a separate repository.
- **A5 — Chezmoi source with only a stub `dot_config/nvim` pointing elsewhere.**
  Rejected. Does not give a separate git history or independent nvim repo
  workflow.

## §3 Architecture / invariants

- **I1 (repo boundary):** `/data/nvim_config` (and `kkiyama117/nvim_config`) is
  an independent git repository. `dotfiles3` contains only the consumer
  definition (external URL/pin).
- **I2 (remote is canonical for apply):** Default external source is the GitHub
  remote, not `/data/nvim_config`. Local `file://` URL is a development override
  only.
- **I3 (pinning):** External ref must be pinned to an immutable tag or commit
  before design moves to Approved. Branch tracking acceptable only during
  bootstrap.
- **I4 (direct target):** External clones directly to `~/.config/nvim`. No
  symlink indirection required.
- **I5 (build safety):** `.chezmoiexternal.toml.tmpl` emits no nvim external
  when `BUILD_MODE=true`. Image build must not depend on GitHub availability or
  bake user nvim config.
- **I6 (runtime state unmanaged):** `~/.local/share/nvim`, lazy.nvim plugin
  cache, swap/backup dirs, and session data remain outside both repositories.
- **I7 (no chezmoi add for externals):** Changes to nvim config are committed in
  the external git checkout (or authoring checkout), then pushed. dotfiles
  commits only change URL/pin.
- **I8 (refresh policy):** `refreshPeriod = "0"` — no automatic pull. User or
  automation runs `chezmoi apply --refresh-externals=always` or `git pull`
  explicitly when syncing from remote.

## §4 Scope / staging breakdown

1. **External repo bootstrap** — ensure `/data/nvim_config` is published to
   `kkiyama117/nvim_config` with appropriate `.gitignore` (local overrides,
   plugin artifacts if any leak into config dir).
2. **Chezmoi external consumer** — extend `.chezmoiexternal.toml.tmpl` with nvim
   block; gate out of build mode.
3. **Template data** — add `nvim_config_url` and `nvim_config_ref` to
   `.chezmoi.toml.tmpl` with GitHub defaults and env overrides.
4. **Docs** — update spec 11 (env vars), host config inventory (nvim external
   entry); document unified workflow with pi-config.
5. **pi-config pinning fix** — wire `pi_config_ref` into pi external
   `clone.args` (currently defined but unused).
6. **Tests** — extend container/chezmoi tests: build mode omits external;
   runtime apply creates git checkout (if test harness supports network or
   fixture).

## §5 Implementation detail

### §5.1 `/data/nvim_config` repository

Expected layout (illustrative; owned by nvim repo):

```text
/data/nvim_config/
├── README.md
├── .gitignore
├── init.lua              # or init.vim
├── lua/
├── plugin/
└── …
```

Repo `.gitignore` should exclude at minimum:

```gitignore
*.swp
*.swo
.netrwhist
```

Plugin manager artifacts should not live under `~/.config/nvim` in the repo
(lazy.nvim default: `~/.local/share/nvim/lazy`).

### §5.2 Chezmoi external target

Add to `.chezmoiexternal.toml.tmpl` (alongside existing pi-config block):

```toml
{{- /* nvim config external. Build mode must not fetch user config into image layers. */ -}}
{{- if not .build_mode }}
[".config/nvim"]
type = "git-repo"
url = "{{ .nvim_config_url }}"
refreshPeriod = "0"
clone.args = ["--branch", "{{ .nvim_config_ref }}", "--depth", "1"]
pull.args = ["--ff-only"]
{{- end }}
```

Add to `.chezmoi.toml.tmpl` `[data]`:

```toml
nvim_config_url = {{ env "NVIM_CONFIG_URL" | default "https://github.com/kkiyama117/nvim_config.git" | quote }}
nvim_config_ref = {{ env "NVIM_CONFIG_REF" | default "<bootstrap-tag>" | quote }}
```

Local development override:

```text
NVIM_CONFIG_URL=file:///data/nvim_config
```

The implementation plan must replace `<bootstrap-tag>` with an immutable tag
before design approval.

**Pinning note:** Verify clone/pin syntax against installed chezmoi (v2.70+).
If branch-in-URL pinning is preferred over `clone.args`, document the chosen
mechanism in the implementation plan.

### §5.3 Edit / commit workflow

Shared rule for **all** chezmoi externals in this repo: config changes are
committed with normal git in the **external git root**, not via `chezmoi add`.
dotfiles commits only change URL/pin.

**nvim — primary path (host authoring checkout):**

```bash
cd /data/nvim_config
nvim init.lua
git add -A && git commit -m "…" && git push
chezmoi apply --refresh-externals=always
```

**nvim — direct path (deployed checkout; git root = edit path):**

```bash
nvim ~/.config/nvim/init.lua
cd ~/.config/nvim
git add init.lua && git commit -m "…" && git push
```

**pi — for comparison (git root ≠ edit path):**

```bash
nvim ~/.pi/agent/prompts/commit.md    # edit via symlink
cd ~/.local/share/pi-config            # commit from git root
git add agent/prompts/commit.md && git commit -m "…" && git push
```

**Container quick edit (nvim):**

```bash
podman exec -it dotfiles-manjaro zsh
cd ~/.config/nvim
nvim init.lua
git add -A && git commit -m "…" && git push   # requires git credentials
```

Container push via HTTPS fails without credentials (verified); prefer host for
commits unless SSH/HTTPS auth is configured in the container.

### §5.4 Host migration

Before first nvim external apply on host:

1. Host `~/.config/nvim` currently tracks legacy remote `miyake-ken/vimrc.git`
   (not `kkiyama117/nvim_config`).
2. `/data/nvim_config` is empty; populate from existing config or fresh clone.
3. Backup or remove `~/.config/nvim` before `chezmoi apply` clones the
   external, or chezmoi will report inconsistent state.

Suggested migration:

```bash
# 1. Copy existing config to authoring checkout
cp -a ~/.config/nvim/. /data/nvim_config/
cd /data/nvim_config
git init && git remote add origin https://github.com/kkiyama117/nvim_config.git
git add -A && git commit -m "Initial nvim config" && git push -u origin main

# 2. Tag for pinning
git tag nvim-config-v2026-07-09-1 && git push origin nvim-config-v2026-07-09-1

# 3. Remove deployed copy so chezmoi can clone
mv ~/.config/nvim ~/.config/nvim.pre-external-backup

# 4. Apply external
chezmoi apply --refresh-externals=always
```

### §5.5 Build and container policy

- **Layer 2 (build-prepass):** `BUILD_MODE=true` → no nvim external in rendered
  `.chezmoiexternal.toml`; build-prepass does not clone nvim config.
- **Layer 5 (runtime entrypoint):** `chezmoi apply` with `BUILD_MODE` unset may
  clone nvim config on first container start.
- **`.containerignore`:** no change required if nvim config is never vendored
  into `dotfiles3` source.
- **Neovim binary:** already declared in package inventory; this design does not
  change install mechanism.

### §5.6 Ignore policy

- No `dot_config/nvim/` tree in `dotfiles3`. Nvim config is entirely external.

## §6 Verification plan

- `chezmoi execute-template --init` renders host config with nvim external
  block and template data.
- `BUILD_MODE=true chezmoi execute-template --init` renders **no** nvim external.
- `chezmoi apply --refresh-externals=always --dry-run` shows external target
  `.config/nvim`.
- After apply on host: `test -d ~/.config/nvim/.git` and
  `git -C ~/.config/nvim remote -v` shows `kkiyama117/nvim_config`.
- `make build` completes without fetching nvim config (no nvim tree in image
  layers from external).
- After `make up` + runtime apply:
  `podman exec dotfiles-manjaro test -d /home/kiyama/.config/nvim/.git` (or
  `$USERNAME`).
- `podman exec dotfiles-manjaro zsh -ic 'nvim --version'` exits 0.

## §7 Open questions

- **Q1:** What immutable tag should bootstrap `nvim_config_ref`? (Set when
  `kkiyama117/nvim_config` is first published.)
- **Q2:** Should `clone.args` use `--branch` + tag (as pi-config) or URL fragment
  pinning for the installed chezmoi version?
- **Q3:** Is `kkiyama117/nvim_config` public? Public is preferred (simplifies
  container fetch).
- **Q4:** Migration steps documented in §5.4; confirm backup strategy before
  first apply on host.
- **Q5:** Should container runtime bind-mount `/data/nvim_config` for dev
  (parallel to `PI_CONFIG_URL=file:///…`), or is GitHub-only fetch sufficient?
