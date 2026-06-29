# Spec 21 (container-build-flow) is out of sync with the Containerfile

**Date:** 2026-06-29
**Status:** open
**Related:** [spec 21](../specifications/21-container-build-flow.md), [spec 22](../specifications/22-container-build-pre-required-envs.md), [`../../container/Containerfile`](../../container/Containerfile)

## Context

`docs/specifications/21-container-build-flow.md` is still a **DRAFT (stub)** and
its "Stage (Layer) ordering" table no longer describes the real
`container/Containerfile`:

- The table says the `base` stage installs `base-devel, sudo, curl, git` from
  `dependencies/layer_1.txt`. The real `base` stage only runs
  `pacman -Sy --noconfirm --needed zsh` (Layer 1-2). No `layer_1.txt` is
  consumed yet.
- The table says the `builder` remap lives in the `no-config-base` stage. The
  real remap (Layer 1-3 + Layer 1-4) lives in the **`base`** stage, before the
  `USER ${USERNAME}` directive. `no-config-base` is currently an empty
  `FROM base AS no-config-base` with a TODO for `chezmoi apply`.
- The sub-layer numbering (1-1 … 1-4) and the UID-collision fallback +
  NOPASSWD sudoers step (Layer 1-4) are not documented at all.

`docs/specifications/22-container-build-pre-required-envs.md` references "the
`no-config-base` stage in 21" for the builder remap, which is now wrong — the
remap is in `base`.

## Problem

The normative spec for the build flow disagrees with the implementation it is
supposed to describe. A reader following spec 21 will mis-locate the user
remap and expect a `layer_1.txt` consumption that does not exist yet.

## Acceptance criteria

1. spec 21's stage table matches the actual `FROM ... AS` stages and their
   sub-layers in `container/Containerfile` as of 2026-06-29.
2. spec 21 records the in-scope inputs (`HOST_UID`, `HOST_GID`, `USERNAME`)
   and which stage/sub-layer consumes them.
3. spec 22's cross-reference to the remap stage points at `base`, not
   `no-config-base`.
4. Forward-looking items (planned `chezmoi-apply` content of `no-config-base`,
   planned `tooling` stage, `layer_<N>.txt` / `packages.toml` wiring) remain
   but are clearly marked as planned, not as current behavior.
5. No behavior change to the Containerfile itself in this revision — this is a
   doc-only sync.

## Notes

- This is a doc-only correction of an existing stub, so it skips the full
  design → review → plan lifecycle (doc-mgmt §4). The issue is filed for
  traceability per doc-mgmt §10 and AGENTS.md §1.
- I7 in spec 20 ("`builder` remapped to `${USERNAME}` is the only non-root
  account; `USER` is set before any installation step that does not require
  root") is now actually realized by Layer 1-3's `USER ${USERNAME}`. No
  invariant change needed, just alignment.