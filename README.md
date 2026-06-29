# New dotfiles

Cross-platform dotfiles managed by [chezmoi](https://chezmoi.io), targeting
Arch Linux / Manjaro Linux. 
You can either install onto an existing host, or use the self-contained Podman container.

## Quickstart

Read [`here`](docs/specifications/12-quickstart.md) to get started with the quickstart guide. 
[pre requirements](docs/specifications/11-pre-required-env-values.md) may help you get started. And full list of managed programs is [here](docs/specifications/02-installed_programs.md).

### Notes for AI agents

- Everything and every rules of this repository is defined in [`specifications/`](docs/specifications/) (and this README.md). Whenever you make a change, please read or update the specs accordingly. especially, YOU MUST FOLLOW [document management rule](docs/specifications/00-documents.md).

## Program files

Mainly target of this repository is `Arch Linux` or `Manjaro Linux`.
This repository uses `chezmoi` for managing dotfiles and `sheldon` for
managing shell plugins (and zsh config files).
and `mise` for managing language toolchain versions.
`nix` is only used for subdir that uses `flake.nix` (so don't use it here).

Full list of managed programs is [here](docs/specifications/02-installed_programs.md).
