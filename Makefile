# Makefile for some tools and manage container.
# For details, see about [Makefile](docs/specifications/08-automations.md) for automation,
# and [rules to manage Container](docs/specifications/20-container-rules.md).
# Pre _requirements should be [here](docs/specifications/22-container-build-pre-requirements.md).

HOST_UID := $(shell id -u)
HOST_GID := $(shell id -g)

JOBS ?= 1

# Container username: read from .env (gitignored, machine-specific).
# The build / up targets fail if .env does not define USERNAME.
-include .env

# Named volumes for toolchain dirs (Podman copy-on-first-mount: build-time
# binaries under $CARGO_HOME / $RUSTUP_HOME / $MISE_DATA_DIR survive into
# the volume on the first `make up`; a host bind would hide them).
CARGO_VOLUME  := dotfiles_cargo
RUSTUP_VOLUME := dotfiles_rustup
MISE_VOLUME   := dotfiles_mise

# Build context (holds Containerfile + bind mount source)
BUILD_CTX := $(CURDIR)/container

# Image and container names. Image tag matches LABEL org.opencontainers.image.title
IMAGE     := localhost/dotfiles-manjaro:latest
CONTAINER := dotfiles-manjaro

.PHONY: help build build_container up exec down clean _require_username gen-deps

help:
	@echo "Usage: make [target]"
	@echo "Targets:"
	@echo "  build           Build the image matching your host uid/gid"
	@echo "  build_container Build the container (alias of build)"
	@echo "  up              Start a detached container with the home bind mount (--userns=keep-id, --replace)"
	@echo "  exec            Open an interactive shell in the running container"
	@echo "  down            Stop and remove the container"
	@echo "  clean           Stop container, remove image, and delete toolchain volumes"

_require_username:
	@if [ -z "$(USERNAME)" ]; then \
		echo "make: *** USERNAME is not set. Define it in .env (e.g. USERNAME=kiyama)" >&2; \
		exit 1; \
	fi

# CONTAINER MANAGEMENT
build: _require_username ## Build the image matching your host uid/gid
	podman build --jobs $(JOBS) \
	--build-arg HOST_UID=$(HOST_UID) \
	--build-arg HOST_GID=$(HOST_GID) \
	--build-arg USERNAME=$(USERNAME) \
	--build-context deps=$(CURDIR)/dependencies \
	--build-context srcroot=$(CURDIR) \
	-t $(IMAGE) \
	$(BUILD_CTX)

up: _require_username ## Start a detached container with chezmoi bind + toolchain volumes
	podman run -d --replace --name $(CONTAINER) \
		--userns=keep-id \
		-e BW_SESSION=$$BW_SESSION \
		-v $(CURDIR):/home/$(USERNAME)/.local/share/chezmoi \
		-v $(CARGO_VOLUME):/home/$(USERNAME)/.local/share/cargo \
		-v $(RUSTUP_VOLUME):/home/$(USERNAME)/.local/share/rustup \
		-v $(MISE_VOLUME):/home/$(USERNAME)/.local/share/mise \
		$(IMAGE) sleep infinity

exec: ## Open an interactive shell in the running container
	podman exec -it $(CONTAINER) zsh

down: ## Stop and remove the container
	-podman stop $(CONTAINER)
	-podman rm $(CONTAINER)

clean: down ## Full reset: stop container, remove image, and delete toolchain volumes
	-podman volume rm $(CARGO_VOLUME) $(RUSTUP_VOLUME) $(MISE_VOLUME)
	-podman rmi $(IMAGE)

# META PROGRAMS
gen-deps: ## Regenerate dependencies/layer_<N>/<manager>.txt + 02 AUTO-GEN block from packages.toml
	python3 programs/generate_deps/main.py
