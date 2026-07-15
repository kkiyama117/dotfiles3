# Result log: Migrate `herdr` install authority to mise

**Date:** 2026-07-15
**Issue:** [`2026-07-15-herdr-mise-management.md`](2026-07-15-herdr-mise-management.md)
**Plan:** [`docs/plans/2026-07-15-herdr-mise-management-impl.md`](../plans/2026-07-15-herdr-mise-management-impl.md)
**Design:** [`docs/specifications/implementations/2026-07-15-herdr-mise-management-design.md`](../specifications/implementations/2026-07-15-herdr-mise-management-design.md)
**Design review:** [`docs/reviews/2026-07-15-herdr-mise-management-review-pass1.md`](../reviews/2026-07-15-herdr-mise-management-review-pass1.md)
**Implementation review:** [`docs/reviews/2026-07-15-herdr-mise-management-review-pass2.md`](../reviews/2026-07-15-herdr-mise-management-review-pass2.md)

## Commit trail

**No commits were created in this implementation session.** The parent session
was not authorized to commit. All Phases 0–5 changes remain in the working
tree on `develop` (modified implementation files and untracked docs/tests). A
future authorized session must stage and commit before merge.

## Acceptance evidence

| Criterion | Status | Evidence |
|---|---|---|
| S1: `"aqua:ogulcancelik/herdr" = "latest"` in mise config | ✅ PASS | `dot_config/mise/config.toml` `[tools]`; policy test `test_herdr_in_mise_config` |
| S2: `herdr` removed from `packages.toml`; spec 02 AUTO-GEN updated | ✅ PASS | No `name = "herdr"` in `dependencies/packages.toml`; `make gen-deps` idempotent (`txt_written=0 doc_updated=False` ×2); policy test `test_herdr_not_in_packages_toml` |
| S3: Containerfile Layer 3-8 deleted; herdr via Layer 3-4 mise only | ✅ PASS | No `HERDR_VERSION` / `HERDR_SHA256` / `herdr-linux-x86_64` / Layer 3-8 comment; policy test `test_containerfile_has_no_bespoke_herdr_install`; build log 0 Layer 3-8 matches |
| S4: Both herdr configs: stable channel + checks disabled | ✅ PASS | `dot_config/herdr/config.toml` and `config.yml`: `channel = "stable"`, `version_check = false`, `manifest_check = false`; policy test `test_herdr_update_checks_disabled`; runtime grep in Step 5.6 |
| S5: `make build` succeeds; herdr via mise shim; old path absent | ✅ PASS | `BUILD_EXIT=0`; image `949c1d9159ea` tagged `localhost/dotfiles-manjaro:latest`; `herdr 0.7.3`; `which herdr` → `~/.local/share/mise/shims/herdr` (normalized from observed runtime output); `mise ls aqua:ogulcancelik/herdr` → `0.7.3`; `OLD_PATH_GONE` (`~/.local/bin/herdr` absent) |
| S6: Persistence across `make down && make up` | ✅ PASS | After restart: `herdr 0.7.3`; shim path unchanged; `dotfiles_mise` volume timestamps stable |
| S7: Specs 02, 20, 21 updated for mise-based herdr | ✅ PASS | Spec 02 prose + AUTO-GEN; spec 20 I-HERDR1..I-HERDR3 rewritten; spec 21 Layer 3-8 row removed, acceptance #25 replaced with mise-shim checks + volume migration note |
| S8: Old container-install docs preserved; design superseded; plan executed | ✅ PASS | `git diff -- docs/issues/2026-07-15-herdr-container-install.md docs/issues/2026-07-15-phase-herdr-container-install.md` → no diff; old design `superseded`; old plan `executed` with forward link and corrected Task 2 snippet |
| Phase 5.1: Build exit 0 + image markers | ✅ PASS | `[5/5] COMMIT localhost/dotfiles-manjaro:latest`; `Successfully tagged localhost/dotfiles-manjaro:latest`; `949c1d9159ea…`; wall ~356 s (~6 min, cache-assisted) |
| Phase 5.1: No bespoke Layer 3-8 in build log | ✅ PASS | `grep -c 'Layer 3-8\|HERDR_\|bespoke' /tmp/phase5-build.log` → 0 |
| Phase 5.1: mise/aqua herdr install | ✅ PASS | Layer 3-4 `mise install --yes`; cache step recorded `mise aqua:ogulcancelik/herdr@0.7.3 [1/2] install` |
| Phase 5.2: One-time `dotfiles_mise` volume removal | ✅ PASS | `make down`; `podman volume rm dotfiles_mise` → exit 0 |
| Phase 5.3: `make up` ready | ✅ PASS | `make: container ready (chezmoi apply finished)`; `UP_EXIT=0` (~41 s) |
| Phase 5.8: go / node / pi regressions | ✅ PASS | `go version go1.26.5 linux/amd64`; `v26.5.0`; `0.80.6` |
| Volume isolation: only `dotfiles_mise` recreated | ✅ PASS | Pre-removal timestamps unchanged for `dotfiles_ssh`, `dotfiles_cargo`, `dotfiles_rustup`, `dotfiles_gnupg`; `dotfiles_mise` recreated at `2026-07-15T21:21:16+09:00` |
| Policy tests (4/4) | ✅ PASS | `pytest programs/generate_deps/tests/test_herdr_mise_migration.py` → 4 passed |
| Generator tests (35/35) | ✅ PASS | `pytest programs/generate_deps/tests/` → 35 passed |

## Phase 5 runtime evidence (summary)

Build window: `2026-07-15T21:14:55+09:00` → `2026-07-15T21:20:51+09:00`.

```
podman exec dotfiles-manjaro zsh -ic 'herdr --version'
# herdr 0.7.3

podman exec dotfiles-manjaro zsh -ic 'which herdr'
# ~/.local/share/mise/shims/herdr  (observed: $MISE_DATA_DIR/shims/herdr)

podman exec dotfiles-manjaro zsh -ic 'test ! -x $HOME/.local/bin/herdr && echo OLD_PATH_GONE'
# OLD_PATH_GONE

podman exec dotfiles-manjaro zsh -ic 'go version; node --version; pi --version'
# go version go1.26.5 linux/amd64
# v26.5.0
# 0.80.6
```

Command transcripts for Phase 5 runtime checks are captured in the summary block above.

## Residual risks

- **E1 (cold-build duration):** This verification retry completed in ~6 min with
  build-cache hits on Layer 3-4. A cold build without cache may still take
  20+ minutes (dominated by AUR packages in Layer 4, as in prior container
  work). Operators should plan accordingly.
- **E2 (aqua backend recurrence):** `herdr` uses the aqua backend. The
  2026-07-09 `pnpm` attestation failure mode did not recur in this build
  (`herdr 0.7.3` installed and runs). If aqua attestation failures return, they
  become an implementation blocker per design §8 Q1.

## Implementation notes

- One-time `podman volume rm dotfiles_mise` was required for this existing
  deployment; new deployments skip that step.
- `make clean` was not used during verification (per plan constraint).
- Historical container-install issue and result-log bodies remain byte-identical.
