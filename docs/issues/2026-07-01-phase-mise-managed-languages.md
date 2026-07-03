# mise-managed languages (go/python/deno) — Phase result-log

**Date:** 2026-07-01
**Phase:** mise-managed-languages (implementation)
**Plan:** [`../plans/2026-07-01-mise-managed-languages-impl.md`](../plans/2026-07-01-mise-managed-languages-impl.md)
**Issue:** [`2026-07-01-mise-managed-languages.md`](2026-07-01-mise-managed-languages.md) → closed
**Design:** [`../specifications/implementations/2026-07-01-mise-managed-languages-design.md`](../specifications/implementations/2026-07-01-mise-managed-languages-design.md)

## Summary

Moved `mise` from a doc-only manager to a list-based manager in the dependency generator, declared `go`/`python`/`deno` in `dependencies/packages.toml` with `manager = "mise"`, added a Containerfile Layer 3-5 that installs them with `mise install` and sets global defaults via `mise use -g`, and verified that the runtime mise shims resolve the tools and that the `dotfiles_mise` named volume persists them across `make down && make up`.

## Acceptance evidence (1–8)

| # | Criterion | Verification | Result |
|---|---|---|---|
| 1 | `go`, `python`, `deno` declared in `dependencies/packages.toml` with `manager = "mise"`, `layer = 3`, `has_configs = false` | `dependencies/packages.toml` contains the three `[[tool]]` entries in the Layer 3 mise section (committed in `b2517e7`) | DONE |
| 2 | `mise` becomes a list manager; `make gen-deps` emits `dependencies/layer_3/mise.txt` | `"mise" in main.LIST_MANAGERS`; `"mise" not in main.DOC_ONLY_MANAGERS`; `(3, "mise") in main.EXPECTED_EMPTY_FILES`; `python3 -m pytest programs/generate_deps/tests/ -q` → 24 passed; `make gen-deps` regenerated `dependencies/layer_3/mise.txt` | DONE |
| 3 | Containerfile `toolchain` stage gains Layer 3-5 that runs `mise install` from `layer_3/mise.txt`; tools land in `~/.local/share/mise` | `container/Containerfile` has the Layer 3-5 block; full `make build` reached STEP 7/7 of the `toolchain` stage and logged `mise ~/.config/mise/config.toml tools: deno@2.9.0, go@1.26.4, python@3.14.6` | DONE |
| 4 | After `make up`, `podman exec dotfiles-manjaro zsh -ic 'go version; python --version; deno --version'` prints a version for each | `go version go1.26.4 linux/amd64`; `Python 3.14.6`; `deno 2.9.0 (stable, release, x86_64-unknown-linux-gnu)` | DONE |
| 5 | `make down && make up` preserves the installed languages | `go version` output captured before and after restart; `diff /tmp/mise_go_before.txt /tmp/mise_go_after.txt` produced no output | DONE |
| 6 | An empty mise list does not break the build | Containerfile Layer 3-5 has `if [ -n "$pkgs" ]; then ...; else echo "toolchain: mise install list is empty -- skipping"; fi`; `(3, "mise")` in `main.EXPECTED_EMPTY_FILES` ensures `layer_3/mise.txt` always exists | DONE |
| 7 | Generator tests green with `test_mise_manager.py`; `test_custom_manager.py` updated | `python3 -m pytest programs/generate_deps/tests/ -q` → `24 passed in 0.49s`; `test_mise_manager.py` covers list rendering, empty-file emission, and doc block; `test_custom_manager.py` docstring no longer claims `mise` is doc-only | DONE |
| 8 | Specs 02 and 21 updated | `docs/specifications/02-installed-programs.md` lists `mise` as a list manager and its manager-rule bullet describes the list-based `@latest` mechanism; `docs/specifications/21-container-build-flow.md` has the Layer 3-5 stage-table row and acceptance criterion #13 | DONE |

## No-regression (existing spec 21 acceptance)

```
paru --version              → paru v2.1.0 - libalpm v16.0.1
nvim --version (AUR)        → NVIM v0.13.0-dev-881+gc040f53dc1
rustc --version             → rustc 1.96.1
```

## Teardown

`make down` stops/removes the container; the `dotfiles_mise` named volume persists so a subsequent `make up` reuses the installed languages.

## Deviations from plan

1. **Runtime shim resolution required an additional `mise use -g` step.** The initial Phase 4 smoke failed because `mise activate zsh --shims` alone does not select a version without a config file. The Containerfile Layer 3-5 was extended to run `mise use -g ${=pkgs}` after `mise install ${=pkgs}`, which writes `~/.config/mise/config.toml` and makes the shims resolve at runtime. This fix was committed as `09c9b89` before the final full build.
