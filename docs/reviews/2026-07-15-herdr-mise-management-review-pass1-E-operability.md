# herdr-mise-management — Review pass-1 (Letter E: operability / runtime)

**Date:** 2026-07-15
**Reviewer:** review subagent
**Subject:** [`docs/specifications/implementations/2026-07-15-herdr-mise-management-design.md`](docs/specifications/implementations/2026-07-15-herdr-mise-management-design.md)
**Pass:** 1
**Status:** done

## Verdict

**Approve.** All operability mechanisms (fresh-volume seed, existing-volume migration, PATH/shim discovery, update, rollback) are feasible against the actual `Makefile` and `Containerfile`, and the stale 2026-07-09 issue is correctly judged a non-blocker on newer build evidence. Two LOW/MEDIUM notes, no blockers.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| E1 | LOW | addressed | design §6.1/§6.3 | one-time volume migration relies on raw `podman volume rm dotfiles_mise`; no dedicated make target |
| E2 | MEDIUM | addressed | design §8 Q1 / issue 2026-07-09 | `herdr` shares `pnpm`'s aqua backend; the 07-09 failure issue is still formally `open` though its symptoms are resolved |

### E1 details

`Makefile` exposes only `clean` (removes **all** volumes + image, lines 137-139) and `down` (container only, 133-135); there is no target that drops just `dotfiles_mise`. The design correctly warns operators off `make clean` and prescribes the manual `podman volume rm dotfiles_mise` between `make down` and `make up` (§6.1 step 3, §6.3 step 4). This is feasible and unambiguous; a `make reset-mise` convenience target is out of scope. No change required.

### E2 details

The 07-09 build failure ([`docs/issues/2026-07-09-mise-pnpm-go-build-failures.md`](docs/issues/2026-07-09-mise-pnpm-go-build-failures.md), Status: **open**) had two causes: (a) `go` post-install `GOROOT` pinned to `.../go/latest`, and (b) `pnpm` aqua Sigstore/TUF attestation cache permission error. Cause (a) is verifiably fixed — `dot_zshenv.tmpl` lines 161-166 now explicitly do **not** export `GOROOT` ("mise shims resolve it per invocation"). Cause (b) has no recorded root-cause fix, but the 2026-07-15 five-stage build succeeded (result-log: full ~17 min build reaching runtime; `pi --version` PASS, which requires Layer 3-5 `mise exec node pnpm` → proves aqua `pnpm` installed; `herdr --version` PASS on the running container). Since `herdr` also uses the aqua backend, a small recurrence risk exists, but the design handles it correctly: `make build` is the mandatory acceptance gate (§6.2), and a recurrence is explicitly an *implementation* blocker, not a *design* blocker (§8 Q1, I3). Recommendation (implementation-phase, non-blocking): annotate/close 2026-07-09 with the 07-15 build evidence so the "stale evidence" claim is backed by tracker status.

## Verified premises

- **P1 (fresh-volume copy, I5/S6):** `Makefile:107` mounts `dotfiles_mise` at `.../.local/share/mise`, which equals `MISE_DATA_DIR` (`dot_zshenv.tmpl:154`). Layer 3-4 bakes `mise install --yes` output there (`Containerfile:212-223`). Makefile comment 22-26 confirms Podman copy-on-first-mount seeds build-time binaries into the empty volume — same pattern as cargo/rustup. First `make up` therefore seeds `herdr`. Confirmed.
- **P2 (existing-volume migration):** Because copy-on-first-mount only fires on an **empty** volume, a pre-existing `dotfiles_mise` will not gain the aqua install on `make up` alone; the design's mandatory one-time `podman volume rm` (§6.1) is the correct and only mechanism. Confirmed.
- **P3 (PATH / shim discovery, I4/S5):** `dot_zshenv.tmpl:183-186` runs `eval "$(mise activate zsh --shims)"` and prepends `$MISE_DATA_DIR/shims` to `path` **last** among all prepends (after `~/.local/bin` at :46, cargo :159, pnpm :180), so shims hold highest precedence; `typeset -U path` (:21) dedups. `which herdr` resolves to a shim even if a stale `~/.local/bin/herdr` existed — and Layer 3-8 removal means it will not exist post-rebuild (`~/.local/bin` is an image path, not a volume). Confirmed; no `dot_zshenv.tmpl` change needed (design non-scope correct).
- **P4 (update):** `mise upgrade aqua:ogulcancelik/herdr` (§5.5) runs on host or via `podman exec`; no image rebuild for version bumps. Feasible. Confirmed.
- **P5 (rollback, §6.3):** git revert + restore Layer 3-8/`packages.toml` + remove aqua entry + `make build && make down && podman volume rm dotfiles_mise && make up`. Uses existing targets plus the same documented manual volume drop. Feasible. Confirmed.
- **P6 (persistence, S6):** `make down` removes only the container (`Makefile:133-135`); `dotfiles_mise` survives, so `make up` re-mounts the seeded volume and `herdr` persists. Confirmed.

## Open questions

- None blocking. E2's tracker-status cleanup is an implementation-phase follow-up, not a precondition for design approval.
