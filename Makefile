# Makefile for some tools and manage container.

HOST_UID := $(shell id -u)
HOST_GID := $(shell id -g)

JOBS ?= 1

# Bitwarden item id file consumed as a BuildKit secret by the Containerfile.
# Only passed when the file actually exists, so a placeholder value is harmless.
BW_ID := TEST
BW_SECRET :=
ifneq ($(wildcard $(BW_ID)),)
BW_SECRET := --secret id=bitwarden_id,src=$(BW_ID)
endif

# Bind mount for the container home directory
HOME_DIR := $(CURDIR)/container/bind/home_dir

# Build context (holds Containerfile + bind mount source)
BUILD_CTX := $(CURDIR)/container

.PHONY: help build build_container

help:
	@echo "Usage: make [target]"
	@echo "Targets:"
	@echo "  build           Build the image matching your host uid/gid"
	@echo "  build_container Build the container"
	@echo "  "

build: ## Build the image matching your host uid/gid
	podman build --jobs $(JOBS) \
	--build-arg HOST_UID=$(HOST_UID) \
	--build-arg HOST_GID=$(HOST_GID) \
	$(BW_SECRET) \
	$(BUILD_CTX)
