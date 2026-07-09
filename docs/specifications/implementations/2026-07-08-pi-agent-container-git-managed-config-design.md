# pi Agent Container Install + External Config — Design

**Status:** DRAFT
**Date opened:** 2026-07-08
**Issue:** [`docs/issues/2026-07-08-pi-agent-container-git-managed-config.md`](../../issues/2026-07-08-pi-agent-container-git-managed-config.md)
**Author:** kiyama

## §1 Context & success criteria

The container should ship a working `pi` CLI, while pi configuration is managed
as a separate git repository outside `dotfiles3`. The intended authoring checkout
is:

```text
/data/pi-config
```

and the likely remote is:

```text
https://github.com/kkiyama117/pi-config.git
```

This keeps pi's managed resources out of the chezmoi source tree and avoids
turning the live `.pi/` runtime directory into part of `dotfiles3`.

Pi's upstream documentation says the CLI is distributed as the npm package
`@earendil-works/pi-coding-agent`, installed with:

```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
```

Pi stores mutable global state under `~/.pi/agent` by default. Stable resources
such as `settings.json`, prompts, skills, extensions, and themes can be
git-managed, but auth, sessions, trust decisions, downloaded packages, logs, and
caches must remain runtime state.

- **S1:** After `make up`, `podman exec dotfiles-manjaro zsh -ic 'pi --version'`
  exits 0.
- **S2:** The pi CLI install mechanism is declared in the tool inventory and
  documented in specs 02 and 21.
- **S3:** `/data/pi-config` is the local editing checkout for pi config, with
  its own git history and `.gitignore`; it is not nested under `dotfiles3`.
- **S4:** `dotfiles3` consumes the pi config through
  `.chezmoiexternal.toml.tmpl`, defaulting to the pinned GitHub remote/ref and
  allowing a local `file:///data/pi-config` override for development.
- **S5:** The external is applied to a non-runtime target, proposed as
  `~/.local/share/pi-config`; pi's live runtime directory remains
  `~/.pi/agent`.
- **S6:** Only stable resources are linked or copied from
  `~/.local/share/pi-config` into `~/.pi/agent`; auth/session/trust/package/cache
  paths are never managed.
- **S7:** Build mode does not fetch pi config externals. Runtime `chezmoi apply`
  may fetch them after the container starts.
- **S8:** The existing host chezmoi auto-commit prompt is moved to the external
  pi config repo or the wrapper is updated to read the new deployed location.
- **S9:** Verification proves the pi CLI works, the external config can be
  refreshed/applied, and sensitive pi runtime paths are absent from git and image
  layers.

## §2 Alternatives considered

- **A1 — Separate `/data/pi-config` repo + `.chezmoiexternal.toml.tmpl`
  consumer (chosen).** Edit pi config in its own checkout, publish it to
  `kkiyama117/pi-config`, and let chezmoi fetch a pinned ref into a safe target
  under `$HOME`. This keeps repo boundaries clean, avoids submodule friction, and
  lets pi runtime state remain unmanaged.
- **A2 — Git submodule inside `dotfiles3`.** Rejected. It still places the pi
  config tree inside the chezmoi source repo, so `.chezmoiignore` and
  `.containerignore` must defend against accidental deployment/build inclusion.
  It also adds submodule init/update friction for a dotfile config dependency.
- **A3 — In-repo `pi-manage/` folder.** Rejected for the preferred path. It
  avoids a live `.pi/` collision, but it is still metadata inside `dotfiles3`;
  ignore rules and build-context policy remain necessary.
- **A4 — Manage `~/.pi/agent` directly as a git checkout.** Rejected. Pi writes
  auth, sessions, trust, package clones, and other mutable state there. Making
  the whole directory a git checkout invites accidental secret/session commits
  and dirty runtime state.
- **A5 — Set `PI_CODING_AGENT_DIR=/data/pi-config`.** Rejected. It would mix
  stable config with pi runtime state in the external repo and may not exist
  inside the container unless separately mounted.

## §3 Architecture / invariants

- **I1 (repo boundary):** `/data/pi-config` is an independent git repository.
  `dotfiles3` contains only the consumer definition and any symlinks/templates
  needed to expose resources to pi.
