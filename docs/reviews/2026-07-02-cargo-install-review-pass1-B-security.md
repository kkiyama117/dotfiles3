# cargo-install — Review pass-1 (Letter B: security)

**Date:** 2026-07-02
**Reviewer:** ecc:security-reviewer (subagent)
**Subject:** [`docs/specifications/implementations/2026-07-02-cargo-install-design.md`](../../../docs/specifications/implementations/2026-07-02-cargo-install-design.md)
**Pass:** 1
**Status:** in-review

## Verdict

Request changes. The design introduces no secret-bake and preserves the
non-root invariant (good), but it adds **two supply-chain trust gaps that
must be tightened before implementation**: (1) the `cargo-binstall` bootstrap
tarball is fetched from a floating `/latest/` URL with no version pin and no
SHA256 verification, and (2) the `cargo binstall -y --no-confirm` invocation
silently trusts arbitrary third-party prebuilt binaries without mandating
`--secure`/provenance enforcement. Both are flagged as open questions (Q1/Q2)
in the design itself; from the security perspective they are HIGH, not
deferrable nits, because the installed binaries land on `$PATH` (`$CARGO_HOME/bin`)
and run as the interactive user at runtime.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| F1 | HIGH | open | `design §5.2` Layer 3-5 RUN | cargo-binstall tarball fetched from floating `/latest/` URL with no version pin and no checksum verification |
| F2 | HIGH | open | `design §5.2` Layer 3-6 RUN | `cargo binstall -y --no-confirm` silently trusts third-party prebuilt binaries; `--secure`/provenance not mandated |
| F3 | MEDIUM | open | `design §5.2` Layer 3-5 RUN | `curl \| tar -xz` into `$CARGO_HOME/bin` (PATH-injected) with no integrity gate — malicious archive can shadow commands |
| F4 | LOW | open | `design §5.2` Layers 3-5/3-6 | No TLS certificate pinning; relies on system CA store (consistent with existing rustup/mise precedent) |
| F5 | LOW | open | `design §3` I6 / `§5.2` | `~/.cache/cargo-binstall` BuildKit cache mount shared across builds by target-path key only — no isolation (acceptable: public binaries only) |

### F1 details

**Quote (design §5.2, Layer 3-5):**
```dockerfile
curl -L --proto =https --tlsv1.2 -sSf \
  https://github.com/cargo-bins/cargo-binstall/releases/latest/download/cargo-binstall-x86_64-unknown-linux-musl.tgz \
| tar -xz -C "$CARGO_HOME/bin";
```

**Issue:** The URL uses `/releases/latest/download/` — a floating tag. The
exact binary installed changes every time a new cargo-binstall release
publishes, so:
- **Non-reproducible builds:** two `make build` invocations separated by an
  upstream release produce different images with no indication.
- **No integrity verification:** there is no `sha256sum -c` or detached
  signature check. If the GitHub release asset is tampered (compromised
  maintainer token, stolen release pipeline, or a MITM downgrading TLS —
  though `--tlsv1.2` mitigates the latter), a malicious `cargo-binstall`
  binary lands in `$CARGO_HOME/bin` and runs as `${USERNAME}` at every
  subsequent build **and** at runtime (it persists via the `dotfiles_cargo`
  volume). A malicious binstall can in turn serve malicious "prebuilt"
  archives for every `layer = 3` cargo tool (F2 compounds this).
- The design's own Q1 acknowledges the asset name / install path is
  "to be confirmed," but Q1 frames it as a packaging question, not a
  security question. From the B perspective the trust gap is the issue,
  not just the asset name.

**Suggested fix:**
1. Pin to a specific release version, e.g.
   `https://github.com/cargo-bins/cargo-binstall/releases/download/v1.x.y/cargo-binstall-x86_64-unknown-linux-musl.tgz`
   (hard-code the version in the Containerfile; record it in a comment).
