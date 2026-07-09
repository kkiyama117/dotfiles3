# Manage nvim config as a chezmoi external repo

**Date:** 2026-07-09
**Status:** open
**Related:** [conversation log](../references/2026-07-09-nvim-external-config-conversation.md), [design](../specifications/implementations/2026-07-09-nvim-external-config-design.md), [pi-config design](../specifications/implementations/2026-07-08-pi-agent-container-git-managed-config-design.md), [host config inventory](../references/host_config_list.md), [spec 11](../specifications/11-pre-required-env-values.md)

## Context

- Neovim config should live in a separate git repository, not inside
  `dotfiles3`.
- Host authoring checkout: `/data/nvim_config`
- GitHub remote: `https://github.com/kkiyama117/nvim_config.git`
- Deployed target on host and container: `~/.config/nvim`
- Currently only `~/.config/nvim/rc/secrets.vim` is dotfiles-managed per
  [host config inventory](../references/host_config_list.md); the rest of nvim
  config is unmanaged by chezmoi source.
- This repository already uses `.chezmoiexternal.toml.tmpl` for pi-config
  (`~/.local/share/pi-config`). The nvim case is simpler: direct external to
  the standard XDG config path with no symlink indirection.
- Conversation and design rationale are recorded in
  [2026-07-09-nvim-external-config-conversation.md](../references/2026-07-09-nvim-external-config-conversation.md).

## Problem

Define and implement a reproducible way to deploy nvim config from
`kkiyama117/nvim_config` to `~/.config/nvim` via chezmoi, while:

1. Keeping nvim source out of the dotfiles chezmoi tree and container build
   context
2. Preserving the existing secrets-only dotfiles management for sensitive nvim
   files
3. Documenting the edit → git add → commit → push workflow (externals are not
   authored via `chezmoi add`)
4. Gating external fetch out of `BUILD_MODE=true` container builds

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
6. Secrets remain dotfiles-managed at a path that does not conflict with the
   external tree (proposed: `~/.config/nvim-secrets/secrets.vim`).
7. `make build` does not fetch or bake nvim config into image layers.
8. After `make up` and runtime `chezmoi apply`, container has nvim config at
   `~/.config/nvim` and `neovim` binary is available (already installed via
   pacman/AUR inventory).
9. Edit workflow is documented: changes are committed in the nvim external
   checkout (or `/data/nvim_config` authoring checkout), not via `chezmoi add`.

## Notes

- Submodule approach was considered and rejected (see conversation log).
- Lazy.nvim / plugin data under `~/.local/share/nvim` remains unmanaged.
- Implementation plan (`docs/plans/…-impl.md`) follows design approval.
