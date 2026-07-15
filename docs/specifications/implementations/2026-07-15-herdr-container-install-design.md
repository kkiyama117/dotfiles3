# Install `herdr` during the container build (pinned prebuilt binary) — Design

**Status:** DRAFT
**Date opened:** 2026-07-15
**Issue:** [`../../issues/2026-07-15-herdr-container-install.md`](../../issues/2026-07-15-herdr-container-install.md)
**Author:** kiyama

## §1 Context & success criteria

`herdr` is a terminal workspace manager for AI coding agents
(<https://herdr.dev>). Its config (`~/.config/herdr/config.toml`,
`config.yml`) is already chezmoi-managed (`dot_config/herdr/`), but the
tool itself is declared `manager = "migrated"`, `layer = -1` in
`dependencies/packages.toml` — config retained, binary **not installed**
in the container. The entry's own comment (`# "custom" if it used`)
anticipates exactly this change.

Distribution facts (verified 2026-07-15):

- Upstream ships **prebuilt, static-pie linked, single-file binaries** per
  release on GitHub:
  `https://github.com/ogulcancelik/herdr/releases/download/v<VER>/herdr-linux-x86_64`.
  No tarball, no wrapper — the asset IS the executable (v0.7.3 =
  18,560,992 bytes; runs on the Manjaro base image with no glibc
  coupling because it is static-pie).
- The **stable** channel manifest (`https://herdr.dev/latest.json`,
  currently `0.7.3`) lists asset URLs but **no checksums**; the
  **preview** manifest (`https://herdr.dev/preview.json`) carries
  per-asset SHA256 but tracks moving preview builds.
- `herdr` is not in the Arch repos; an AUR package is not part of the
  supported upstream install matrix (official paths: direct download,
  Homebrew, Nix, mise).
- The host binary lives at `~/.local/bin/herdr`; the shared
  `dot_zshenv.tmpl` already puts `$HOME/.local/bin` on `$path`
  (line `path=($HOME/.local/bin(N-/) $path)`), identically at build time
  (Stage 2 render) and runtime.
- v0.7.3 `herdr-linux-x86_64` SHA256 (computed from the downloaded
  asset; `herdr --version` of that artifact prints `herdr 0.7.3`):
  `043ef43ecbabda28465dcff1eec3184518150d567b8b8f20cda9c6c88770641d`.

The repo already has the exact pattern this needs: `cargo-binstall`
(Containerfile Layer 3-6) is curl-bootstrapped from a **version-pinned +
SHA256-gated** prebuilt artifact in the `toolchain` stage. `herdr`
follows that mechanism — with one contract difference: `cargo-binstall`
is installer infra (spec 20 I-INFRA1, NOT in `packages.toml`), while
`herdr` is a **user-facing tool** and therefore MUST be declared in
`packages.toml` (spec 20 I5) as a `manager = "custom"` doc-only entry,
the same declaration class as `pi-coding-agent` and `paru`.

Success criteria (mirror the issue's acceptance, labeled for review
cross-reference):

- **S1** `dependencies/packages.toml`: the `herdr` entry flips from
  `manager = "migrated"` / `layer = -1` to `manager = "custom"` /
  `layer = 3` (`has_configs = true` unchanged); `make gen-deps`
  regenerates the spec 02 AUTO-GEN block (herdr moves from the
  Layer -1 table to the Layer 3 table). No `layer_<N>/*.txt` install
  list changes — `custom` is doc-only (spec 20 I5 satisfied via the
  declaration, like `pi-coding-agent`).
- **S2** Containerfile `toolchain` stage gains **Layer 3-8**:
  `ARG HERDR_VERSION=0.7.3` + `ARG HERDR_SHA256=043ef43e…770641d`;
  `curl` the pinned `herdr-linux-x86_64` release asset, verify with
  `sha256sum -c` **before** install, then `install -D -m 0755` to
  `/home/${USERNAME}/.local/bin/herdr`, and sanity-check
  `herdr --version`. Runs as non-root `${USERNAME}` (spec 20 I7).
- **S3** After `make build`, the image carries
  `~/.local/bin/herdr`, `0755`, `${USERNAME}`-owned; after `make up`,
  `podman exec <c> zsh -ic 'herdr --version'` prints `herdr 0.7.3`.
- **S4** No PATH edits: `~/.local/bin` is already on `$path` via
  `dot_zshenv.tmpl` (no `.zshenv` / Makefile / volume changes).