2. Fetch the companion `*.tgz.sha256sum` (cargo-binstall publishes
   `cargo-binstall-*.tgz.sha256sum` per release) and verify with
   `sha256sum -c` before extracting. Sketch:
   ```dockerfile
   curl -L --proto =https --tlsv1.2 -sSf -o /tmp/binstall.tgz \
     https://github.com/cargo-bins/cargo-binstall/releases/download/v1.x.y/cargo-binstall-x86_64-unknown-linux-musl.tgz
   curl -L --proto =https --tlsv1.2 -sSf \
     https://github.com/cargo-bins/cargo-binstall/releases/download/v1.x.y/cargo-binstall-x86_64-unknown-linux-musl.tgz.sha256sum \
     | sha256sum -c -
   tar -xz -C "$CARGO_HOME/bin" -f /tmp/binstall.tgz
   ```
3. If a SHA file is not published for the exact asset, pin the expected
   SHA256 as a literal in the Containerfile and verify against it.
4. Record the pinned version + SHA in spec 24 / spec 20 `I-CARGO1` so the
   upgrade path is auditable (a version bump is a deliberate review event,
   not a side effect of `/latest/`).

**Verification:** `make build` twice with no upstream change produces
identical `$CARGO_HOME/bin/cargo-binstall` SHA; `podman exec ... sha256sum
$CARGO_HOME/bin/cargo-binstall` matches the pinned value.

### F2 details

**Quote (design §5.2, Layer 3-6):**
```dockerfile
if [ -n "$pkgs" ]; then cargo binstall -y --no-confirm ${=pkgs}; \
```

**Issue:** `cargo binstall` fetches prebuilt binaries from each crate's
GitHub releases. With `-y` / `--no-confirm`, binstall installs the binary
**without prompting the user to review the binary source** — this is
exactly the trust prompt that binstall's interactive mode exists to
surface. The design relies on `--no-confirm` for non-interactivity (Q2
admits the flag set is unconfirmed) but does not mandate `--secure`.

`cargo binstall --secure` enforces that the fetched binary is a
**signed** release artifact (binstall's provenance/strategy
verification). Without `--secure`, binstall will install an unsigned
binary from any compatible GitHub release asset, so a compromised crate
release (or a typosquatted crate name in `layer_3/cargo.txt`) becomes a
direct code-execution path on the build host and in the runtime image.

The blast radius is wider than F1: F1 is one binary (binstall itself);
F2 is **every `layer = 3` cargo tool** (currently `topgrade`, plus
whatever future entries land in `layer_3/cargo.txt`). The Rust packages
rule (design §5.4 spec 24 §3) requires build-time cargo entries to "have
prebuilt binaries" but says nothing about **signed** prebuilt binaries.

**Suggested fix:**
1. Mandate `--secure` in the Layer 3-6 invocation:
   `cargo binstall -y --secure ${=pkgs}`.
2. If `--secure` rejects a legitimately-unsigned-but-trusted tool,
  treat that as a **layer = 6 (runtime-manual)** entry, not as a reason
  to drop `--secure` from the build path. Record this in spec 24 §3:
  "build-time (`layer = 3`) cargo entries MUST ship a signed/cargo-binstall
  `--secure`-compatible prebuilt; unsigned-prebuilt tools are
  runtime-manual (`layer = 6`)."
3. Resolve Q2 in the design to the specific flag set
  (`--secure` + `-y`), not "to be confirmed."
4. (Hardening, optional) Pin each `layer = 3` cargo tool to a version
  string in `packages.toml` (e.g. a `version` field or `name = "topgrade@x.y.z"`)
  so a floating `latest` release cannot swap the binary between builds.

**Verification:** `cargo binstall --secure -y topgrade` succeeds in a
clean build; an unsigned-prebuilt crate in `layer_3/cargo.txt` fails the
build loudly (not silently installed).

### F3 details

**Quote (design §5.2, Layer 3-5):** `curl ... | tar -xz -C "$CARGO_HOME/bin"`

