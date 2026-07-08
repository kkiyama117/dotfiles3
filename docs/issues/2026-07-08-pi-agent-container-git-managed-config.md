# Install pi agent in the container with git-managed config

**Date:** 2026-07-08
**Status:** open
**Related:** [design](../specifications/implementations/2026-07-08-pi-agent-container-git-managed-config-design.md), [plan](../plans/2026-07-08-pi-agent-container-git-managed-config-impl.md), [spec 02](../specifications/02-installed-programs.md), [spec 11](../specifications/11-pre-required-env-values.md), [spec 21](../specifications/21-container-build-flow.md), [chezmoi reference](../references/chezmoi_reference.md), [host config inventory](../references/host_config_list.md)

## Context

- The container already has the Node/pnpm toolchain path work needed for
  global JavaScript CLI tooling, and `pnpm = "latest"` is managed by mise.
- Pi is distributed as the npm package
  `@earendil-works/pi-coding-agent`; upstream documents
  `npm install -g --ignore-scripts @earendil-works/pi-coding-agent` as the
  normal install path.
- Pi stores global state under `~/.pi/agent` by default. Project-local
  resources and settings live under `.pi/` in a project checkout.
- The host-side chezmoi auto-commit hook reads the pi commit prompt from
  external pi config and linked runtime paths, not from this repository.
  Precedence: `PI_COMMIT_PROMPT_FILE`, then `~/.pi/agent/prompts/commit.md`,
  then `~/.local/share/pi-config/agent/prompts/commit.md`. The stable prompt
  lives in the external `pi-config` repo; chezmoi links it into `~/.pi/agent`
  at apply time. `.pi` remains excluded from both `.chezmoiignore` and
  `.containerignore`.
- There is no `.chezmoiexternal.toml` in this repository yet. Chezmoi externals
  are the intended mechanism for fetching externally managed source state
  without vendoring it directly into this repository.

## Problem

Install the `pi` CLI in the container and define a safe, reproducible way to
manage the desired `.pi` configuration with git via `.chezmoiexternal.toml`,
without committing or baking credentials, sessions, trust decisions, package
caches, or other mutable agent state.

The design needs to distinguish:

1. **Pi binary installation** in the container image or persistent tool volume.
2. **Git-managed `.pi` resources** such as prompts, settings, skills,
   extensions, and package manifests.
3. **Runtime-only pi state** such as auth, sessions, trust, logs, downloaded
   packages, and caches.

## Acceptance criteria

1. The container has a working `pi` executable available on `PATH`; after
   `make up`, `podman exec dotfiles-manjaro zsh -ic 'pi --version'` exits 0.
2. The chosen install mechanism is documented and reproducible. If the npm
   package is used, lifecycle scripts remain disabled during install
   (`--ignore-scripts`) unless a reviewed design explicitly requires otherwise.
3. `.chezmoiexternal.toml` or `.chezmoiexternal.toml.tmpl` exists and fetches
   the git-managed `.pi` source from a pinned, reviewable source/ref.
4. The managed `.pi` scope is explicit: only stable project/global resources
   are managed. Auth files, sessions, trust files, logs, npm/git package
   checkouts, and caches are excluded from git, chezmoi deploy, and image
   build layers unless a later design explicitly permits a specific path.
5. `.chezmoiignore` and `.containerignore` are updated so the intended `.pi`
   resources are included where needed and excluded where unsafe.
6. Container startup/apply flow preserves runtime pi state across
   `make down && make up` only through approved runtime storage, not through
   committed source files or baked image contents.
7. Existing host auto-commit behavior keeps working via the external pi config
   prompt and linked runtime paths (`PI_COMMIT_PROMPT_FILE`, then
   `~/.pi/agent/prompts/commit.md`, then
   `~/.local/share/pi-config/agent/prompts/commit.md`), with equivalent
   tests/documentation.
8. Specs 02, 11, and 21 are updated to document the pi package, any required
   non-secret environment variables, the container build/runtime flow, and
   secret/session exclusions.
9. Focused verification covers:
   - `pi --version` in the running container.
   - chezmoi external fetch/application of the managed `.pi` content.
   - absence of known sensitive pi paths from git and image build context.

## Notes

- Do not commit provider credentials, OAuth artifacts, API keys, sessions,
  transcripts, trust decisions, or downloaded package checkouts.
- Decide during design whether `.pi` represents project-local resources in the
  chezmoi source checkout, deployed global pi config under `~/.pi`, or both.
- Decide during design whether the pi CLI should be installed by npm, pnpm, or
  another package manager. The upstream npm command is the current documented
  baseline.
- If project-local pi packages are used, account for pi project trust behavior:
  interactive pi asks for trust before loading project `.pi` resources, while
  non-interactive mode relies on `defaultProjectTrust` or `--approve` /
  `--no-approve`.
