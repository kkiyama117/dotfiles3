# Migrate `herdr` install authority to mise

**Date:** 2026-07-15
**Status:** closed (see [result-log](2026-07-15-phase-herdr-mise-management.md))
**Related:** [design](../specifications/implementations/2026-07-15-herdr-mise-management-design.md), [plan](../plans/2026-07-15-herdr-mise-management-impl.md), [design review](../reviews/2026-07-15-herdr-mise-management-review-pass1.md), [implementation review](../reviews/2026-07-15-herdr-mise-management-review-pass2.md), superseded approach [herdr-container-install](2026-07-15-herdr-container-install.md), [herdr-container-install design](../specifications/implementations/2026-07-15-herdr-container-install-design.md), spec 02, spec 20, spec 21

## Context

On 2026-07-15 the repository closed
[`2026-07-15-herdr-container-install.md`](2026-07-15-herdr-container-install.md)
after installing `herdr` v0.7.3 as a bespoke Containerfile Layer 3-8 curl
bootstrap into `~/.local/bin/herdr`, with a `manager = "custom"` doc-only
entry in `dependencies/packages.toml`. That path works but duplicates install
authority: the container already installs mise-managed tools from the
chezmoi-rendered [`dot_config/mise/config.toml`](../../dot_config/mise/config.toml)
at Containerfile Layer 3-4, and upstream documents mise as a supported install
path for `herdr`.

The mise config already sets `disable_default_registry = true`, so any new
aqua-backed tool must be declared with an explicit `aqua:` prefix. The host
and container share the same mise config source; `dotfiles_mise` persists
`MISE_DATA_DIR` across `make down && make up`.

## Problem

Consolidate `herdr` into the existing mise install pipeline so that mise is
the **sole** install, version, and upgrade authority on host and container.
Remove the parallel bespoke binary install (Containerfile Layer 3-8 and
`packages.toml` `custom` entry) and stop `herdr`'s built-in update checks
from competing with mise upgrades.

## Acceptance criteria

1. [`dot_config/mise/config.toml`](../../dot_config/mise/config.toml) declares
   `"aqua:ogulcancelik/herdr" = "latest"` under `[tools]` (required because
   `disable_default_registry = true`).
2. `dependencies/packages.toml` no longer contains a `herdr` entry; `make
   gen-deps` removes `herdr` from the spec 02 AUTO-GEN block.
3. Containerfile Layer 3-8 (`ARG HERDR_*`, curl bootstrap to
   `~/.local/bin/herdr`) is removed; `herdr` is installed only via Layer 3-4
   `mise install --yes` reading the rendered mise config.
4. [`dot_config/herdr/config.toml`](../../dot_config/herdr/config.toml) and
   [`dot_config/herdr/config.yml`](../../dot_config/herdr/config.yml) set
   `[update] channel = "stable"`, `version_check = false`, and
   `manifest_check = false`; upgrades use `mise upgrade aqua:ogulcancelik/herdr`.
5. After rollout (`make build` and, for existing deployments, one-time
   `podman volume rm dotfiles_mise` before `make up`), `podman exec <c> zsh
   -ic 'herdr --version'` exits 0; `which herdr` resolves to a mise shim
   under `$MISE_DATA_DIR/shims`, not `~/.local/bin/herdr`.
6. Specs 02, 20, and 21 are updated: I-HERDR1..I-HERDR3 and Layer 3-8
   references are replaced with mise-based invariants and acceptance criteria;
   spec 21 documents the one-time `dotfiles_mise` volume migration.
7. Historical docs from the closed container-install work
   ([issue](2026-07-15-herdr-container-install.md),
   [result-log](2026-07-15-phase-herdr-container-install.md),
   [old design](../specifications/implementations/2026-07-15-herdr-container-install-design.md),
   [old plan](../plans/2026-07-15-herdr-container-install-impl.md)) remain
   byte-identical as history, except that the old design is marked
   `superseded` and the old plan is marked `executed` with a forward link to
   the replacement design during implementation.

## Notes

- Approved direction: mise `latest` policy at install time; ongoing upgrades
  via `mise upgrade aqua:ogulcancelik/herdr`, not `herdr update` or image
  rebuild SHA bumps.
- Existing `dotfiles_mise` volumes created before this change will not pick up
  the aqua install on `make up` alone; operators must remove the volume once
  (see design §6 rollout).
- Replacement design:
  [`2026-07-15-herdr-mise-management-design.md`](../specifications/implementations/2026-07-15-herdr-mise-management-design.md).
  Required review letters: A + C + E ([`09-review.md`](../specifications/09-review.md) §2.2).