**Issue:** The pipe-from-curl-to-tar pattern extracts an unverified
archive directly into a directory on `$PATH` (`$CARGO_HOME/bin` is
PATH-injected via `.zshenv`). A malicious or corrupted archive can
include:
- A binary named `cargo` / `rustc` / `make` that shadows the real
  toolchain (since `$CARGO_HOME/bin` is early on PATH).
- Files outside the intended single binary (`tar` can include
  `../../etc/...` paths unless `--no-same-owner` / extraction scoping
  is enforced; `tar -xz` without `--strip-components` trusts the
  archive layout).

This is the same pattern as rustup (Layer 3-2: `curl | sh`) and mise
(Layer 3-3: `curl | sh`), so it is **consistent with existing precedent**
— but the existing precedent is itself unverified, and adding a third
instance widens the surface. F1 (checksum verification) is the primary
mitigation; F3 is the blast-radius observation that the extraction
target is PATH-injected.

**Suggested fix:** (layered on F1)
1. After F1's checksum gate, verify the archive contains exactly one
  file (`tar -tzf /tmp/binstall.tgz` lists a single `cargo-binstall`
  entry) before extracting — defends against path-traversal / extra
  payload.
2. Extract to a staging dir and `mv` the single binary into
  `$CARGO_HOME/bin` (rather than `tar -C "$CARGO_HOME/bin"`).
3. Document in spec 24 that the bootstrap extraction is single-file +
  checksum-gated.

**Verification:** `tar -tzf` of the pinned tarball lists exactly one
entry; no `..` path components.

### F4 details

**Quote (design §5.2):** `--proto =https --tlsv1.2`

**Issue:** TLS is enforced (good: `--proto =https` rejects non-HTTPS,
`--tlsv1.2` sets a floor) but there is no certificate/public-key
pinning. Trust anchors on the build host's system CA store. A
compromised CA (or a build host with an injected CA, e.g. a corporate
MITM proxy) could intercept the download.

**Assessment:** This is **consistent with the existing rustup / mise
bootstraps** (Layer 3-2 / 3-3 use the same `--proto =https --tlsv1.2`
without pinning) and with the `paru`/AUR clones over HTTPS. Introducing
pinning for only binstall would be inconsistent. Treat as LOW / accepted
risk; the F1 checksum gate is the meaningful integrity control, not TLS
pinning. No change required unless the project adopts a global
pinning policy (out of scope for this design).

### F5 details

**Quote (design §3 I6 / §5.2):** `--mount=type=cache,target=/home/${USERNAME}/.cache/cargo-binstall`

**Issue:** BuildKit `--mount=type=cache` caches are shared across builds
by the target path (and optionally `--sharing` mode); without an explicit
`--sharing=private`, concurrent or sequential builds on the same builder
reuse the same cache directory. The cache holds **only downloaded public
prebuilt archives** (no credentials, no tokens — binstall fetches from
public GitHub releases). So there is **no cross-build secret leakage**.

Two minor observations (not blockers):
- The cache is not keyed by the pinned binstall version (F1); after a
  version bump, stale archives may linger in the cache. Harmless (F1's
  checksum gate rejects mismatches) but worth a note.
- If a future change ever passes credentials through a binstall invocation
  (e.g. a private crate registry), the cache could retain fetched
  artifacts from an authenticated source. Today this does not apply
  (all public). Recommend a one-line guard in spec 24: "the binstall
  cache mount is public-binary-only; any authenticated-source binstall
  invocation must NOT share this cache."

**Suggested fix:** Add the one-line spec 24 guard above. No Containerfile
change needed.

**Verification:** `podman build --no-cache` (cache cleared) reproduces
the same installed binaries as a cache-hit build (F1 checksum gate holds).

## Verified premises