- **S5** No herdr runtime state is baked: the build never starts a herdr
  server; no sockets / logs / `session.json` / release-note cache under
  `~/.config/herdr` enter any image layer. The image stays secret-free
  (spec 20 I4 unaffected — herdr carries no credentials).
- **S6** A SHA256 mismatch (or missing asset) fails the build **loudly**
  at Layer 3-8 (reproducibility gate; identical failure mode to
  Layer 3-6 cargo-binstall).
- **S7** Specs updated: spec 02 AUTO-GEN (via `make gen-deps`, no
  hand-edit); spec 20 gains I-HERDR1..I-HERDR3; spec 21 gains the
  Layer 3-8 stage-table row, a note, and an acceptance criterion.
- **S8** Config management is untouched: `dot_config/herdr/` continues to
  be applied by the runtime `chezmoi apply` (entrypoint); the managed
  `onboarding = false` suppresses first-run onboarding in the container.

## §2 Alternatives considered

- **A — stable channel, hardcoded version + SHA256 (CHOSEN).** Pin
  `HERDR_VERSION=0.7.3` and a literal SHA256 as `ARG`s, exactly like
  `CARGO_BINSTALL_VERSION` / `CARGO_BINSTALL_SHA256` (Layer 3-6).
  Reproducible: the same Containerfile always produces the same binary
  or fails loudly. Version bumps are a two-line `ARG` edit. The stable
  manifest not shipping checksums is irrelevant — the SHA is computed
  once at pin time and hardcoded, which is precisely the cargo-binstall
  precedent (upstream ships sigstore `.sig`, not `.sha256sum`; a literal
  SHA was chosen there as "the simplest reproducible integrity gate").
- **B — preview channel + manifest SHA256.** `preview.json` carries
  per-asset SHA256, so the checksum could be fetched at build time.
  Rejected: fetching both URL and checksum from the same mutable
  endpoint at build time authenticates nothing (a compromised or
  updated manifest changes both), makes builds **non-reproducible**
  (preview builds churn ~daily), and couples the build to a manifest
  schema that upstream marks `schema_version = 1` (can change). The
  host's `channel = "preview"` preference is a *runtime update-channel*
  choice, not a build-pin requirement; a container user can still
  `herdr update` / `herdr channel set preview` in a running container.
- **C — AUR / paru (Layer 4).** No maintained AUR package in upstream's
  supported matrix; packaging a -bin PKGBUILD ourselves adds a moving
  part for zero benefit over the direct pinned download. Revisit only
  if upstream starts publishing an AUR package.
- **D — mise-managed install.** Upstream mentions mise
  (`mise upgrade herdr`; self-update disables itself under mise
  installs). Rejected: this repo scopes `dot_config/mise/config.toml`
  to **language runtimes** (spec 02: "New global mise-managed tool
  versions belong in `dot_config/mise/config.toml`" — currently
  node/go/python/deno), and a mise/aqua registry hop gives weaker,
  less explicit pinning than a literal SHA256 in the Containerfile.
- **E — install at runtime (entrypoint / `herdr update` on first
  start).** Rejected: network dependency on every container start,
  unpinned artifact, violates the "image is complete after
  `make build`" property every other tool follows.
- **F — declare as I-INFRA1 infra (out of `packages.toml`).** Rejected:
  I-INFRA1 is a carve-out for installer-of-installers (`rustup`,
  `cargo-binstall`). `herdr` is an end-user tool, so spec 20 I5
  requires a `packages.toml` declaration; `manager = "custom"` is the
  established class for bespoke install paths (`paru`,
  `pi-coding-agent`).

## §3 Architecture / Invariants

- **I-HERDR1** — `herdr` is a `manager = "custom"`, `layer = 3`
  `packages.toml` entry (doc-only; appears in the spec 02 AUTO-GEN
  block, never in a generated install list). Its sole install path is
  Containerfile Layer 3-8: a **version-pinned + SHA256-gated** prebuilt
  `herdr-linux-x86_64` release asset from GitHub, verified with
  `sha256sum -c` before install. This is the cargo-binstall integrity
  mechanism applied to a user-facing tool (declared under I5, not
  carved out under I-INFRA1).
- **I-HERDR2** — Install destination is
  `/home/${USERNAME}/.local/bin/herdr` (`0755`,
  `${USERNAME}`-owned), on PATH via the shared `.zshenv`. `~/.local/bin`
  is **image content, not a volume mountpoint** — the binary survives
  `make down && make up` because it is baked, not because it is
  persisted. Consequence: a runtime self-update (`herdr update`)
  rewrites the binary only in the container overlay and is **lost on
  container replacement**; the supported version-bump path is editing
  `HERDR_VERSION` / `HERDR_SHA256` in the Containerfile and re-running
  `make build`.
