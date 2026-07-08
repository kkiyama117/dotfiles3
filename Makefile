# Makefile for some tools and manage container.
# For details, see about [Makefile](docs/specifications/08-automations.md) for automation,
# and [rules to manage Container](docs/specifications/20-container-rules.md).
# Pre _requirements should be [here](docs/specifications/22-container-build-pre-requirements.md).

HOST_UID := $(shell id -u)
HOST_GID := $(shell id -g)

JOBS ?= 1

# Seconds `make up` waits for the entrypoint's `chezmoi apply` to finish
# before returning. Covers Bitwarden auth + apply against the host bind.
# `make up` aborts (non-zero, with `podman logs`) if the entrypoint exits
# early or this timeout elapses without the readiness sentinel appearing.
# See spec 20 I-RUN2 and docs/issues/2026-07-06-make-up-races-chezmoi-apply.md.
UP_WAIT_TIMEOUT ?= 120

# Container username: read from .env (gitignored, machine-specific).
# The build / up targets fail if .env does not define USERNAME.
-include .env

# Named volumes (Podman copy-on-first-mount: build-time binaries under
# $CARGO_HOME / $RUSTUP_HOME / $MISE_DATA_DIR survive into the volume on the
# first `make up`; a host bind would hide them). dotfiles_gnupg / dotfiles_ssh
# persist runtime keyrings (no build-time binaries, but kept here as the
# single named-volume registry).
CARGO_VOLUME  := dotfiles_cargo
RUSTUP_VOLUME := dotfiles_rustup
MISE_VOLUME   := dotfiles_mise
GNUPG_VOLUME  := dotfiles_gnupg
SSH_VOLUME    := dotfiles_ssh

# Bitwarden credentials as podman secrets. Each is mounted only if it
# exists, so `make up` still starts when no secrets have been created
# (entrypoint skips auth when /run/secrets/bw_password is absent). The
# master password is read by `bw unlock --passwordfile` inside the
# container and never placed in an environment variable.
BW_SECRETS := $(foreach s,bw_clientid bw_clientsecret bw_password,$(shell podman secret exists $(s) 2>/dev/null && printf -- '--secret %s ' $(s)))

# Build context (holds Containerfile + bind mount source)
BUILD_CTX := $(CURDIR)/container

# Image and container names. Image tag matches LABEL org.opencontainers.image.title
IMAGE     := localhost/dotfiles-manjaro:latest
CONTAINER := dotfiles-manjaro

.PHONY: help build up exec down clean _require_username _verify_image_fresh gen-deps test-deps test-zsh

help:
	@echo "Usage: make [target]"
	@echo "Targets:"
	@echo "  build           Build the image matching your host uid/gid"
	@echo "  up              Start a detached container with chezmoi bind + named volumes (cargo, rustup, mise, gnupg, ssh) (--userns=keep-id, --replace)"
	@echo "  exec            Open an interactive shell in the running container"
	@echo "  down            Stop and remove the container"
	@echo "  clean           Stop container, remove image, and delete named volumes (cargo, rustup, mise, gnupg, ssh)"
	@echo "  test-zsh        Run zsh dotfile regression tests"

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

# Verify the image's /usr/local/bin/entrypoint.sh matches the source at
# container/bind/layer_5_files/entrypoint.sh, so `make up` cannot silently
# run a stale image (e.g. one built before an entrypoint edit — which would
# make the readiness-sentinel wait loop time out at UP_WAIT_TIMEOUT because
# the old entrypoint never writes /tmp/chezmoi-applied). Byte-hash based;
# catches ANY entrypoint drift, not just the sentinel. Cheap: a throwaway
# `podman run --rm --entrypoint` container that just hashes the file and
# exits — no volumes, no entrypoint script, no --userns. See
# docs/issues/2026-07-06-make-up-races-chezmoi-apply.md and spec 20 I-RUN3.
_verify_image_fresh:
	@src_hash=$$(sha256sum $(BUILD_CTX)/bind/layer_5_files/entrypoint.sh | cut -d' ' -f1); \
	img_hash=$$(podman run --rm --entrypoint /usr/bin/sha256sum $(IMAGE) /usr/local/bin/entrypoint.sh 2>/dev/null | cut -d' ' -f1); \
	if [ -z "$$img_hash" ]; then \
		echo "make: *** image $(IMAGE) not found or unreadable — run \`make build\` first." >&2; \
		exit 1; \
	fi; \
	if [ "$$src_hash" != "$$img_hash" ]; then \
		echo "make: *** image $(IMAGE) has a stale entrypoint (source $$src_hash != image $$img_hash)." >&2; \
		echo "make: *** run \`make build\` then re-run \`make up\`." >&2; \
		exit 1; \
	fi

up: _require_username _verify_image_fresh ## Start a detached container with init, chezmoi bind, and named volumes (cargo, rustup, mise, gnupg, ssh)
	podman run -d --replace --name $(CONTAINER) \
		--init \
		--userns=keep-id \
		$(BW_SECRETS) \
		-v $(CURDIR):/home/$(USERNAME)/.local/share/chezmoi \
		-v $(CARGO_VOLUME):/home/$(USERNAME)/.local/share/cargo \
		-v $(RUSTUP_VOLUME):/home/$(USERNAME)/.local/share/rustup \
		-v $(MISE_VOLUME):/home/$(USERNAME)/.local/share/mise \
		-v $(GNUPG_VOLUME):/home/$(USERNAME)/.local/share/gnupg \
		-v $(SSH_VOLUME):/home/$(USERNAME)/.ssh \
		$(IMAGE) sleep infinity
	@echo "make: waiting for entrypoint's chezmoi apply to finish (timeout $(UP_WAIT_TIMEOUT)s)..."
	@i=0; \
	while [ $$i -lt $(UP_WAIT_TIMEOUT) ]; do \
		if podman exec $(CONTAINER) test -f /tmp/chezmoi-applied 2>/dev/null; then \
			echo "make: container ready (chezmoi apply finished)."; \
			exit 0; \
		fi; \
		if [ "$$(podman inspect -f '{{.State.Running}}' $(CONTAINER) 2>/dev/null)" != "true" ]; then \
			echo "make: *** container exited before chezmoi apply finished" >&2; \
			podman logs $(CONTAINER) >&2 || true; \
			exit 1; \
		fi; \
		sleep 1; \
		i=$$((i+1)); \
	done; \
	echo "make: *** timed out after $(UP_WAIT_TIMEOUT)s waiting for chezmoi apply" >&2; \
	podman logs $(CONTAINER) >&2 || true; \
	exit 1

exec: ## Open an interactive shell in the running container
	podman exec -it $(CONTAINER) zsh

down: ## Stop and remove the container
	-podman stop $(CONTAINER)
	-podman rm $(CONTAINER)

clean: down ## Full reset: stop container, remove image, and delete named volumes (cargo, rustup, mise, gnupg, ssh)
	-podman volume rm $(CARGO_VOLUME) $(RUSTUP_VOLUME) $(MISE_VOLUME) $(GNUPG_VOLUME) $(SSH_VOLUME)
	-podman rmi $(IMAGE)

# META PROGRAMS
test-deps: ## Run the generate_deps pytest suite
	python3 -m pytest programs/generate_deps/tests/ -q

test-zsh: ## Run zsh dotfile regression tests
	zsh tests/zsh/zoxide_zi_test.zsh

gen-deps: ## Regenerate dependencies/layer_<N>/<manager>.txt + 02 AUTO-GEN block from packages.toml
	python3 programs/generate_deps/main.py