- **I2 (remote is canonical for apply):** The default external source is the
  GitHub remote, not the local `/data/pi-config` path. Local file URLs are an
  override for development only, because containers and fresh hosts cannot assume
  `/data/pi-config` exists.
- **I3 (pinning):** The external source must be pinned to a commit or immutable
  tag before the design is approved. Branch tracking is acceptable only for a
  temporary bootstrap phase.
- **I4 (runtime state separation):** `~/.pi/agent` remains pi's runtime state
  root. Managed config is stored separately, then exposed through narrowly scoped
  symlinks or copied files.
- **I5 (no managed secrets):** `auth.json`, provider API keys, OAuth artifacts,
  sessions, transcripts, trust decisions, logs, downloaded npm/git package
  checkouts, and caches are excluded from both repositories and from image build
  layers.
- **I6 (build safety):** `.chezmoiexternal.toml.tmpl` emits no pi-config external
  when `BUILD_MODE=true`. The image build must not depend on GitHub availability
  or fetch user config into a baked layer.
- **I7 (container runtime):** Runtime `chezmoi apply` may fetch the external pi
  config after Bitwarden/bootstrap has completed. This is acceptable because the
  pi config repo contains no secrets.
- **I8 (host hook compatibility):** The host auto-commit hook must not depend on
  a `.pi/` directory inside `dotfiles3`. It reads the prompt from the managed pi
  config target, or from a documented override path.
- **I9 (project-local `.pi` remains ignored):** Any `.pi/` directory that appears
  inside `dotfiles3` is treated as pi project/runtime state unless explicitly
  reintroduced by a later design. The default remains ignored.

## §4 Scope / staging breakdown

1. **External repo bootstrap** — create `/data/pi-config`, add a restrictive
   `.gitignore`, move stable pi resources into it, and publish to
   `kkiyama117/pi-config` if desired.
2. **Chezmoi external consumer** — add `.chezmoiexternal.toml.tmpl` to
   `dotfiles3`; gate it out of build mode; default to the GitHub remote/ref.
3. **Resource exposure** — add source-state symlinks or templates so pi reads
   stable resources from `~/.local/share/pi-config` while runtime state stays in
   `~/.pi/agent`.
4. **Pi CLI installation** — install `@earendil-works/pi-coding-agent` in the
   container via the chosen npm/pnpm path with lifecycle scripts disabled unless
   review approves otherwise.
5. **Host hook migration** — update `programs/chezmoi_pi_commit.sh` to read the
   commit prompt from the new managed location, with a clear override variable.
6. **Docs/tests** — update specs 02/11/21 and focused tests for external policy,
   ignored sensitive paths, and hook prompt resolution.

## §5 Implementation detail

### §5.1 `/data/pi-config` repository layout

The external repo should contain only stable, reviewable pi resources:

```text
/data/pi-config/
├── README.md
├── .gitignore
└── agent/
    ├── settings.json
    ├── prompts/
    │   └── commit.md
    ├── skills/
    ├── extensions/
    └── themes/
```

The repo-level `.gitignore` must exclude mutable/sensitive pi state even if a
future layout accidentally creates it:

```gitignore
auth.json
trust.json
sessions/
logs/
cache/
npm/
git/
*.log
```

### §5.2 Chezmoi external target

`dotfiles3` should not clone pi config directly into `~/.pi/agent`. Instead,
fetch it under an XDG data path:

```text
~/.local/share/pi-config
```

That target may be a git external managed by `.chezmoiexternal.toml.tmpl`. The
implementation must verify the exact pinning syntax supported by the installed
chezmoi version, but the intended shape is:

```toml
{{- if not .build_mode }}
[".local/share/pi-config"]
type = "git-repo"
url = "{{ .pi_config_url }}"
# pin to .pi_config_ref once kkiyama117/pi-config exists
{{- end }}
```

Template data defaults should be:

- `pi_config_url = "https://github.com/kkiyama117/pi-config.git"`

No committed default ref is defined until `kkiyama117/pi-config` exists.
Before this design can move from DRAFT to Approved, the implementation plan
must replace bootstrap branch tracking with an immutable commit or tag and
record the exact pinning mechanism for the installed chezmoi version.

