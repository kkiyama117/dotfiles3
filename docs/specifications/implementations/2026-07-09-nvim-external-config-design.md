# nvim External Config via chezmoi — Design

**Status:** DRAFT
**Date opened:** 2026-07-09
**Issue:** [`docs/issues/2026-07-09-nvim-external-config.md`](../../issues/2026-07-09-nvim-external-config.md)
**Conversation:** [`docs/references/2026-07-09-nvim-external-config-conversation.md`](../../references/2026-07-09-nvim-external-config-conversation.md)
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

Per [host config inventory](../../references/host_config_list.md), only
`~/.config/nvim/rc/secrets.vim` is currently dotfiles-managed. This design
moves secrets to a non-conflicting path while the main config comes from the
external repo.

- **S1:** After runtime `chezmoi apply`, `~/.config/nvim` exists as a git
  checkout of `kkiyama117/nvim_config` (`.git/` present, editable).
- **S2:** Host authoring checkout `/data/nvim_config` is the preferred edit
  location; deployed copy at `~/.config/nvim` is updated via push + refresh.
- **S3:** `dotfiles3` consumes nvim config through
  `.chezmoiexternal.toml.tmpl` with pinned GitHub remote/ref and optional
  `file:///data/nvim_config` override for local development.
- **S4:** Secrets remain dotfiles-managed at `~/.config/nvim-secrets/` and are
  sourced by the nvim config; they do not live in the external repo.
- **S5:** `BUILD_MODE=true` renders no nvim external; container image build does
  not fetch user nvim config.
- **S6:** Runtime `chezmoi apply` in the container may fetch the external after
  bootstrap; nvim config repo must contain no secrets.
- **S7:** Edit workflow is documented: external files are committed with normal
  git in the nvim repo checkout, not via `chezmoi add`.
- **S8:** `make build` does not bake `/data/nvim_config` or `~/.config/nvim`
  into image layers.
- **S9:** Verification proves clone/refresh works on host and container, secrets
  overlay does not conflict, and neovim starts with the deployed config.

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
  external is simpler and matches Neovim's expected config path.
- **A4 — Manage `~/.config/nvim` entirely in dotfiles3 source.** Rejected.
  User explicitly wants a separate repository.
- **A5 — Chezmoi source with only a stub `dot_config/nvim` pointing elsewhere.**
  Rejected. Does not give a separate git history or independent nvim repo
  workflow.

## §3 Architecture / invariants

- **I1 (repo boundary):** `/data/nvim_config` (and `kkiyama117/nvim_config`) is
  an independent git repository. `dotfiles3` contains only the consumer
  definition (external URL/pin) and secrets overlay.
- **I2 (remote is canonical for apply):** Default external source is the GitHub
  remote, not `/data/nvim_config`. Local `file://` URL is a development override
  only.
- **I3 (pinning):** External ref must be pinned to an immutable tag or commit
  before design moves to Approved. Branch tracking acceptable only during
  bootstrap.
- **I4 (direct target):** External clones directly to `~/.config/nvim`. No
  symlink indirection required.
- **I5 (secrets separation):** Secrets live at `~/.config/nvim-secrets/` (or
  equivalent) managed by dotfiles `private_*` source files. The nvim external
  repo must not contain secrets; its `.gitignore` may list `rc/secrets.vim` if
  that path is ever copied locally.
- **I6 (build safety):** `.chezmoiexternal.toml.tmpl` emits no nvim external
  when `BUILD_MODE=true`. Image build must not depend on GitHub availability or
  bake user nvim config.
- **I7 (runtime state unmanaged):** `~/.local/share/nvim`, lazy.nvim plugin
  cache, swap/backup dirs, and session data remain outside both repositories.
- **I8 (no chezmoi add for externals):** Changes to nvim config are committed in
  the external git checkout (or authoring checkout), then pushed. dotfiles
  commits only change URL/pin or secrets overlay.
