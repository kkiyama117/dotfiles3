# `make build` fails at Layer 3-4 (`mise install`) for `pnpm` and `go`

**Date:** 2026-07-09
**Status:** open
**Related:** [spec 21](../specifications/21-container-build-flow.md) (Layer 3-4, acceptance #14), [spec 20](../specifications/20-container-rules.md), [`dot_config/mise/config.toml`](../../dot_config/mise/config.toml), [`dot_zshenv.tmpl`](../../dot_zshenv.tmpl), [makepkg-conf issue](2026-07-09-makepkg-conf-container.md) (full build blocked by this failure), [mise-managed-languages (closed)](2026-07-01-mise-managed-languages.md)

## Context

- Containerfile Layer 3-4 copies the rendered chezmoi mise config to
  `${XDG_CONFIG_HOME}/mise/config.toml` and runs `mise install --yes` with a
  BuildKit cache mount on `~/.cache/mise`.
- [`dot_config/mise/config.toml`](../../dot_config/mise/config.toml) declares
  `go = "latest"` and `pnpm = "latest"` (among deno/python/node/julia/usage).
- [`dot_zshenv.tmpl`](../../dot_zshenv.tmpl) exports hard-coded Go paths under
  `$MISE_DATA_DIR/installs/go/latest` (`GOROOT`, `GOPATH`).
- On 2026-07-09, while validating the `makepkg.conf` Layer 1-2 change
  (`docs/issues/2026-07-09-makepkg-conf-container.md`), a full `make build`
  failed at stage `toolchain` / Layer 3-4. Layer 1-2 (including the new
  `makepkg.conf` COPY) completed successfully; the regression is in mise
  tool installation, not makepkg.

## Problem

`make build` (or `podman build --target toolchain`) fails at Layer 3-4 when
`mise install --yes` cannot finish installing **pnpm** and **go**. Other
tools in the same run (deno, node, python, julia, usage) install successfully.

Reproduced 2026-07-09 with:

```bash
podman build --target toolchain \
  --build-arg HOST_UID=1000 --build-arg HOST_GID=1000 --build-arg USERNAME=kiyama \
  --build-context deps=$PWD/dependencies \
  --build-context srcroot=$PWD \
  -t localhost/dotfiles-manjaro:toolchain-smoke \
  container/
```

### Failure 1 — `pnpm` (aqua backend, GitHub artifact attestation)

```
mise pnpm@11.10.0    [2/3] verify GitHub artifact attestations
...
mise ERROR Failed to install tools: aqua:pnpm/pnpm@latest, core:go@latest

aqua:pnpm/pnpm@latest: GitHub artifact attestations verification failed: Verification failed: Sigstore error: Verification error: TSA timestamp verification failed: Failed to verify timestamp signature: no certificate matches issuer and serial number; Sigstore error: TUF error: Failed to create cache directory: Permission denied (os error 13)
```

**Working hypothesis:** mise's Sigstore/TUF attestation cache cannot be
created or written inside the build `RUN` (permission or sandbox interaction
with the `~/.cache/mise` BuildKit cache mount and/or rootless Podman). Python
in the same run reports `✓ GitHub artifact attestations verified`, so the
failure may be pnpm/aqua-specific or timing/cert-chain specific rather than a
global network block.

### Failure 2 — `go` (core backend, post-install smoke)

```
mise go@1.26.5       [3/3] extract go1.26.5.linux-amd64.tar.gz
mise go@1.26.5       [3/3] go version
go: cannot find GOROOT directory: /home/kiyama/.local/share/mise/installs/go/latest
mise ERROR ~/.local/share/mise/installs/go/1.26.5/bin/go failed
...
core:go@latest: ~/.local/share/mise/installs/go/1.26.5/bin/go exited with non-zero status: exit code 2
```

**Working hypothesis:** Layer 3-4 `RUN` sources `/tmp/build-home/.zshenv`, which
sets `GOROOT=$MISE_DATA_DIR/installs/go/latest`. Mise installs the toolchain
under `.../go/1.26.5` and runs `go version` as a post-install check while
`GOROOT` still points at the non-existent `.../go/latest` path (no `latest`
symlink yet, or `.zshenv` should not pin `GOROOT` during build). This is
orthogonal to the pnpm attestation failure but causes the same `mise install`
step to exit non-zero.

### Ancillary warning (non-fatal in observed run)

```
mise WARN  Failed to read shorthands file: ~/.config/mise/shorthands.toml ...
```

[`dot_config/mise/config.toml`](../../dot_config/mise/config.toml) references
`shorthands_file = '~/.config/mise/shorthands.toml'`, but that file is not
rendered into the build-home tree. Treat as cleanup/low priority unless it
contributes to install failures.

## Impact

- Full image build cannot reach `aur` or `runtime` stages.
- Spec 21 acceptance **#14** (`go version; python --version; deno --version`
  after `make up`) cannot be verified end-to-end until Layer 3-4 passes.
- Downstream work blocked on a green `make build`, including closing
  [`2026-07-09-makepkg-conf-container.md`](2026-07-09-makepkg-conf-container.md)
  (makepkg Layer 1-2 smoke on the final runtime image).

## Acceptance criteria

1. `make build` (full, five stages) succeeds through Layer 3-4; build log shows
   `mise pnpm@… ✓ installed` and `mise go@… ✓ installed` (or equivalent).
2. Root cause for each failure is identified and fixed with a recorded diagnosis
   (not an undocumented workaround). Likely fix areas:
   - **pnpm:** attestation/cache permissions, aqua vs core backend settings, or
     mise config to skip/disable attestation verification in the container build
     context if that is the intended policy.
   - **go:** reconcile `dot_zshenv.tmpl` `GOROOT`/`GOPATH` (`.../go/latest`)
     with mise's versioned install layout during Layer 3-4 post-install checks
     (e.g. defer `GOROOT` export until after install, use mise-resolved paths,
     or ensure `latest` symlink exists before `go version`).
3. `podman build --target toolchain` succeeds in isolation on a cache-bust
   rebuild (touch mise config or `--no-cache` on Layer 3-4).
4. After `make up`, spec 21 acceptance #14 passes:
   `podman exec <container> zsh -ic 'go version; python --version; deno --version'`.
5. `pnpm` remains available for Layer 3-5 (`npm install -g` via
   `mise exec node@latest`) and runtime use per
   [`dot_zshenv.tmpl`](../../dot_zshenv.tmpl) `PNPM_HOME` wiring.

## Suggested first diagnostics

1. Inside a failing Layer 3-4 intermediate container (or a manual replay of the
   RUN script), run `mise install --yes --verbose` and capture full Sigstore/TUF
   paths for pnpm.
2. After `go` extract, before `go version`: `ls -la
   ~/.local/share/mise/installs/go/` and `echo $GOROOT` with and without
   sourcing `.zshenv`.
3. Test `GOROOT` unset + `mise exec go@latest -- go version` vs hard-coded
   `GOROOT=.../latest`.
4. Compare pnpm (aqua) vs python (core) attestation behavior under the same
   cache mount UID/GID (`uid=${HOST_UID},gid=${HOST_GID}`).

## Notes

- Branch observed: `migrate_old_configs` (commit `c2da9af` and later).
- This issue is **not** about the `makepkg.conf` Layer 1-2 COPY itself; base-stage
  smoke for makepkg passed on `localhost/dotfiles-manjaro:base-smoke`.
- Out of scope unless required for the fix: changing which tools are in
  `[tools]` (e.g. pinning `go` to a specific version instead of `latest`);
  prefer fixing install/verification plumbing first.