For local development, override the URL to:

```text
file:///data/pi-config
```

The local file URL must not be the committed default, because it will not exist
on fresh machines or inside the container unless deliberately mounted.

### §5.3 Exposing resources to pi

Pi should keep its default runtime root:

```text
~/.pi/agent
```

Chezmoi should expose only stable resources from the external checkout, for
example:

```text
~/.pi/agent/settings.json -> ~/.local/share/pi-config/agent/settings.json
~/.pi/agent/prompts       -> ~/.local/share/pi-config/agent/prompts
~/.pi/agent/skills        -> ~/.local/share/pi-config/agent/skills
~/.pi/agent/extensions    -> ~/.local/share/pi-config/agent/extensions
~/.pi/agent/themes        -> ~/.local/share/pi-config/agent/themes
```

Do not symlink or manage:

```text
~/.pi/agent/auth.json
~/.pi/agent/trust.json
~/.pi/agent/sessions/
~/.pi/agent/npm/
~/.pi/agent/git/
~/.pi/agent/logs/
```

### §5.4 Ignore policy

Because `/data/pi-config` is outside `dotfiles3`, the old "how do we prevent an
in-repo `.pi` tree from deploying or entering the build context?" problem is
reduced. Still, `dotfiles3` should keep defensive rules:

- `.chezmoiignore` keeps `.pi` ignored unless a future design explicitly manages
  a project-local `.pi` file.
- `.containerignore` keeps `.pi` and `.pi-subagents` ignored.
- No `pi-config/` or `pi-manage/` directory is added under `dotfiles3`.

The external target `~/.local/share/pi-config` is managed by
`.chezmoiexternal.toml.tmpl`, not by a normal source directory in `dotfiles3`.

### §5.5 Pi CLI install

The default implementation path is to install the upstream npm package with
scripts disabled:

```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
```

If the container standardizes on pnpm global installs instead, the design must
verify the equivalent no-lifecycle-script behavior and PATH outcome before
switching. In either case, `pi --version` is the acceptance smoke test.

### §5.6 Host auto-commit prompt

`programs/chezmoi_pi_commit.sh` currently reads:

```text
<chezmoi-source>/.pi/prompts/commit.md
```

This should move to one of:

```text
${PI_COMMIT_PROMPT_FILE}
~/.pi/agent/prompts/commit.md
~/.local/share/pi-config/agent/prompts/commit.md
```

in that precedence order. After migration, the in-repo `.pi/prompts/commit.md`
can be removed from `dotfiles3` or kept only as a short bootstrap fallback if the
implementation plan justifies it.

## §6 Verification plan

- `chezmoi execute-template --init` renders host/runtime config without
  template errors.
- `BUILD_MODE=true chezmoi execute-template --init` renders no pi-config
  external.
- `chezmoi apply --refresh-externals=always --dry-run` shows the external
  target and symlink changes without touching sensitive paths.
- `make build` does not fetch or bake `/data/pi-config`,
  `~/.local/share/pi-config`, or `~/.pi/agent` runtime state.
- `make up` followed by
  `podman exec dotfiles-manjaro zsh -ic 'pi --version'` exits 0.
- `podman exec dotfiles-manjaro zsh -ic 'test -r ~/.pi/agent/prompts/commit.md'`
  exits 0 after runtime apply.
- Git checks confirm no known sensitive pi paths are tracked in either repo.

## §7 Open questions

- **Q1:** What exact `.chezmoiexternal.toml` field or URL convention should pin
  the git external for the installed chezmoi version?
- **Q2:** Should `kkiyama117/pi-config` be public? Public is preferred because
  the config must contain no secrets and private GitHub auth would complicate
  container startup.
- **Q3:** Should `settings.json` be symlinked from the external repo, or copied
  so interactive `/settings` changes do not dirty `/data/pi-config`?
- **Q4:** Should pi be installed with npm exactly as upstream documents, or via
  pnpm now that `PNPM_HOME` is on PATH?
- **Q5:** Is the host auto-commit prompt global pi config, dotfiles-specific pi
  config, or a separate hook-owned prompt? The first implementation should pick
  one and remove the old in-repo ambiguity.
