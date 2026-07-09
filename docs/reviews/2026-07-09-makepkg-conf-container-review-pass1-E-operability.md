# makepkg-conf-container — Review pass-1 (Letter E: operability / runtime)

**Date:** 2026-07-09
**Reviewer:** review subagent (Letter E, operability/runtime)
**Subject:** [`docs/specifications/implementations/2026-07-09-makepkg-conf-container-design.md`](../../docs/specifications/implementations/2026-07-09-makepkg-conf-container-design.md) + commit `c2da9af`
**Pass:** 1
**Status:** done

## Verdict

**Approve with conditions.** The Layer 1-2 `COPY` is build-feasible, the acceptance
#24 runtime checks are satisfiable against the committed bind file, and the
zstd-toggle-via-bind-file workflow is documented. The only condition is
operational: existing deployments must run `make build` before `make up`, and
`_verify_image_fresh` cannot detect that gap by design. No blockers.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| F1 | LOW | addressed | `Makefile:86-97`; spec 21 #24; design §5 | `make up`'s `_verify_image_fresh` only hashes `entrypoint.sh`, so a `make up` without `make build` silently runs a stale image with the old `PKGEXT`. Documented; intentionally not extended. |
| F2 | LOW | open | `container/tests/container/test_entrypoint.py:167-177`; spec 21 #24 | The regression test and acceptance #24 hard-code `PKGEXT='.pkg.tar.xz'`, coupling them to one compression choice and partially contradicting design S4/§2's "toggle by editing the bind file" story. |
| F3 | LOW | addressed | design §4; `makepkg.conf:1-147` | Full-file COPY drops the base image's `source /etc/makepkg.conf.d/{fortran,rust}.conf` snippets. Intentional; paru bootstrap empirically succeeds under the new conf (smoke evidence). |

### F1 details

`up:` depends on `_verify_image_fresh`, which compares only the entrypoint hash:

```86:97:Makefile
_verify_image_fresh:
	@src_hash=$$(sha256sum $(BUILD_CTX)/bind/layer_5_files/entrypoint.sh | cut -d' ' -f1); \
	img_hash=$$(podman run --rm --entrypoint /usr/bin/sha256sum $(IMAGE) /usr/local/bin/entrypoint.sh 2>/dev/null | cut -d' ' -f1); \
	...
```

`makepkg.conf` is baked at Layer 1-2 and is invisible to this check, so editing
the bind file and running `make up` without `make build` yields a container that
still reports the previous `PKGEXT`. This is called out in
`docs/specifications/21-container-build-flow.md` #24 ("existing deployments must
run `make build` before the first `make up` after this change ... parallel to SSH
rollout #23") and design §5 ("Do **not** extend `_verify_image_fresh` in this
change"). Consistent with the existing SSH rollout #23 precedent. No fix required;
listed so the aggregate pass records the operator-discipline dependency.

**Verification:** `git show c2da9af -- Makefile` shows no `_verify_image_fresh`
change (the commit did not touch `Makefile`); confirmed the target still hashes
only `entrypoint.sh`.

### F2 details

The added test asserts the literal compression values:

```167:177:container/tests/container/test_entrypoint.py
    assert "COPY bind/layer_1_files/makepkg.conf /etc/makepkg.conf" in containerfile
    assert "PKGEXT='.pkg.tar.xz'" in makepkg
    assert "COMPRESSZST=(zstd -c -z -q -)" in makepkg
    ...
```

Acceptance #24 likewise pins `PKGEXT='.pkg.tar.xz'`. Design S4/§2 and spec 20
`I-MAKEPKG1` advertise switching compression by editing only the bind file's
`PKGEXT` line + `make build`. An operator who follows S4 to switch to
`.pkg.tar.zst` breaks both the regression test and acceptance #24. This is a minor
tension between the "freely toggle" ergonomics and a value-pinned guard, not a
correctness defect. Suggested follow-up (optional, not this pass): have the test
assert the `COPY` placement + presence of a `PKGEXT=` line rather than the exact
extension, and rephrase #24 as "matches the committed bind file" if toggling is
meant to be routine. Left `open` as a documentation/test-design note.

### F3 details

The curated `container/bind/layer_1_files/makepkg.conf` (147 lines) contains no
`source /etc/makepkg.conf.d/...` directive, so the base image's Rust/Fortran
snippets are no longer applied to `paru`/`makepkg` builds. Design §4 states this is
intentional (the curated `CFLAGS`/`MAKEFLAGS`/hardening are self-contained). The
supplied smoke evidence (`paru --version` and `makepkg --version` both succeed in
the running container built from this conf) demonstrates the paru Layer 4-1
bootstrap is not regressed in practice. `addressed`.

## Verified premises

- **P1 (build feasibility):** `make build` uses `BUILD_CTX = $(CURDIR)/container`
  (`Makefile:41,75`); the COPY source `bind/layer_1_files/makepkg.conf` resolves to
  `container/bind/layer_1_files/makepkg.conf`, which exists and is git-tracked via
  the `container/.gitignore` allowlist (`!bind/layer_1_files/makepkg.conf`). The
  file is present in the build context, so the `COPY` at `Containerfile:32`
  succeeds.
- **P2 (ignore-file safety):** No `container/.containerignore` or
  `container/.dockerignore` exists; the only `.containerignore` is at repo root and
  (per spec 21 Q2) is applied to the `srcroot` named context, not the `container/`
  main build context. Therefore `makepkg.conf` is not excluded from the build
  context. Verified via directory listing.
- **P3 (acceptance #24 — `stat` mode):** COPY runs as root (before
  `USER ${USERNAME}`) so ownership is `root:root`; the host source file mode is
  `644` (verified `stat -c '%a'` → `644`), and `COPY` preserves source mode, so
  `/etc/makepkg.conf` is `644 root:root` — matches #24's `stat` assertion.
- **P4 (acceptance #24 — `grep` output):** `makepkg.conf:145` is
  `PKGEXT='.pkg.tar.xz'` and `:134` is `COMPRESSZST=(zstd -c -z -q -)`; both are the
  only lines matching `grep -E "PKGEXT|COMPRESSZST"` (no commented duplicates), so
  the #24 grep yields exactly the asserted two lines.
- **P5 (ordering):** `Containerfile` orders the makepkg.conf COPY (line 32) before
  the mirrorlist COPY (line 47) and before `pacman -Syu` (line 49-50); the added
  test's `copy_idx < mirror_idx < syu_idx` assertion is satisfied. `pacman -Syu`
  consumes `pacman.conf`, not `makepkg.conf`, so placing the COPY earlier is
  harmless. `makepkg.conf` is in place before the first `makepkg`/`paru` at Layer
  4-1 (S2).
- **P6 (zstd toggle documented):** The bind-file-only compression switch is
  documented in design S4/§2 and spec 20 `I-MAKEPKG1` ("To switch compression
  (e.g. xz → zstd), edit the bind file's `PKGEXT` line and re-run `make build` — no
  Containerfile edit required."). No Containerfile change is required to toggle.
- **P7 (added test passes):** `python3 -m pytest container/tests/container/test_entrypoint.py -k makepkg -q` → `1 passed`.

## Open questions

- Q1 (for design author, non-blocking): Should the makepkg regression test and
  acceptance #24 be relaxed to tolerate the S4 zstd toggle (assert a `PKGEXT=` line
  rather than the exact `.pkg.tar.xz` value), or is `.pkg.tar.xz` the committed
  canonical default that a toggle is expected to also update in the test/spec? (See
  F2.)
