# SSH-first external repository fallback — Phase completion result log

**Date:** 2026-07-16
**Status:** closed
**Parent issue:** [Use SSH first for managed external repositories](../issues/2026-07-16-ssh-first-external-fallback.md)
**Plan:** [SSH-first external repository fallback — Implementation Plan](../plans/2026-07-16-ssh-first-external-fallback-impl.md)
**Design:** [SSH-first external repository fallback design](../specifications/implementations/2026-07-16-ssh-first-external-fallback-design.md)
**Reviews:** [Aggregate pass 1](../reviews/2026-07-16-ssh-first-external-fallback-review-pass1.md)

## What changed

- `container/bind/layer_5_files/entrypoint.sh` now selects `~/.pi` and `~/.config/nvim` transports independently with an SSH-first probe and HTTPS fallback, preserves non-empty URL overrides, validates HTTP(S) userinfo, bounds probe execution with `timeout`, forwards signals, and rewrites existing checkout `origin` remotes before `chezmoi apply` so the same startup's external pull uses the selected transport.
- `Makefile` forwards `PI_CONFIG_URL`, `PI_CONFIG_REF`, `NVIM_CONFIG_URL`, and `NVIM_CONFIG_REF` via `--env`.
- `.chezmoiexternal.toml.tmpl` quotes URL/ref values at the final TOML sink.
- `container/tests/container/test_entrypoint.py` covers SSH success/fallback, independent selection, override behavior, URL validation, timeout options, signal forwarding, forced-kill fallback, remote migration, migration-before-apply ordering, render boundary, Makefile forwarding, and TOML quoting.
- `docs/specifications/11-pre-required-env-values.md` and `docs/specifications/21-container-build-flow.md` were synchronized to describe SSH-first behavior, direct `~/.pi` / `~/.config/nvim` cloning, bounded probes, override handling, and existing-remote enforcement.

## Verification commands

```bash
python3 -m pytest container/tests/container/ -q
```

Output:

```text
........................................                                 [100%]
40 passed in 12.62s
```

Exit code: `0`
Test count: 40 passed, 0 failed.

```bash
zsh -n container/bind/layer_5_files/entrypoint.sh
```

Exit code: `0` (no output).

```bash
git diff --check
```

Exit code: `0` (no output).

## Lifecycle

- Implementation plan: `executed`
- Parent issue: `closed`
