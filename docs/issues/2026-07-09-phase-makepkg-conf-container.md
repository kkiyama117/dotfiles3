# Result-log — makepkg-conf-container (bake host makepkg.conf at Layer 1-2)

**Date:** 2026-07-09
**Phase:** makepkg-conf-container
**Issue:** [2026-07-09-makepkg-conf-container.md](2026-07-09-makepkg-conf-container.md) → closed
**Plan:** [2026-07-09-makepkg-conf-container-impl.md](../plans/2026-07-09-makepkg-conf-container-impl.md)
**Design:** [2026-07-09-makepkg-conf-container-design.md](../specifications/implementations/2026-07-09-makepkg-conf-container-design.md)
**Implementation commit:** `c2da9af`
**Review:** [aggregate pass-1](../reviews/2026-07-09-makepkg-conf-container-review-pass1.md)

## Summary

Baked host `makepkg.conf` into the container image at Layer 1-2 via
`container/bind/layer_1_files/makepkg.conf` → `COPY /etc/makepkg.conf`.
Paru/makepkg now use `PKGEXT='.pkg.tar.xz'` and host build flags without
chezmoi migration or runtime bind mounts. Phases 1–4 completed in `c2da9af`;
Phase 5 review (A + C + E) completed 2026-07-09 with pi-subagents.

## Acceptance evidence

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Bind file tracked via allowlist | PASS | `container/.gitignore` `!bind/layer_1_files/makepkg.conf`; `git check-ignore` exit 1 |
| 2 | Layer 1-2 COPY before mirrorlist / pacman -Syu | PASS | `Containerfile:32` < `:47` < `:50`; `test_makepkg_conf_baked_into_layer_1_2` |
| 3 | Specs 01, 03, 20 (`I-MAKEPKG1`), 21 (#24) updated | PASS | commit `c2da9af` |
| 4 | Runtime PKGEXT + paru works | PASS | `grep PKGEXT /etc/makepkg.conf` → `.pkg.tar.xz`; `paru --version` v2.1.0; `makepkg --version` 7.1.0; `stat` 644 root:root |

## Verification commands (2026-07-09)

```bash
python -m pytest container/tests/container/test_entrypoint.py::test_makepkg_conf_baked_into_layer_1_2 -v
podman exec dotfiles-manjaro zsh -ic 'grep -E "PKGEXT|COMPRESSZST" /etc/makepkg.conf'
podman exec dotfiles-manjaro zsh -ic 'paru --version; makepkg --version'
podman exec dotfiles-manjaro stat -c '%a %U:%G' /etc/makepkg.conf
podman exec dotfiles-manjaro ls /etc/makepkg.conf.d/
```

## Review outcomes

- **Letter A:** Approve (factual/correctness).
- **Letter C:** F1 RESOLVED — corrected false `.d` bypass premise in design §4 and
  `I-MAKEPKG1`; verified `fortran.conf`/`rust.conf` are comment-only.
- **Letter E:** Approve with conditions (`make build` before `make up` for rollout).

## Residual / follow-up

- **E-F2 (LOW, open):** Test and acceptance #24 pin exact `PKGEXT`; relax if zstd
  toggle becomes routine.
- **C-F2 (MEDIUM, addressed):** Full-file copy vs `.d` drop-in — deferred.
- Host `~/.config/pacman/makepkg.conf` remains outside repo (image-owned only).
