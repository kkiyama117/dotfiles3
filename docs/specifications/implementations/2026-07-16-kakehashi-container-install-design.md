# Install `kakehashi` during the container build — Design

**Status:** Approved
**Date opened:** 2026-07-16
**Issue:** [`../../issues/2026-07-16-kakehashi-container-install.md`](../../issues/2026-07-16-kakehashi-container-install.md)
**Author:** kiyama
**Review required:** letters A + B + C + D + E (spec 09 §2.2)

## §1 Context & success criteria

[`kakehashi`](https://github.com/atusy/kakehashi) is a language-server bridge
distributed through GitHub releases. Distribution facts verified on
2026-07-16:

- The latest stable release is v0.8.0.
- The x86_64 GNU/Linux asset is named
  `kakehashi-v0.8.0-x86_64-unknown-linux-gnu.tar.gz`.
- The tar archive contains exactly one top-level member named `kakehashi`.
- The extracted executable reports `kakehashi 0.8.0` for
  `kakehashi --version`.
- Upstream publishes no checksum file with the release. GitHub's release API
  exposes an asset digest, but fetching the expected value from the same
  mutable release source is not an independent reproducibility or
  authenticity anchor.
- Neither `mise registry` nor an aqua-registry code search returned a
  `kakehashi` package on 2026-07-16. Upstream's installation guidance says to
  download the platform binary and place it on `PATH`.

The repository's build-time tool convention and runtime contract make the
Containerfile `toolchain` stage the appropriate lifecycle. The entrypoint
applies runtime configuration and emits readiness; it must not introduce a
network-dependent binary install. `dot_zshenv.tmpl` already puts
`$HOME/.local/bin` on `PATH`.

Success criteria:

- **S1** — `kakehashi` is declared in `dependencies/packages.toml` as a
  user-facing `manager = "custom"`, `layer = 3` tool. `make gen-deps` places
  it in the generated spec 02 Layer 3 inventory without creating a generated
  manager install-list entry.
- **S2** — A new final `toolchain` sub-layer resolves the latest stable release
  tag, downloads the x86_64 GNU/Linux archive, verifies that its only member is
  a regular, non-symlink file named `kakehashi`, and installs it as
  `/home/${USERNAME}/.local/bin/kakehashi` with mode `0755`.
- **S3** — The install runs as `${USERNAME}` and fails loudly on redirect,
  tag-validation, download, archive-shape, extraction, install, or
  `kakehashi --version` failure.
- **S4** — After `make build` and `make up`, `command -v kakehashi` resolves to
  the requested `~/.local/bin` path and `kakehashi --version` exits zero.
- **S5** — Normal image-layer caching remains enabled. "Latest" means latest
  when the install layer executes, not latest at container start or at every
  cached build. Operators use the documented full no-cache build command when
  they require an immediate refresh.
- **S6** — No Makefile, PATH, volume, secret, chezmoi template, or entrypoint
  behavior changes.
- **S7** — Specs 02, 20, and 21 and focused static tests record and enforce the
  install lifecycle and policy.

## §2 Alternatives considered

- **A — Inline Containerfile latest-release install (CHOSEN).** Discover the
  stable tag from GitHub's `releases/latest` redirect, construct the
  versioned x86_64 asset URL, validate and extract the single-file archive,
  and install to `~/.local/bin`. This is the smallest change, keeps the binary
  in the image, and has no startup network dependency.
- **B — Dedicated installer script copied into the image.** This gives the
  release-resolution logic an isolated shell-test surface, but adds a
  maintained file and copy layer for a short, single-consumer operation.
  The inline form follows the existing `cargo-binstall` bootstrap convention;
  its static tests are regression guards, while `make build` is the functional
  acceptance gate. A script becomes preferable if the logic gains
  multi-architecture, multiple channels, or enough branches to warrant
  executable unit fixtures.
- **C — Build from source with Cargo.** This avoids release-archive discovery
  but increases build time and dependency traffic and does not install the
  upstream-published binary requested here.
- **D — Entrypoint install.** This can refresh on each new container, but makes
  startup and readiness depend on GitHub availability and repeats work across
  container replacements. It conflicts with the current entrypoint boundary.
- **E — Mise/aqua install.** This would match the repository's current
  [`herdr` management pattern](2026-07-15-herdr-mise-management-design.md),
  which deliberately retired a bespoke `~/.local/bin` installer. Unlike
  `herdr`, however, `kakehashi` was not found in mise or aqua registry searches
  on 2026-07-16, and the user explicitly selected the literal
  `~/.local/bin/kakehashi` destination after being offered the mise-shim
  alternative. The divergence is therefore intentional rather than a new
  general preference over mise.
- **F — Pinned version and SHA-256.** This best matches the reproducible
  `cargo-binstall` bootstrap, but the user explicitly selected an unpinned
  latest-release policy. Revisit if deterministic builds become more important
  than automatic resolution when the layer rebuilds.

## §3 Architecture / Invariants

- **I-KAKEHASHI1 — Build-time ownership.** `kakehashi` is a Layer 3 custom
  user tool. Its sole install authority is the Containerfile `toolchain`
  stage; the entrypoint and runtime `chezmoi apply` never install or update it.
- **I-KAKEHASHI2 — Requested path.** The image contains
  `/home/${USERNAME}/.local/bin/kakehashi`, mode `0755`, owned by
  `${USERNAME}`. In the `toolchain` stage, `$HOME` is
  `/home/${USERNAME}`; the install command uses
  `$HOME/.local/bin/kakehashi`, and `install -D` creates the parent directory
  if absent. No PATH edit is needed.
- **I-KAKEHASHI3 — Latest with ordinary caching.** The layer resolves
  `https://github.com/atusy/kakehashi/releases/latest` only when the container
  builder executes that layer. Cached builds may retain an older resolved
  release; a no-cache rebuild is the explicit refresh mechanism.
- **I-KAKEHASHI4 — Narrow platform and archive shape.** Only
  `x86_64-unknown-linux-gnu` is supported, matching the repository's existing
  x86_64-specific `cargo-binstall` bootstrap; the GNU asset matches the
  Manjaro base image's glibc runtime. The build accepts exactly one tar member
  named `kakehashi`, and the extracted member must be a regular file and not a
  symlink. Additional members, alternate paths, and non-regular members fail
  before installation.
- **I-KAKEHASHI5 — Integrity boundary.** HTTPS is required for the latest
  redirect and asset download, and redirects may only continue over HTTPS.
  The asset URL uses a hardcoded
  `https://github.com/atusy/kakehashi/releases/download/` base; only the
  validated tag token comes from the effective latest-release URL.
  Because no expected digest is pinned independently in the repository, this
  policy is non-reproducible and trusts GitHub/upstream release control. The
  archive-shape check and version execution detect malformed or incompatible
  artifacts but are not substitutes for a pinned cryptographic identity.
- **I-KAKEHASHI6 — No baked runtime state.** The build invokes only
  `kakehashi --version`; it does not start bridge services or create user
  configuration. No secret is read or written.

## §4 Scope / staging breakdown

1. Create the parent issue and this design under the repository document
   lifecycle.
2. Add `kakehashi` alongside the other custom Layer 3 entries in
   `dependencies/packages.toml`.
3. Run `make gen-deps`; commit generated inventory changes rather than editing
   spec 02's AUTO-GEN block manually.
4. Add Layer 3-8 in `container/Containerfile` after the existing Layer 3-7
   cargo-tool install and before `FROM toolchain AS aur`.
5. Add focused static tests to the existing container/dependency test suites.
6. Synchronize spec 20 invariants and spec 21's Layer 3-8 row, notes, and new
   acceptance criterion #26.

Explicit non-changes: `Makefile`, `dot_zshenv.tmpl`, mise configuration,
entrypoint, named volumes, secret-management files, and chezmoi templates.

## §5 Implementation detail

### §5.1 Release resolution

The build step follows GitHub's stable latest-release redirect and captures
the effective URL with curl's `%{url_effective}` output rather than parsing
HTML. It takes only the final path component and validates it as a whole,
single-line value. In zsh, the concrete fail-closed check is equivalent to
`[[ $tag == v<->.<->.<-> ]] || exit 1`; this avoids quoted-regex ambiguity and
rejects empty, malformed, prerelease, and unexpected redirect results.

The selected asset name is:

```text
https://github.com/atusy/kakehashi/releases/download/${tag}/kakehashi-${tag}-x86_64-unknown-linux-gnu.tar.gz
```

The URL base above is a hardcoded literal. Neither its host, scheme, nor path
prefix is derived from the latest-release redirect. Both requests use
`curl --proto '=https' --proto-redir '=https' --tlsv1.2` with
fail/silent/show-error and redirect handling under
`set -eo pipefail`.

The layer creates a private staging directory with `mktemp -d`, puts the
archive inside it, and registers cleanup for shell exit so both archive and
extraction state are removed on success or failure. It does not use a
predictable shared `/tmp/kakehashi*` path.

### §5.2 Extraction and installation

Before extraction, two name checks must both pass:

1. `tar -tzf` reports exactly one archive member.
2. That member is exactly `kakehashi`, with no directory prefix or traversal.

The archive is then extracted inside the private staging directory with
ownership and archive permissions ignored. Before installation,
`[ -f "$staging/kakehashi" ] && [ ! -L "$staging/kakehashi" ]` must pass, so
a symlink, hardlink-to-missing-target, directory, device, or FIFO is rejected.
The layer installs the file with `install -D -m 0755` to
`$HOME/.local/bin/kakehashi`, invokes that absolute path with `--version`, and
removes staging state through the exit cleanup. Strict error and pipe-failure
handling makes every failed check fail the image build.

### §5.3 Dependency inventory and specs

`dependencies/packages.toml` remains the hand-edited source of truth:

```toml
[[tool]]
name = "kakehashi"
manager = "custom"
layer = 3
has_configs = false
description = "language-server bridge; latest x86_64 release binary installed to ~/.local/bin during the container build"
```

The entry is placed with the custom Layer 3 tools rather than relying on the
currently non-alphabetical order of that section. `make gen-deps` updates spec
02. Spec 20 gains I-KAKEHASHI1 through I-KAKEHASHI6 (or equivalent normative
wording), and spec 21 gains the Layer 3-8 row and acceptance criterion #26.

### §5.4 Verification

- Generator: `make gen-deps` is idempotent and `make test-deps` passes.
- Static container contract: `make test-container` checks the custom Layer 3
  inventory entry, hardcoded download base, latest-release resolution,
  HTTPS-only curl policy, x86_64 asset suffix, exact tar-member and
  regular-file validation, private staging and cleanup, destination, version
  check, and absence from the entrypoint.
- Coverage boundary: static tests are regression guards for Containerfile
  structure. They do not execute GitHub redirects or adversarial tar fixtures;
  the uncached `make build` below is the functional acceptance gate.
- Build: `make build` completes with the new layer.
- Runtime: after `make up`,
  `podman exec dotfiles-manjaro zsh -ic 'command -v kakehashi; kakehashi
  --version'` resolves the requested path and exits zero.
- Ownership: `stat -c '%a %U:%G' ~/.local/bin/kakehashi` reports mode `755`
  and the configured non-root user/group.
- Cache policy: ordinary `make build` may reuse the layer. To force release
  re-resolution, run the following from the repository root after loading the
  configured username. This is intentionally a full rebuild because Podman
  has no per-layer no-cache selector and the Makefile has no flag
  pass-through:

  ```zsh
  set -a
  source ./.env
  set +a
  podman build --no-cache --jobs "${JOBS:-1}" \
    --build-arg HOST_UID="$(id -u)" \
    --build-arg HOST_GID="$(id -g)" \
    --build-arg USERNAME="$USERNAME" \
    --build-context deps="$PWD/dependencies" \
    --build-context srcroot="$PWD" \
    -t localhost/dotfiles-manjaro:latest \
    "$PWD/container"
  ```

  No automatic cache-bust argument or Makefile target is added.

## §6 Error handling and rollback

Release lookup, malformed tag, missing asset, non-HTTPS redirect, changed
archive layout or type, extraction, install, or executable failure stops the
build. Exit cleanup removes the private staging directory even on failure. No
partial runtime state exists because installation happens while creating an
image layer.

Rollback removes the custom inventory entry, regenerates dependencies, removes
the Containerfile sub-layer and focused tests, and reverts the synchronized
spec 20/21 text. Existing images remain usable until explicitly rebuilt or
removed.

## §7 Risks / edge cases

- **Moving latest release.** The same repository revision can produce
  different binaries when the layer executes at different times. This is an
  accepted consequence of the selected policy.
- **Cache staleness.** An ordinary cached build can keep an older binary.
  This is intentional; "latest" describes intent at layer execution, not a
  live guarantee. Use the documented full no-cache rebuild to force refresh.
- **No independent digest pin.** HTTPS and GitHub release control are the
  supply-chain trust boundary. A compromised upstream release can pass archive
  and version checks. Mitigation requires changing policy to a reviewed,
  repository-pinned version and digest.
- **GitHub availability and redirects.** The layer requires network access
  when uncached and fails closed if the redirect or asset is unavailable.
- **Future multi-architecture images.** aarch64 requires an explicit asset
  mapping and tests; silently selecting by host architecture is out of scope.
- **Upstream naming changes.** A changed asset name or archive layout fails the
  build rather than guessing.

## §8 Open questions

- **Q1 (resolved — lifecycle):** Build-time installation was selected over
  entrypoint installation.
- **Q2 (resolved — version policy):** Resolve the latest stable release when
  the layer executes; do not pin a version.
- **Q3 (resolved — caching):** Preserve ordinary layer caching; do not force a
  refresh on every `make build`.
- **Q4 (resolved — architecture):** Support x86_64 GNU/Linux only.
- **Q5 (resolved — accepted risk):** The pass-1 security review accepts the
  explicitly disclosed moving-release trust boundary under the user's chosen
  policy. If that policy changes, a new reviewed design must pin a version and
  SHA-256 before implementation.

## §9 Review pass-1 responses

The aggregate review is
[`2026-07-16-kakehashi-container-install-review-pass1.md`](../../reviews/2026-07-16-kakehashi-container-install-review-pass1.md).

- **A-F1:** addressed — §3 and §5.2 now state the `$HOME` /
  `/home/${USERNAME}` equivalence and use one install-command path.
- **A-F2:** addressed — §4 and §5.3 now specify grouped custom-tool placement,
  not alphabetical placement.
- **A-F3:** RESOLVED — the v0.8.0 archive was directly verified as one regular
  executable member named `kakehashi`.
- **B-F1:** addressed — §5.1 hardcodes the asset URL base and interpolates only
  the validated tag.
- **B-F2:** addressed — I-KAKEHASHI4 and §5.2 require a regular, non-symlink
  member.
- **B-F3:** addressed — §5.1 and §5.2 require private staging and exit cleanup.
- **B-F4:** addressed — §5.1 specifies fail-closed effective-URL capture and
  whole-value zsh tag validation.
- **C-F1:** RESOLVED — §1 and §2 record registry evidence, link the `herdr`
  precedent, and explain the explicit user-selected divergence.
- **C-F2:** addressed — §2 and §5.4 state the inline testability boundary and
  functional build gate.
- **C-F3:** addressed — §4 and §5.3 assign Layer 3-8 and acceptance #26.
- **C-F4:** addressed — S5, I-KAKEHASHI3, and §5.4 distinguish latest-at-build
  from live latest and document refresh cost.
- **D-F1:** addressed — §2 links and reconciles the `herdr` mise design.
- **D-F2:** addressed — Layer 3-8 reuse is explicit.
- **D-F3:** addressed — the header lists required letters.
- **D-F4:** addressed — §3 matches the spec 00 heading.
- **E-F1:** addressed — §5.4 gives the exact full no-cache build.
- **E-F2:** addressed — staging cleanup is required on every exit.
- **E-F3:** addressed — inventory checks and static/functional coverage roles
  are explicit.
- **E-F4:** addressed — §5.1 gives a tested zsh-safe tag check.

This design changes container build flow and performs a network download, so
the required review set is letters A, B, C, D, and E under spec 09 §2.2.
