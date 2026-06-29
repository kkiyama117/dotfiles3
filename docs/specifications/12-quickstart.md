# Quickstart

TODO: write this file with correct format.

### Local

- Install [chezmoi](https://chezmoi.io) and the tools listed in
  [`docs/specifications/installed_programs.md`](docs/specifications/installed_programs.md),

```sh
# Run from inside this cloned repo:
# FOR AI agents: Don't do this until the repo is growing up and ready to use. 
chezmoi init --apply --source="$PWD"
# And if you make `<your_github_account>/dotfiles`, run it downloads your dotfiles automatically 
chezmoi init --apply
```

For more information, see the ... (TODO)

### Container

Use the container to try the setup without polluting the host. It builds
a Manjaro image with every tool listed in
[`docs/specifications/installed_programs.md`](docs/specifications/installed_programs.md)
pre-installed and applies the dotfiles to a persistent home bind on first
boot. Full instructions (rbw secret wiring, bind mounts, chezmoi behavior,
make targets) live in [`containers/README.md`](containers/README.md).

Quick start:

```sh
cd containers

# build the image (host uid/gid auto-detected; rootless Podman required)
make build

# start a detached container. RBW_CONFIG / RBW_SECRET default to
# $XDG_STATE_HOME/dotfiles2/{rbw_config.json,rbw_password} — `make up` alone
# picks them up if present (mode 0600). Override or set to empty to skip.
#   install -d -m 0700 "${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles2"
#   # place rbw_config.json + rbw_password there with 0600
make up

# drop into zsh
make exec

# stop & remove the container (also wipes the per-uid Podman secrets)
make down
```

See [`container documents`](20-container-rules.md) for the full Make target
list, rbw setup, and Containerfile tier breakdown.
