# herdr-mise-management — Review prompt pass-1

**Date:** 2026-07-15
**Subject:** [`docs/specifications/implementations/2026-07-15-herdr-mise-management-design.md`](../specifications/implementations/2026-07-15-herdr-mise-management-design.md)
**Issue:** [`docs/issues/2026-07-15-herdr-mise-management.md`](../issues/2026-07-15-herdr-mise-management.md)
**Required letters:** A + C + E (changes Containerfile / Makefile / build flow; see [`../specifications/09-review.md`](../specifications/09-review.md) §2.2)
**Output format:** [`../specifications/09-review.md`](../specifications/09-review.md) §3

## Scope

Review the replacement design that migrates `herdr` from a bespoke Containerfile Layer 3-8 curl bootstrap to mise management via the explicit aqua backend.

## Reviewer A — factual / correctness

Reads:
- target design (full)
- [`docs/issues/2026-07-15-herdr-mise-management.md`](../issues/2026-07-15-herdr-mise-management.md)
- [`dot_config/mise/config.toml`](../dot_config/mise/config.toml)
- [`container/Containerfile`](../container/Containerfile) (Layer 3-4, Layer 3-8)
- [`Makefile`](../Makefile) (volume/build/up targets)
- [`dot_zshenv.tmpl`](../dot_zshenv.tmpl) (mise activation, MISE_DATA_DIR, PATH ordering)
- [`docs/issues/2026-07-15-phase-herdr-container-install.md`](../issues/2026-07-15-phase-herdr-container-install.md) (prior result-log)

Evaluation points:
- Are all load-bearing factual claims (Layer 3-4 behavior, Layer 3-8 contents, `disable_default_registry = true`, shim PATH precedence, named-volume first-mount semantics) supported by the cited files?
- Is the aqua-prefix precedent claim accurate? (Only `"npm:@earendil-works/pi-coding-agent"` is a backend-prefix precedent; `node`/`go`/`python` are bare core tools.)
- Are both `dot_config/herdr/config.toml` and `config.yml` TOML-formatted despite the `.yml` extension?
- Does the 2026-07-15 result-log evidence match the claims made about it?

## Reviewer C — architecture / senior engineering

Reads:
- target design (full)
- [`docs/specifications/02-installed-programs.md`](../specifications/02-installed-programs.md)
- [`dependencies/packages.toml`](../dependencies/packages.toml)
- [`programs/generate_deps/tests/test_mise_manager.py`](../programs/generate_deps/tests/test_mise_manager.py)
- [`docs/specifications/implementations/2026-07-15-herdr-container-install-design.md`](../specifications/implementations/2026-07-15-herdr-container-install-design.md) (old design header only)

Evaluation points:
- Is removing `herdr` from `packages.toml` entirely the only coherent option given the generator contract?
- Is the AUTO-GEN disappearance intentionally explained?
- Is mise the sole install/version/update authority, with no competing `herdr update` path?
- Is historical treatment coherent (byte-identical preservation, superseded design, executed plan with snippet correction)?
- Is the `latest` tradeoff vs. SHA pinning sound and documented?
- Is rollback coherent with forward migration?

## Reviewer E — operability / runtime

Reads:
- target design (full)
- [`Makefile`](../Makefile)
- [`container/Containerfile`](../container/Containerfile) (Layer 3-4, Layer 3-8)
- [`dot_zshenv.tmpl`](../dot_zshenv.tmpl)
- [`docs/issues/2026-07-15-phase-herdr-container-install.md`](../issues/2026-07-15-phase-herdr-container-install.md)
- [`docs/issues/2026-07-09-mise-pnpm-go-build-failures.md`](../issues/2026-07-09-mise-pnpm-go-build-failures.md)

Evaluation points:
- Is fresh-volume copy-on-first-mount feasible with existing `dotfiles_mise` wiring?
- Is the one-time existing-volume migration (`podman volume rm dotfiles_mise`) the correct and only mechanism?
- Is shim PATH precedence correct so `~/.local/bin/herdr` cannot shadow the mise shim?
- Is the update procedure (`mise upgrade aqua:ogulcancelik/herdr`) feasible on host and container?
- Is rollback feasible using existing `make` targets and the documented manual volume drop?
- Is the 2026-07-09 mise failure issue stale evidence given the 2026-07-15 successful build?

## Expected outputs

Each reviewer writes a file under [`docs/reviews/`](../reviews/):
- `2026-07-15-herdr-mise-management-review-pass1-A-factual.md`
- `2026-07-15-herdr-mise-management-review-pass1-C-architecture.md`
- `2026-07-15-herdr-mise-management-review-pass1-E-operability.md`

After all three letters land, the author produces the aggregate:
- `2026-07-15-herdr-mise-management-review-pass1.md`
