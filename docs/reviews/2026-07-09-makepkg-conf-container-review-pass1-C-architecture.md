# makepkg-conf-container — Review pass-1 (Letter C: architecture / senior engineering)

**Date:** 2026-07-09
**Reviewer:** ecc:code-architect (review subagent)
**Subject:** [`docs/specifications/implementations/2026-07-09-makepkg-conf-container-design.md`](../specifications/implementations/2026-07-09-makepkg-conf-container-design.md) + commit `c2da9af`
**Pass:** 1
**Status:** done

## Verdict

**Request changes → Approve with conditions (addressed).** The plumbing is coherent with the existing `layer_1_files`
(mirrorlist) pattern, ownership is minimal, and the observable behavior
(acceptance #24: `PKGEXT='.pkg.tar.xz'`) is correct. F1 (false `.d` bypass
premise) was **RESOLVED** in design §4 and `I-MAKEPKG1` — `.d` snippets still
apply; current drop-ins are comment-only. F2 remains an optional
maintainability follow-up (full-file vs drop-in delta).

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| F1 | HIGH | RESOLVED | design §4; `20-container-rules.md` I-MAKEPKG1 | False "bypass" premise corrected: `.d` snippets still apply after curated file; verified comment-only on current base. |
| F2 | MEDIUM | open | design §2 / §4 | The rejected "minimal delta" is, on this distro, a `/etc/makepkg.conf.d/` drop-in — the idiomatic mechanism the design mislabels as bypassed. Full 146-line copy pins the whole file and drifts from upstream `makepkg.conf` improvements. |
| F3 | LOW | open | issue AC#2; `test_entrypoint.py`; `Containerfile:32,47-50` | "COPY before `pacman -Syu`" is stricter than the real constraint (first consumer is `makepkg` at Layer 4-1). Harmless anchor, but the stated ordering requirement is over-specified. |
| F4 | LOW | blocked | design S1 (§1) | Byte-stability vs host `~/.config/pacman/makepkg.conf` is unverifiable — the host file is not in the repo/build context. Blocker is external (host-only file). |

### F1 details — the `.d` bypass premise is false

Design §4 states:

> The base image's `/etc/makepkg.conf` sources
> `/etc/makepkg.conf.d/{fortran,rust}.conf`. The full-file COPY replaces the
> entire file, so `.d/` snippets are no longer sourced.

And this was promoted to a normative invariant in `20-container-rules.md`:

> I-MAKEPKG1: ... The full-file COPY **intentionally bypasses** the base
> image's `/etc/makepkg.conf.d/{fortran,rust}.conf` snippets.

This is incorrect. `makepkg` — not the content of `/etc/makepkg.conf` — is what
loads the drop-in directory. From pacman's `source_makepkg_config()`
(GitLab `pacman/pacman` commit `007261ad`, and documented in `makepkg.conf(5)`):

```sh
if [[ -r $MAKEPKG_CONF ]]; then
    source_safe "$MAKEPKG_CONF"
    if [[ -d "$MAKEPKG_CONF.d" ]] && compgen -G "$MAKEPKG_CONF.d"/'*.conf' > /dev/null; then
        for c in "$MAKEPKG_CONF.d"/*.conf; do
            source_safe "$c"
        done
    fi
fi
```

Load order (per `makepkg.conf(5)`): `/etc/makepkg.conf` → `/etc/makepkg.conf.d/*.conf`
→ `$XDG_CONFIG_HOME/pacman/makepkg.conf` / `~/.makepkg.conf`.

Consequences of the false premise:

1. **The snippets are NOT bypassed.** After the curated `/etc/makepkg.conf` is
   sourced, `makepkg` still sources `/etc/makepkg.conf.d/*.conf`. So every
   `makepkg -si` (Layer 4-1 paru bootstrap) and every `paru -S` (Layer 4-2 /
   runtime) still applies `fortran.conf` / `rust.conf` if present.
2. **`.d` wins over the curated file for any shared variable**, because it is
   sourced last. The curated file's intent could be silently overridden by a
   future base-image drop-in — and a maintainer reading I-MAKEPKG1 ("bypassed")
   would not think to look there.