- **I-HERDR3** — No herdr runtime state in the image. The build never
  launches a herdr server or client; `~/.config/herdr` state (sockets,
  logs, `session.json`, `sessions/`, release-note cache) is created at
  runtime only. Config files under `~/.config/herdr/` are chezmoi's
  domain (runtime `chezmoi apply`, `dot_config/herdr/`), never baked by
  Layer 3-8. Extends the spec 20 I4 secret-free property trivially
  (herdr ships no credentials).
- Non-root discipline holds (spec 20 I7): Layer 3-8 runs as
  `${USERNAME}` (the `toolchain` stage default), writing into its own
  home; no sudo, no root escalation.
- Chezmoi coexistence: chezmoi manages `dot_local/bin/*` files it
  declares; `~/.local/bin/herdr` is unmanaged and `chezmoi apply
  --force` never removes unmanaged files (no `.chezmoiignore` change
  needed).

## §4 Scope / staging breakdown

Four mechanical change areas, each independently reviewable:

1. **`dependencies/packages.toml`** — flip the existing `herdr` entry:

   ```toml
   [[tool]]
   name = "herdr"
   manager = "custom"
   layer = 3
   # `~/.config/herdr`; installed by Containerfile Layer 3-8 (pinned prebuilt
   # binary, SHA256-gated) — custom install path, not in any generated list
   has_configs = true
   description = "terminal workspace manager for AI coding agents; pinned prebuilt binary to ~/.local/bin (custom install path)"
   ```

   Then `make gen-deps` regenerates the spec 02 AUTO-GEN block (herdr
   leaves the Layer -1 `migrated` table, appears in the Layer 3 table
   as `custom`). No generated `layer_<N>/*.txt` changes.

2. **`container/Containerfile`** — add Layer 3-8 at the end of the
   `toolchain` stage (after Layer 3-7 cargo tools, before the `aur`
   stage) so the new layer invalidates nothing upstream of it.

3. **Spec sync** —
   - spec 02: AUTO-GEN block refreshed by `make gen-deps` (no
     hand-edit).
   - spec 20: add I-HERDR1..I-HERDR3 (this design §3) under the Build
     invariants.
   - spec 21: add the Layer 3-8 row to the stage table; add a note in
     "Notes on the current state" (binary is baked image content, not
     volume-persisted; self-update writes are ephemeral); add an
     acceptance criterion (`herdr --version` after `make up`; SHA gate
     fails loudly on mismatch).

4. **Issue / plan cross-links** — issue
   `docs/issues/2026-07-15-herdr-container-install.md`, plan
   `docs/plans/2026-07-15-herdr-container-install-impl.md`, this design.

Explicit non-changes: no `Makefile` edit (no new volume, no new build
arg wiring — `ARG` defaults live in the Containerfile like
`CARGO_BINSTALL_VERSION`), no `.chezmoiignore` edit, no
`dot_zshenv.tmpl` edit (PATH already correct), no entrypoint edit, no
`dot_config/herdr/` edit.

## §5 Implementation detail

### §5.1 Containerfile Layer 3-8

```dockerfile
# Layer 3-8: Install herdr (pinned prebuilt binary — packages.toml `custom`).
#
# herdr is a user-facing terminal workspace manager distributed as a
# single-file static-pie binary per GitHub release (no tarball). Same
# integrity gate as cargo-binstall (Layer 3-6): pin version + verify a
# hardcoded SHA256 before install (I-HERDR1). Installed to
# ~/.local/bin/herdr (already on PATH via .zshenv; I-HERDR2). Declared
# in packages.toml as manager="custom", layer=3 (doc-only entry, spec 20
# I5) — NOT I-INFRA1 infra, because herdr is not an installer.
# No cache mount: single small artifact (~18 MB), re-fetched only when
# the ARGs change. Runs as ${USERNAME}; no root needed.
ARG HERDR_VERSION=0.7.3
ARG HERDR_SHA256=043ef43ecbabda28465dcff1eec3184518150d567b8b8f20cda9c6c88770641d
RUN zsh -c 'set -eo pipefail; \
      curl -L --proto "=https" --tlsv1.2 -sSf -o /tmp/herdr \
        https://github.com/ogulcancelik/herdr/releases/download/v${HERDR_VERSION}/herdr-linux-x86_64; \
      printf "%s  /tmp/herdr\n" "${HERDR_SHA256}" | sha256sum -c -; \
      install -D -m 0755 /tmp/herdr "$HOME/.local/bin/herdr"; \
      rm -f /tmp/herdr; \
      "$HOME/.local/bin/herdr" --version; \
    '
```

