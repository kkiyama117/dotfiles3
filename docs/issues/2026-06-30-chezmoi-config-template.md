# Manage runtime chezmoi.toml via dotfiles (.chezmoi.toml.tmpl)

**Date:** 2026-06-30
**Status:** open
**Related:** [design](../specifications/implementations/2026-06-30-chezmoi-config-template-design.md), [plan](../plans/2026-06-30-chezmoi-config-template-impl.md)

## Context

- The runtime `~/.config/chezmoi/chezmoi.toml` (`build_mode = false`) is
  currently hardcoded as an inline heredoc (`cat > ... <<'TOML'`) in
  `container/bind/layer_5_files/entrypoint.sh`.
- The build-prepass `~/.config/chezmoi/chezmoi.toml` (`build_mode = true`)
  is a static file `container/bind/layer_2_files/chezmoi.toml` `COPY`'d
  into Containerfile Stage 2.
- The chezmoi source root is the repo root (`dot_config/`,
  `dot_zshenv.tmpl`, `.chezmoiignore`). No `.chezmoi.toml.tmpl` exists yet.
- chezmoi supports a config template `.chezmoi.$FORMAT.tmpl` in the source
  root, rendered by `chezmoi init` / `chezmoi execute-template --init` to
  `~/.config/chezmoi/chezmoi.toml`. This template is executed **prior to
  reading the source state**, so it can use `env` / `promptString` but not
  `.chezmoidata` / source-state `[data]` (it is generating the config).

## Problem

The `chezmoi.toml` content (notably `build_mode`) is split across two
non-dotfiles locations: an entrypoint heredoc (runtime) and a
`bind/layer_2_files/` static file (build). The runtime config should be
managed in dotfiles (the chezmoi source), not hardcoded in `entrypoint.sh`.

## Acceptance criteria

1. `chezmoi.toml` content is defined by a single `.chezmoi.toml.tmpl` at
   the chezmoi source root (repo root); `entrypoint.sh` no longer
   hardcodes the config via a heredoc.
2. `build_mode` is driven by the `BUILD_MODE` env var: build-prepass
   renders `build_mode = true`, runtime renders `build_mode = false`
   (unset → false).
3. Both phases render the config with `chezmoi execute-template --init`
   (no `chezmoi init` git/clone side effects).
4. `container/bind/layer_2_files/chezmoi.toml` (and the now-empty
   `layer_2_files/` dir) are removed; the Stage 2 `COPY` is removed.
5. `BUILD_MODE` is set inline in the build-prepass `RUN` (not `ENV`) →
   does NOT appear in `podman inspect` or image `Env`.
6. Layer 5-3 still strips the carried-forward
   `~/.config/chezmoi/chezmoi.toml` so the entrypoint renders it fresh.
7. `make build` green; `.chezmoi.toml.tmpl` is ignored by `chezmoi apply`
   (it is a chezmoi special file, not a source entry).
8. `make up` (with and without `bw_*` secrets): container `Up`,
   `chezmoi apply` OK, runtime `chezmoi.toml = build_mode = false`
   (USERNAME-owned), secrecy invariants unchanged, toolchain named-volumes
   persist.
9. The build-prepass rendered config is `build_mode = true` (verified in
   the Stage 2 scratch).
10. Host is not broken: a host `chezmoi init` renders `build_mode = false`
    (the host runtime value); a host `chezmoi apply` with an existing
    config is unaffected.
11. Specs 01 / 13 / 20 / 21 and the entrypoint / Containerfile comments are
    updated to the new mechanism.

## Notes

- `.chezmoi.toml.tmpl` is a chezmoi **special file** (config template),
  not a regular source entry → `chezmoi apply` ignores it. Only
  `chezmoi init` / `chezmoi execute-template --init` render it.
- `execute-template --init` is chosen over `chezmoi init` for both phases
  to avoid `chezmoi init`'s git-init side effect on the build-prepass
  scratch (`/tmp/chezmoi-src` has no `.git`, excluded by `.dockerignore`).
- This builds on the container-bake work (PR #4) that made the entrypoint
  create `chezmoi.toml` fresh and strip the carried-forward copy in
  Layer 5-3.