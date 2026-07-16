# Install `kakehashi` during the container build

**Date:** 2026-07-16
**Status:** closed (see [result-log](2026-07-16-phase-kakehashi-container-install.md))
**Related:** [design](../specifications/implementations/2026-07-16-kakehashi-container-install-design.md), [review](../reviews/2026-07-16-kakehashi-container-install-review-pass1.md), spec 02, spec 20, spec 21

## Context

[`kakehashi`](https://github.com/atusy/kakehashi) is distributed as a
single-file executable inside platform-specific GitHub release archives. As of
2026-07-16, the latest release is v0.8.0 and includes
`kakehashi-v0.8.0-x86_64-unknown-linux-gnu.tar.gz`. The archive contains only
`kakehashi`, and the executable reports its version with
`kakehashi --version`.

The shared `dot_zshenv.tmpl` already places `~/.local/bin` on `PATH`. The
container installs user-facing tools during the image build; the entrypoint is
reserved for runtime configuration and readiness.

## Problem

Provide `kakehashi` at `~/.local/bin/kakehashi` in the container without a
manual post-start install or an entrypoint network dependency. The user chose
an unpinned latest-release policy, normal container layer caching, and the
repository's current x86_64-only target.

## Acceptance criteria

1. `kakehashi` is declared as a Layer 3 `custom` tool in
   `dependencies/packages.toml`, and `make gen-deps` updates the generated
   installed-program inventory.
2. The Containerfile resolves the latest stable GitHub release when the install
   layer executes, downloads the x86_64 GNU/Linux archive, and installs its
   sole regular, non-symlink `kakehashi` member to
   `~/.local/bin/kakehashi` as the non-root container user.
3. The build fails on release-resolution, download, archive-shape, extraction,
   install, or version-check failure.
4. `kakehashi --version` succeeds after `make build` and `make up`, and
   `command -v kakehashi` resolves to `~/.local/bin/kakehashi`.
5. The entrypoint performs no `kakehashi` installation or update.
6. Specs 02, 20, and 21 and focused static tests describe and enforce the
   install path, latest-release policy, x86_64 asset, and build-time lifecycle.

## Notes

- Normal container caching is intentional: "latest" is resolved whenever the
  install layer runs. A forced refresh requires the full no-cache build command
  documented by the design; ordinary `make build` has no cache-bust behavior.
- Upstream does not publish a checksum file alongside the release archives.
  This unpinned policy therefore relies on HTTPS/GitHub release delivery plus
  strict archive-shape and executable-version validation, rather than a
  repository-pinned digest.
- No Makefile, PATH, volume, secret-management, or entrypoint behavior change
  is required.