- **P1 (no-secret invariant holds):** The change bakes **no secret** into
  any image layer. `cargo-binstall` and all `layer = 3` / `layer = 6`
  cargo tools are **public binaries** fetched over HTTPS from public
  GitHub releases; no credentials, tokens, or private-registry auth are
  involved in any RUN. Confirmed against spec 13 I-S3 ("secrets are
  never baked into image layers") / I-S4 ("image layers contain no
  resolved secret") and spec 20 I4 ("the image is secret-free in both
  phases"). The build-time Stage 2 pre-pass is unchanged (no new
  `bitwarden*` template calls); the new RUN steps (3-5/3-6) run in Stage
  3 `toolchain`, which inherits `build_mode = true` / secret-free
  posture. S9 / I8 in the design are accurate.
- **P2 (non-root invariant holds):** The new RUN steps (Layer 3-5
  cargo-binstall bootstrap, Layer 3-6 cargo tools) execute in Stage 3
  `toolchain`, which inherits `USER ${USERNAME}` from the end of Stage 1
  Layer 1-6 (`container/Containerfile:120`). No `USER root` is
  introduced in Stage 3; no `sudo` / `su` / `pacman` escalation appears
  in the new RUNs. The `--mount=type=cache` directives use
  `uid=${HOST_UID},gid=${HOST_GID}` so cache files are owned by the
  non-root user (consistent with existing 3-2/3-4/3-5 cache mounts).
  Spec 20 I1 (rootless), I7 (`builder`/`${USERNAME}` is the only
  non-root account; USER set before non-root installation) hold.
- **P3 (HTTPS-only):** All new network fetches use
  `curl --proto =https --tlsv1.2`, matching the existing rustup (3-2)
  and mise (3-3) precedent. No `http://` URL, no plain-FTP, no
  `git://` clone in the new layers. The `cargo binstall` fetches also
  use HTTPS (binstall's default transport).
- **P4 (cache mount is public-only):** The `~/.cache/cargo-binstall`
  cache mount stores only downloaded public prebuilt archives (binstall
  downloads from public crate GitHub releases). No podman secret
  (`/run/secrets/*`) is reachable from Stage 3 (secrets are mounted at
  runtime via `podman run --secret`, not at build time). No
  cross-build secret leakage path exists. Spec 20 I4 / spec 13 I-S3
  hold for the cache mount.
- **P5 (rootless volume persistence holds):** `cargo-binstall` installs
  to `$CARGO_HOME/bin` = `~/.local/share/cargo/bin` (the
  `dotfiles_cargo` named-volume mountpoint), owned by `${USERNAME}`.
  No root-owned file is created in the new RUNs. `make down && make up`
  preserves the volume (S6) without re-rooting (the Layer 5-2
  `/home` re-chown covers the cache-mount root-creation side effect,
  same as today).

## Open questions

- **Q-B1 (carries design Q1, security-framed):** Will the design pin
  `cargo-binstall` to a specific release version and verify a SHA256
  (detached `.sha256sum` or a hardcoded literal) before extraction,
  replacing the floating `/latest/` URL? This is required to close F1.
- **Q-B2 (carries design Q2, security-framed):** Will the design
  mandate `cargo binstall --secure` (signed/provenance-verified
  prebuilts only) for the Layer 3-6 build-time install path, and
  route unsigned-prebuilt tools to `layer = 6` (runtime-manual)? This
  is required to close F2. The exact non-interactive flag set
  (`--secure -y` vs `--secure --no-confirm`) should be resolved against
  `cargo binstall --help` and recorded in spec 24.
- **Q-B3:** Should spec 24 §3 record an explicit "build-time cargo
  entries MUST ship `--secure`-compatible (signed) prebuilts;
  unsigned-prebuilt and source-only tools are `layer = 6`" rule, so the
  trust boundary is documented rather than implicit? (Supports F2 fix.)
- **Q-B4 (non-blocking, F5):** Should spec 24 carry a one-line guard
  that the `~/.cache/cargo-binstall` cache mount is public-binary-only
  and must not be shared by any future authenticated-source binstall
  invocation?