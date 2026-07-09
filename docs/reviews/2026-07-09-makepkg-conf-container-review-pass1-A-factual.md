# makepkg-conf-container — Review pass-1 (Letter A: factual / correctness)

**Date:** 2026-07-09
**Reviewer:** pi review subagent (Letter A, factual/correctness)
**Subject:** [`docs/specifications/implementations/2026-07-09-makepkg-conf-container-design.md`](../specifications/implementations/2026-07-09-makepkg-conf-container-design.md) + commit `c2da9af` ("Bake host makepkg.conf into the container image at Layer 1-2")
**Pass:** 1
**Status:** done

## Verdict

**Approve.** All five verification targets check out against their cited sources.
The Layer 1-2 `COPY` is correctly ordered, the bind file carries the curated
`PKGEXT`/`COMPRESSZST`/`MAKEFLAGS`/hardening values claimed in the design, the
test assertions match both the Containerfile and the bind file, and the spec
acceptance criteria (issue, spec 20 `I-MAKEPKG1`, spec 21 #24) are satisfied.
No blockers.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| A1 | LOW | addressed | `container/Containerfile:32,47,50` | `COPY makepkg.conf` precedes mirrorlist COPY and `pacman -Syu`; order matches test + design S2/issue #2. |
| A2 | LOW | addressed | `container/bind/layer_1_files/makepkg.conf:145` | `PKGEXT='.pkg.tar.xz'` present verbatim. |
| A3 | LOW | addressed | `docs/.../20-container-rules.md:209-217` | `I-MAKEPKG1` states image-owned, not chezmoi-managed; matches design S3 and Containerfile (`COPY`, no bind mount / no `dot_config` entry). |
| A4 | LOW | addressed | `container/tests/container/test_entrypoint.py:167-177` | All four test assertions resolve against current Containerfile + bind file. |
| A5 | LOW | addressed | issue #1-4 / spec 21 #24 | Acceptance criteria met (allowlist, COPY placement, spec sync, PKGEXT + COMPRESSZST + stat 644 root:root). |
| A6 | LOW | Note | `docs/issues/2026-07-09-makepkg-conf-container.md:29-31` | Issue #2 phrases placement as "before `pacman -Syu`"; makepkg.conf is not consumed by `pacman` itself (first real consumer is `makepkg`/`paru` at Layer 4-1, per design S2). Placement satisfies both wordings; wording is imprecise but harmless. |
| A7 | LOW | Note | `docs/.../design.md:42-49` §3 | Base-image default column (`.pkg.tar.zst`, `zstd -c -T0 -`, `-j2`, `-D_FORTIFY_SOURCE=3`) not independently verified this run (requires inspecting `manjarolinux/base`). Curated values verified; delta direction is plausible. |

### A1 details

`container/Containerfile`:
- L32 `COPY bind/layer_1_files/makepkg.conf /etc/makepkg.conf`
- L47 `COPY bind/layer_1_files/pacman_mirrorlist /etc/pacman.d/mirrorlist`
- L50 `RUN ... pacman -Syu --noconfirm --needed ...`

Order `32 < 47 < 50` satisfies design **S2** ("before the first `makepkg`/`paru`
invocation (Layer 4-1)") and issue acceptance **#2** ("before `pacman -Syu`").
Verified by the test at L174-177 (`copy_idx < mirror_idx < syu_idx`), which
indexes the exact same strings.

### A2 details

`container/bind/layer_1_files/makepkg.conf:145` → `PKGEXT='.pkg.tar.xz'`
(single-quoted, exact). Design §1 S1 / §3 and issue #4 both require this value.
Also confirmed against §3 diff table and spec 21 #24.

### A3 details

`I-MAKEPKG1` (spec 20 L209-217): "`/etc/makepkg.conf` is image-owned, not
chezmoi-managed. The build-time `COPY ... /etc/makepkg.conf` (Layer 1-2, before
the first `pacman -Syu`) embeds the curated ... To switch compression ... edit
the bind file's `PKGEXT` line and re-run `make build` — no Containerfile edit
required." This matches design S3/S4 and §4 (full-file COPY bypasses
`/etc/makepkg.conf.d/{fortran,rust}.conf`). No chezmoi `dot_config/pacman/`
entry exists; `docs/references/host_config_list.md:161` records the host file as
"container-side ... not chezmoi-managed", consistent with the "no migration"
claim.

### A4 details

`test_makepkg_conf_baked_into_layer_1_2` (L167-177) assertions vs sources:
- `"COPY bind/layer_1_files/makepkg.conf /etc/makepkg.conf"` → Containerfile L32 ✓
- `"PKGEXT='.pkg.tar.xz'"` → bind file L145 ✓
- `"COMPRESSZST=(zstd -c -z -q -)"` → bind file L134 ✓
- ordering `copy_idx < mirror_idx < syu_idx` (indexes `"COPY bind/layer_1_files/pacman_mirrorlist"` L47 and `"pacman -Syu --noconfirm"` L50) ✓

Path constant `MAKEPKG_CONF` (L14) resolves to
`container/bind/layer_1_files/makepkg.conf` (`parents[3]` from
`container/tests/container/test_entrypoint.py` = repo root). Correct.

### A5 details

Issue acceptance criteria (L24-37):
1. Bind file exists as byte copy + tracked via `container/.gitignore` allowlist —
   `container/.gitignore:4` `!bind/layer_1_files/makepkg.conf`;
   `git check-ignore` returns exit 1 (not ignored); `git ls-files -s` shows the
   file tracked at mode `100644`. ✓
2. Layer 1-2 `COPY ... before pacman -Syu` — see A1. ✓
3. Specs 01, 03, 20, 21 updated — `01-file-structures.md:54`,
   `03-makefile.md:13`, `20-container-rules.md:209` (`I-MAKEPKG1`),
   `21-container-build-flow.md:18,214` (#24). All present. ✓
4. In-container `PKGEXT='.pkg.tar.xz'` + `paru --version` works — corroborated by
   the provided smoke evidence (PKGEXT `.pkg.tar.xz`, paru v2.1.0, makepkg 7.1.0).

Spec 21 #24 additionally asserts `COMPRESSZST=(zstd -c -z -q -)` (bind file
L134 ✓) and `stat -c '%a %U:%G' /etc/makepkg.conf` → `644 root:root`. The
source is tracked at `100644`; `COPY` preserves source mode and runs as root at
Layer 1-2 (before the `USER ${USERNAME}` switch at L101), so `644 root:root` is
the expected result — matches the smoke evidence.

## Verified premises

- P1: Working tree is clean and there are no staged files (`git status --porcelain` empty).
- P2: `c2da9af` is an ancestor of `HEAD` (`e6eb8f3`); the only later commit touching these files is `e48a000` (Layer 3-4 mise fix), which does not alter the Layer 1-2 `COPY`, the bind file, or the test — so the reviewed current state faithfully reflects `c2da9af`.
- P3: Design §3 diff-table curated values are byte-consistent with the bind file: `COMPRESSZST=(zstd -c -z -q -)` (L134), `MAKEFLAGS="-j$(($(nproc)+1))"` (L45), `CPPFLAGS="-D_FORTIFY_SOURCE=2"` (L40), `-fstack-protector-strong` in `CFLAGS`/`CXXFLAGS` (L41-42).
- P4: `.gitignore` allowlist glob (`bind/**/*` deny, then per-file re-includes) correctly un-ignores the makepkg bind file (`git check-ignore` exit 1).

## Open questions

- Q1: (A7, non-blocking) Should the design §3 base-image default column be
  annotated as "manjarolinux/base defaults, not re-verified" or backed by an
  `podman run --rm manjarolinux/base grep ...` capture? Purely documentary; does
  not affect correctness of the implementation.
