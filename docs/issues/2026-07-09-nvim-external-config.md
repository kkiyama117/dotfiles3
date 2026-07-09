# Manage nvim config as a chezmoi external repo

**Date:** 2026-07-09
**Status:** open
**Related:** [conversation log](../references/2026-07-09-nvim-external-config-conversation.md), [design](../specifications/implementations/2026-07-09-nvim-external-config-design.md), [plan](../plans/2026-07-09-nvim-external-config-impl.md), [pi-config design](../specifications/implementations/2026-07-08-pi-agent-container-git-managed-config-design.md), [spec 11](../specifications/11-pre-required-env-values.md), [reviewer artifact](../../.pi-subagents/artifacts/5aabfcc6-20b4-4488-b722-27858d8923ed_reviewer_output.md)

## Context

- Neovim config should live in a separate git repository, not inside
  `dotfiles3`.
- Host authoring checkout: `/data/nvim_config`
- GitHub remote: `https://github.com/kkiyama117/nvim_config.git`
- Deployed target on host and container: `~/.config/nvim`
- No dotfiles-managed nvim files; the full config tree comes from the external
  repo.
- This repository already uses `.chezmoiexternal.toml.tmpl` for pi-config
  (`~/.local/share/pi-config` + symlinks into `~/.pi/agent`). Nvim uses direct
  external to `~/.config/nvim` (no symlinks).
- **Unified workflow (pi + nvim):** separate repos, dotfiles pins URL/ref,
  config changes committed with normal git in the external checkout (not
  `chezmoi add`). Layout differs because pi mixes runtime state in
  `~/.pi/agent`; nvim config is config-only.
- Reviewer verdict (2026-07-09): accept layout divergence; unify workflow only.
  See [conversation log](../references/2026-07-09-nvim-external-config-conversation.md)
  §6.
- Host `~/.config/nvim` currently has legacy remote `miyake-ken/vimrc.git`;
  migration to `kkiyama117/nvim_config` required before first external apply.

## Problem

Define and implement a reproducible way to deploy nvim config from
`kkiyama117/nvim_config` to `~/.config/nvim` via chezmoi, while:

1. Keeping nvim source out of the dotfiles chezmoi tree and container build
   context
2. Documenting the edit → git add → commit → push workflow (externals are not
   authored via `chezmoi add`)
3. Gating external fetch out of `BUILD_MODE=true` container builds

## Acceptance criteria

1. `.chezmoiexternal.toml.tmpl` declares a `git-repo` external for
   `~/.config/nvim` when `build_mode` is false.
2. Default external URL is `https://github.com/kkiyama117/nvim_config.git` with
   a pinned ref (tag or commit) in `.chezmoi.toml.tmpl` data.
3. `NVIM_CONFIG_URL` and `NVIM_CONFIG_REF` env overrides are documented in
   spec 11 (local dev: `file:///data/nvim_config`).
4. `BUILD_MODE=true chezmoi execute-template --init` renders **no** nvim
   external block.
5. `chezmoi apply --refresh-externals=always` on host or container clones or
   updates `~/.config/nvim` as a normal git checkout (`.git/` present).
6. `make build` does not fetch or bake nvim config into image layers.
7. After `make up` and runtime `chezmoi apply`, container has nvim config at
   `~/.config/nvim` and `neovim` binary is available (already installed via
   pacman/AUR inventory).
8. Edit workflow is documented: changes are committed in the nvim external
   checkout (or `/data/nvim_config` authoring checkout), not via `chezmoi add`.
9. Unified external workflow doc covers both pi and nvim (same git workflow;
   pi commits from `~/.local/share/pi-config`, not `~/.pi/agent`).
10. Host migration path documented for legacy `~/.config/nvim` checkout.

## Notes

- Submodule approach was considered and rejected (see conversation log).
- Lazy.nvim / plugin data under `~/.local/share/nvim` remains unmanaged.
- pi-config `pi_config_ref` is defined but not yet used in `clone.args` (fix
  alongside nvim implementation).
- Implementation plan: [`docs/plans/2026-07-09-nvim-external-config-impl.md`](../plans/2026-07-09-nvim-external-config-impl.md)