- **I9 (refresh policy):** `refreshPeriod = "0"` — no automatic pull. User or
  automation runs `chezmoi apply --refresh-externals=always` or `git pull`
  explicitly when syncing from remote.

## §4 Scope / staging breakdown

1. **External repo bootstrap** — ensure `/data/nvim_config` is published to
   `kkiyama117/nvim_config` with appropriate `.gitignore` (exclude secrets,
   local overrides, plugin artifacts if any leak into config dir).
2. **Chezmoi external consumer** — extend `.chezmoiexternal.toml.tmpl` with nvim
   block; gate out of build mode.
3. **Template data** — add `nvim_config_url` and `nvim_config_ref` to
   `.chezmoi.toml.tmpl` with GitHub defaults and env overrides.
4. **Secrets migration** — move dotfiles-managed secrets from
   `~/.config/nvim/rc/secrets.vim` to `~/.config/nvim-secrets/secrets.vim`
   (or keep path under `private_dot_config/nvim-secrets/`); update nvim repo to
   source the new path.
5. **Docs** — update spec 11 (env vars), host config inventory, conversation
   reference; add verification steps.
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
rc/secrets.vim
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

### §5.3 Secrets overlay

Move dotfiles-managed secrets out of the external tree:

| Source (dotfiles3) | Deployed path |
|---|---|
| `private_dot_config/nvim-secrets/private_secrets.vim` | `~/.config/nvim-secrets/secrets.vim` |

In the nvim repo (`init.lua` or early config):

```lua
local secrets = vim.fn.expand("~/.config/nvim-secrets/secrets.vim")
if vim.fn filereadable(secrets) == 1 then
  vim.cmd("source " .. secrets)
end
```

Update [host config inventory](../../references/host_config_list.md) to reflect
the new secrets path.

No `run_after` copy script is required if secrets live outside `~/.config/nvim`.

### §5.4 Edit / commit workflow

**Primary path (host authoring checkout):**

```bash
cd /data/nvim_config
nvim init.lua
git add -A && git commit -m "…" && git push
chezmoi apply --refresh-externals=always
```

**Direct path (deployed checkout — same git repo):**

```bash
nvim ~/.config/nvim/init.lua
cd ~/.config/nvim
git add init.lua && git commit -m "…" && git push
```

**Secrets (dotfiles-managed):**

```bash
chezmoi edit ~/.config/nvim-secrets/secrets.vim
chezmoi apply
# commits go to dotfiles3 via chezmoi hooks, not nvim repo
```

**Container quick edit:**

```bash
podman exec -it dotfiles-manjaro zsh
cd ~/.config/nvim
nvim init.lua
git add -A && git commit -m "…" && git push   # requires git credentials
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

- No `dot_config/nvim/` tree in `dotfiles3` except secrets under
  `private_dot_config/nvim-secrets/`.
- If legacy `private_dot_config/nvim/rc/secrets.vim` exists on host, migration
  removes or renames it during implementation.

## §6 Verification plan

- `chezmoi execute-template --init` renders host config with nvim external
  block and template data.
- `BUILD_MODE=true chezmoi execute-template --init` renders **no** nvim external.
- `chezmoi apply --refresh-externals=always --dry-run` shows external target
  `.config/nvim` without touching secrets path.
- After apply on host: `test -d ~/.config/nvim/.git` and
  `git -C ~/.config/nvim remote -v` shows `kkiyama117/nvim_config`.
- `test -f ~/.config/nvim-secrets/secrets.vim` after secrets migration apply.
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
- **Q3:** Is `kkiyama117/nvim_config` public? Public is preferred (no secrets in
  repo; simplifies container fetch).
- **Q4:** Does existing host `~/.config/nvim` need a one-time migration script,
  or manual move to `/data/nvim_config` before first external apply?
- **Q5:** Should container runtime bind-mount `/data/nvim_config` for dev
  (parallel to `PI_CONFIG_URL=file:///…`), or is GitHub-only fetch sufficient?
