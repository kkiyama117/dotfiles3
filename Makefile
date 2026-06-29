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

# Bitwarden item id file consumed as a BuildKit secret by the Containerfile.
# Only passed when the file actually exists, so a placeholder value is harmless.
# TODO: IMPLEMENT
BW_ID := TEST
BW_SECRET :=
ifneq ($(wildcard $(BW_ID)),)
BW_SECRET := --secret id=bitwarden_id,src=$(BW_ID)
endif

# Bind mount for the container home directory
HOME_DIR := $(CURDIR)/container/bind/home_dir

# Build context (holds Containerfile + bind mount source)
BUILD_CTX := $(CURDIR)/container

# Image and container names. Image tag matches LABEL org.opencontainers.image.title
IMAGE     := localhost/dotfiles-manjaro:latest
CONTAINER := dotfiles-manjaro

.PHONY: help build build_container up exec down _require_username

help:
	@echo "Usage: make [target]"
	@echo "Targets:"
	@echo "  build           Build the image matching your host uid/gid"
	@echo "  build_container Build the container (alias of build)"
	@echo "  up              Start a detached container with the home bind mount (--userns=keep-id, --replace)"
	@echo "  exec            Open an interactive shell in the running container"
	@echo "  down            Stop and remove the container"

_require_username:
	@if [ -z "$(USERNAME)" ]; then \
		echo "make: *** USERNAME is not set. Define it in .env (e.g. USERNAME=kiyama)" >&2; \
		exit 1; \
	fi

build: _require_username ## Build the image matching your host uid/gid
	podman build --jobs $(JOBS) \
	--build-arg HOST_UID=$(HOST_UID) \
	--build-arg HOST_GID=$(HOST_GID) \
	--build-arg USERNAME=$(USERNAME) \
	$(BW_SECRET) \
	-t $(IMAGE) \
	$(BUILD_CTX)

up: _require_username ## Start a detached container with the home bind mount
	@mkdir -p $(HOME_DIR)
	podman run -d --replace --name $(CONTAINER) \
		--userns=keep-id \
		-v $(HOME_DIR):/home/$(USERNAME) \
		$(IMAGE) sleep infinity

exec: ## Open an interactive shell in the running container
	podman exec -it $(CONTAINER) zsh

down: ## Stop and remove the container
	-podman stop $(CONTAINER)
	-podman rm $(CONTAINER)
