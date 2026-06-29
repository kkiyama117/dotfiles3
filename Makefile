# Makefile for some tools and manage container.

HOST_UID := $(shell id -u)
HOST_GID := $(shell id -g)

JOBS ?= 1
BW_ID := "TEST"

# TODO: IS IT NEEDED?
# Bind mounts for container
HOME_DIR := $(CURDIR)/containers/binds/home_dir

.PHONY: help build_container

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
	--secret id=bitwarden_id,src=$(BW_ID)