3. **A wrong contract now lives in a normative spec** (`20-container-rules.md`
   I-MAKEPKG1) that other docs reference by ID. This is architectural
   misinformation, not just a doc typo.

Why acceptance #24 still passes: `fortran.conf` / `rust.conf` set language
build flags (`FFLAGS`/`FCFLAGS`, `RUSTFLAGS`/debug), not `PKGEXT` or
`COMPRESSZST`, so `grep PKGEXT /etc/makepkg.conf` is unaffected — the test
inspects the file on disk, not `makepkg`'s effective environment. The green
test masks the wrong mental model.

**Suggested fix (pick one, then reword §4 + I-MAKEPKG1 to match):**

- **(A) Accept `.d` (recommended, lowest cost):** Drop the "bypass" language.
  State plainly that `.d` snippets still apply and are sourced *after* the
  curated file. Confirm no `.d` snippet sets a variable the curated file cares
  about (see Q1). This is honest and matches actual behavior.
- **(B) Genuinely isolate from `.d`:** If isolation is truly the goal, the
  change must also neutralize the directory (e.g. `RUN rm -f /etc/makepkg.conf.d/*.conf`
  or copy an empty dir) in Layer 1-2. The current commit does **not** do this,
  so the stated intent is unimplemented.

**Verification:** `podman run --rm localhost/dotfiles-manjaro:latest bash -c
'source /usr/share/makepkg/util.sh 2>/dev/null; makepkg --printsrcinfo >/dev/null 2>&1;
ls -1 /etc/makepkg.conf.d/ 2>/dev/null; grep -H "" /etc/makepkg.conf.d/*.conf 2>/dev/null'`
— if any `.conf` exists, the "bypass" claim is disproven directly.

### F2 details — full-file copy vs the idiomatic drop-in

Design §2 rejects a "minimal ~10-line delta" as a "YAGNI fallback only if review
requires it." On Arch/Manjaro the idiomatic minimal delta *is* a
`/etc/makepkg.conf.d/` drop-in — the exact mechanism the manual recommends for
"specific additions (e.g. build flags)" and the mechanism §4 mistakenly believes
it is bypassing (F1). So the design rejected the distro-native option while
simultaneously misunderstanding it.

Architectural trade-off of the chosen full copy:

- **Cost:** 146 lines pinned to one point-in-time snapshot of the host file.
  Upstream `makepkg.conf` evolution (new hardening defaults, new variables,
  e.g. the base image's `-D_FORTIFY_SOURCE=3` in §3) will never reach the
  container. Every future divergence is invisible until someone diffs by hand
  (design §6 already flags the reverse host-drift risk).
- **The mirrorlist precedent is weaker than it looks.** `pacman_mirrorlist` is
  inherently host/volatile (it even carries `TODO: auto generate mirrorlist`),
  so a full snapshot is appropriate there. `makepkg.conf` is ~95% distro
  defaults with a handful of deltas (§3 lists 4), so a full snapshot maximizes
  drift surface for minimal unique content — the opposite ratio.
- **A `zz-dotfiles.conf` drop-in** carrying only `PKGEXT`, `COMPRESSZST`,
  `MAKEFLAGS`, `CPPFLAGS`, `CFLAGS`, `CXXFLAGS`, `LDFLAGS` would: keep upstream
  defaults live, self-document the delta, and stay allowlist-tracked exactly
  like the current file. It is not YAGNI — it is the lower-maintenance
  architecture.

This is a MEDIUM (maintainability) item; the full copy is defensible if the
author consciously prefers a frozen, self-contained file, but the design should
say so on the correct grounds (not the F1 bypass reasoning).

### F3 details — ordering over-specification

Issue AC#2 and `test_makepkg_conf_baked_into_layer_1_2` assert
`copy_idx < mirror_idx < syu_idx` (makepkg COPY before mirrorlist before
`pacman -Syu`). Functionally, `pacman -Syu` installs *binary* packages and never
reads `/etc/makepkg.conf`; the first real consumer is `makepkg -si` at Layer
4-1. So "before `pacman -Syu`" is a stricter constraint than correctness
requires. It is a harmless, stable anchor and keeps the two Layer-1 COPYs
grouped, so no change is mandatory — but the design/spec framing ("before the
first `pacman -Syu`") slightly misstates *why* the placement matters. Consider
"before the first `makepkg`/`paru` invocation (Layer 4-1)" for accuracy.

### F4 details — S1 byte-stability unverifiable

S1 asserts the bind file is "a byte-stable copy of the host file." The host file
`~/.config/pacman/makepkg.conf` is not tracked in the repo and is outside the
build context, so I cannot confirm byte-identity from evidence. The committed
file is internally consistent with §3's deltas (`PKGEXT='.pkg.tar.xz'`,
`COMPRESSZST=(zstd -c -z -q -)`, `MAKEFLAGS="-j$(($(nproc)+1))"`,
`-D_FORTIFY_SOURCE=2` + `-fstack-protector-strong`). Left as a note; not
actionable within this repo.

## Correct (good architecture — with evidence)

- **Coherence with the `layer_1_files` (mirrorlist) pattern is solid.** The new
  file sits in `container/bind/layer_1_files/`, is allowlisted in
  `container/.gitignore` (`!bind/layer_1_files/makepkg.conf`, line 4), and is
  copied in Layer 1-2 (`Containerfile:32`) exactly parallel to
  `pacman_mirrorlist` (`Containerfile:47`). Image-owned `root:root`, no runtime
  bind mount, no named volume — S3 is honored and the ownership model is the
  simplest possible.
- **Ownership/complexity is minimal.** One allowlist line, one `COPY`, one bind
  file. No new stage, no new mount, no entrypoint change. The change respects
  I6–I8 (no ad-hoc `pacman -S`, no new layer ordinal coupling).
- **Scope discipline on `_verify_image_fresh` is the right call** (design §5).
  Deliberately *not* extending the entrypoint-only freshness hash keeps
  `_verify_image_fresh` single-purpose (I-RUN3), and the rollout is documented
  as acceptance #24 parallel to the SSH #23 precedent — consistent with how the
  repo has handled prior image-content rollouts.
- **Chezmoi and runtime-bind rejections (design §2) are sound.** Chezmoi is
  correctly excluded (user scoped this as build-time image config, not user
  config migration; `host_config_list.md` §8 updated to reflect image-owned).
  Runtime bind mount is correctly rejected for reproducibility (S3).
- **Toggle story (S4) is architecturally clean:** compression changes are a
  one-line bind-file edit + `make build`, no Containerfile churn — a good
  separation of volatile config from build structure.

## Verified premises

- **P1:** `makepkg` loads `/etc/makepkg.conf` then `/etc/makepkg.conf.d/*.conf`
  automatically (pacman `source_makepkg_config`, GitLab commit `007261ad`;
  `makepkg.conf(5)` load-order section). Confirms F1.
- **P2:** The curated file (`container/bind/layer_1_files/makepkg.conf:1-147`)
  contains no `source .../makepkg.conf.d` line and sets no variable that
  `fortran`/`rust` drop-ins are known to set, so acceptance #24
  (`PKGEXT`/`COMPRESSZST` grep) holds regardless of F1.
- **P3:** `.gitignore` allowlist (`container/.gitignore:1-5`) tracks
  `makepkg.conf` via the same `bind/**/*` + re-include pattern as
  `pacman_mirrorlist` and `entrypoint.sh`; `git show --stat c2da9af` confirms the
  file is committed.

## Open questions

- **Q1:** Do `/etc/makepkg.conf.d/fortran.conf` and `rust.conf` actually exist
  in `manjarolinux/base:latest`, and what variables do they set? Because they
  are sourced *after* the curated file (P1), any variable they share with the
  curated file will override it. This must be answered to know whether the
  curated intent actually survives at runtime.
- **Q2:** Is isolation from `/etc/makepkg.conf.d/` genuinely desired, or is it
  acceptable for `.d` snippets to continue applying? The answer selects F1 fix
  (A) vs (B). The current commit implements neither isolation nor an explicit
  "let `.d` apply" acknowledgement.