Notes:

- The release asset is the bare executable — no archive extraction, so
  none of the tar single-file / PATH-traversal guards Layer 3-6 needs.
- The `--version` sanity check invokes the binary by absolute path (the
  RUN shell does not need `.zshenv` sourcing; the destination is a
  literal `$HOME` path, unlike the `$CARGO_HOME`-relative Layer 3-6).
  `herdr --version` is a pure client-side print — it does not spawn a
  server or create `~/.config/herdr` state (verified on the downloaded
  artifact).
- `install -D` creates `~/.local/bin` owner-correct as a side effect
  (Layer 1-5 provisions `~/.local` but not `~/.local/bin`); running as
  `${USERNAME}` under the `0755` `~/.local` parent, no root needed.
- x86_64 is hardcoded, matching the Layer 3-6 precedent
  (`cargo-binstall-x86_64-…`); the image is x86_64-only today.

### §5.2 Version-bump procedure (documented in spec 21 note)

1. Pick the target version from `https://herdr.dev/latest.json`.
2. Download `herdr-linux-x86_64` for that tag; compute `sha256sum`.
3. Edit the two `ARG` lines; `make build`.
4. A wrong/stale SHA fails at `sha256sum -c` (S6) — never silently
   installs a different artifact.

### §5.3 Verification

- `make gen-deps` idempotent; spec 02 AUTO-GEN shows `herdr` under
  Layer 3 (`custom`), no longer under Layer -1; generator tests pass.
- `make build` green; `podman build --target toolchain` in isolation
  has `~/.local/bin/herdr` (`stat -c '%a %U:%G'` → `755
  <USERNAME>:<group>`).
- After `make up`: `podman exec <c> zsh -ic 'herdr --version'` →
  `herdr 0.7.3`; `podman exec <c> zsh -ic 'which herdr'` →
  `/home/<USERNAME>/.local/bin/herdr`.
- Negative test: flip one hex digit of `HERDR_SHA256`, rebuild with
  `--no-cache` on that layer → build fails at `sha256sum -c` (S6).
- State check: in the `--target toolchain` image, `~/.config/herdr`
  does not exist (S5; config arrives only via runtime `chezmoi apply`).
- `make down && make up` → `herdr --version` still works (baked image
  content; no volume involved).

## §6 Risks / edge cases

- **Self-update drift (accepted, documented).** The chezmoi-managed
  `config.toml` sets `channel = "preview"` and leaves
  `version_check = true`, so an in-container herdr may surface update
  prompts and `herdr update` can overwrite the binary in the container
  overlay. That copy dies with the container (`make up --replace`);
  the image pin is the source of truth (I-HERDR2). If prompts prove
  noisy, a follow-up can gate `[update] version_check = false` for
  `runtime = "container"` via the existing `DOTFILES_RUNTIME` template
  signal (spec 20 I-GIT7 pattern) — out of scope here.
- **Upstream re-tags / deletes a release asset.** `sha256sum -c` fails
  the build loudly (desired). Recovery: re-pin to a live version.
- **Stable manifest lag.** `latest.json` moving to 0.7.4+ does not
  affect builds (nothing reads the manifest at build time) — that is
  the point of Option A.
- **Preview-channel host vs stable-pinned container.** Host (0.7.1
  preview lineage) and container (0.7.3 stable) versions differ;
  herdr's client/server protocol matters only within one machine's
  session, and `herdr --remote` bridges install matching binaries
  themselves. No cross-contamination: host and container have separate
  homes/sockets.
- **Layer size.** +18 MB image layer; negligible against the existing
  toolchain layers.
- **aarch64.** Not supported by this pin (asset name hardcoded). If the
  image ever goes multi-arch, lift the asset name + SHA into per-arch
  ARGs (same treatment cargo-binstall would need).

## §7 Open questions

- **Q1 (update-prompt suppression in container)** — Deferred. If
  `version_check = true` proves noisy inside the container, gate it off
  for `runtime = "container"` via `DOTFILES_RUNTIME` templating of
  `dot_config/herdr/config.toml` (would keep host behavior unchanged).
  Not required for this change.
- **Q2 (preview channel in the container)** — Deferred / non-blocking.
  A container user can run `herdr update` / `herdr channel set preview`
  at runtime; the change is ephemeral by I-HERDR2. No build-time
  preview support is planned (see §2 Option B rejection).
