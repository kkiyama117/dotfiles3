# Apptainer remote support — Design

**Status:** DRAFT
**Date opened:** 2026-08-08
**Issue:** [Apptainer remote support (HPC login node)](../../issues/2026-08-08-apptainer-remote.md)
**Author:** kiyama
**Review required:** letter A (spec 09 §2.2, ordinary design)

## §1 Context & success criteria

The container is built and run with Podman (spec 20/21). A remote HPC login
node (accessed via `ssh sp`) has only Apptainer. Apptainer runs OCI images
directly (`apptainer run docker://...` / `apptainer pull docker://...` →
SIF), so the existing image is reusable without rewriting the Containerfile.
The remote is x86_64, has internet access, and is rootless.

- **S1:** GitHub Actions builds the existing Containerfile unchanged and
  pushes a public GHCR package that the remote can pull anonymously.
- **S2:** A wrapper script in the repo starts an interactive zsh on the
  remote: `apptainer run` runs the existing entrypoint (`chezmoi apply` +
  Bitwarden auth from `/run/secrets`) and then `exec zsh -l`.
- **S3:** The remote home is used directly as `$HOME`; the five Podman
  named volumes are replaced by binds of the remote home's XDG directories
  (`~/.local/share/{cargo,rustup,mise,gnupg}`, `~/.ssh`).
- **S4:** Bitwarden credentials are provided as files bound to
  `/run/secrets` (podman-secrets equivalent).
- **S5:** Local Makefile / Containerfile / entrypoint are unchanged.
- **S6:** The remote contract is documented in a new spec
  (`26-apptainer-remote.md`).

## §2 Alternatives considered

### A1 — OCI build in GitHub Actions → GHCR (selected)

`docker/build-push-action` (BuildKit) builds the existing Containerfile
with named build contexts (`deps`, `srcroot`) and `--mount=type=cache`
persisted via the `gha` cache backend. The remote pulls with
`apptainer pull docker://ghcr.io/...`. No build-logic duplication; the
image is byte-identical in spirit to the local `make build` output.

### A2 — SIF build in GitHub Actions with Apptainer (rejected)

Apptainer's Dockerfile support does not implement multi-stage builds,
`--mount=type=cache`, or named build contexts — this Containerfile cannot
be built by Apptainer. A separate `.def` file would duplicate the build
logic (packages, layers, prepass) and drift from `packages.toml`.

### A3 — Local build + manual transfer (rejected)

`make build` locally and copy the image to the remote (e.g. `podman save`
+ scp + `apptainer import`). No CI, no freshness guarantee, manual
rollout; rejected in favor of A1.

### A4 — Persistent instance model (`apptainer instance start`) (rejected)

Closer to the local `make up` / `make exec` model, but leaves a resident
process on the login node and requires instance restarts to pick up
dotfile changes. The ephemeral `apptainer run` model (selected) re-applies
chezmoi on every shell, is stateless, and needs no cleanup.

## §3 Architecture / invariants

- **I1:** The Containerfile is not modified. The GH Actions build passes
  the same named contexts as the Makefile: `deps=./dependencies`,
  `srcroot=.` (repo root, filtered by `.containerignore`).
- **I2:** CI build args are fixed: `HOST_UID=1000`, `HOST_GID=1000`,
  `USERNAME=kiyama`. Apptainer runs the container as the invoking user and
  mounts the invoking user's home, so the baked uid/gid/username are
  irrelevant at runtime on the remote. `USERNAME=kiyama` is the canonical
  value the wrapper references for the baked kakehashi path (I6).
- **I3:** The GHCR package is public (one-time manual visibility setting),
  enabling anonymous `apptainer pull`.
- **I4:** The wrapper requires the secrets directory
  (`~/.config/dotfiles-secrets/{bw_clientid,bw_clientsecret,bw_password}`,
  mode 600) and exits with a message if any file is missing. Without
  `BW_SESSION`, `private_secrets.zsh.tmpl`'s `bitwarden*` template
  functions fail and `chezmoi apply` cannot succeed (choice A: Bitwarden
  is used on the remote).
- **I5:** `XDG_RUNTIME_DIR` is overridden to `$HOME/.run` (created by the
  wrapper). `dot_zshenv.tmpl` uses `${XDG_RUNTIME_DIR:-/run/user/$UID}`, so
  the preset env var wins; Apptainer's `/run` is a root-owned tmpfs and
  cannot host `/run/user/<uid>`.
- **I6:** The baked kakehashi binary (`/home/kiyama/.local/bin/kakehashi`)
  is hidden by the home mount. The wrapper copies it out once into
  `$HOME/.local/bin/kakehashi` via `apptainer exec` (a bind cannot source
  from inside the image). If the copy fails, the wrapper continues with a
  warning (kakehashi is optional on the remote).
- **I7:** The entrypoint is unchanged. It already reads `/run/secrets/*`,
  uses `${HOME}` for the chezmoi source, and `exec "$@"` — so
  `apptainer run <sif> zsh -l` works as-is. The readiness sentinel
  (`/tmp/chezmoi-applied`) and `make up` polling are podman-only and not
  used on the remote (foreground run).
- **I8:** The wrapper detects `apptainer` or `singularity` (legacy name)
  and uses whichever exists.
- **I9:** The remote's native (non-container) shell also sees the applied
  dotfiles (choice A side effect). If the native login shell is zsh, it
  will source the same configs; tools not installed on the host (sheldon,
  starship, mise) degrade via the existing `(N-/)` PATH globs and
  `mise activate` failure is a known cosmetic risk. The container shell is
  the supported shell.

## §4 Components

### 4.1 `.github/workflows/build-image.yml` (new)

- Trigger: push to `main` (paths: `container/**`, `dependencies/**`,
  `.github/workflows/build-image.yml`, `.chezmoi*`, `dot_zshenv.tmpl`) +
  `workflow_dispatch`.
- Permissions: `contents: read`, `packages: write`.
- Steps: checkout → `docker/setup-buildx-action` →
  `docker/login-action` (GHCR) → `docker/build-push-action` with:
  - `context: ./container`, `file: container/Containerfile`
  - `build-contexts: deps=./dependencies, srcroot=.`
  - `build-args: HOST_UID=1000, HOST_GID=1000, USERNAME=kiyama`
  - `tags: ghcr.io/kkiyama117/dotfiles-manjaro:latest, ghcr.io/kkiyama117/dotfiles-manjaro:<sha>`
  - `cache-from: type=gha`, `cache-to: type=gha,mode=max`
  - `push: true`
- No secrets needed (I4 in spec 20: the build is secret-free).

### 4.2 `scripts/apptainer-run.sh` (new)

Bash script in the repo root `scripts/` (not chezmoi-managed; on the remote
it lives at `~/.local/share/chezmoi/scripts/apptainer-run.sh`). Flow:

1. Detect `apptainer` / `singularity`; fail with a message if neither.
2. Pull: if the SIF file is missing (or `--update` is given), run
   `apptainer pull docker://ghcr.io/kkiyama117/dotfiles-manjaro:latest`
   into `~/.apptainer/`.
3. Clone: if `~/.local/share/chezmoi/.git` is missing, `git clone
   https://github.com/kkiyama117/dotfiles3.git ~/.local/share/chezmoi`
   (public repo, no auth).
4. Secrets: require `~/.config/dotfiles-secrets/{bw_clientid,
   bw_clientsecret,bw_password}` (I4); warn if mode is not 600.
5. Prepare `$HOME/.run` (mkdir -p, mode 700) for `XDG_RUNTIME_DIR` (I5).
6. Copy out kakehashi if missing (I6, warning on failure).
7. Run:
   `apptainer run --env XDG_RUNTIME_DIR=$HOME/.run --bind
   ~/.local/share/cargo,~/.local/share/rustup,~/.local/share/mise,
   ~/.local/share/gnupg,~/.ssh,~/.config/dotfiles-secrets:/run/secrets
   <sif> zsh -l`
   - The entrypoint runs `chezmoi apply` (Bitwarden auth from
     `/run/secrets`) and `exec zsh -l` (I7).
   - Optional `--env PI_CONFIG_URL=...` / `NVIM_CONFIG_URL=...` overrides
     pass through to the entrypoint.

### 4.3 `docs/specifications/26-apptainer-remote.md` (new spec)

Documents the remote contract: image source (GHCR), wrapper usage,
bind/secret mapping table (podman → Apptainer), known differences
(§5), and rollout steps.

## §5 Known differences (podman → Apptainer)

| podman (local) | Apptainer (remote) |
|---|---|
| `--secret` (podman secrets) | files bound to `/run/secrets` |
| named volumes (cargo/rustup/mise/gnupg/ssh) | binds of remote-home XDG dirs |
| `--userns=keep-id` | not needed (runs as invoking user) |
| `--init` | not needed (Apptainer starter handles signals) |
| baked `/run/user/<uid>` | irrelevant (`XDG_RUNTIME_DIR` env override) |
| baked USERNAME/HOST_UID | irrelevant (CI-fixed build args) |
| `make up` readiness polling | not needed (foreground run) |

## §6 Error handling

- Missing secrets → wrapper exits non-zero with instructions (I4).
- Pull / clone failure → wrapper exits non-zero (network or auth problem).
- `chezmoi apply` failure → entrypoint exits non-zero; the wrapper surfaces
  the exit code and the user can re-run (idempotent).
- kakehashi copy-out failure → warning only (I6).
- `/run/secrets` bind over Apptainer's tmpfs `/run` is the one
  environment-specific assumption; if it fails on the target node, the
  fallback is an entrypoint env override for the secrets dir (tracked as a
  follow-up, not implemented now).

## §7 Testing

- **CI:** the workflow itself is the build test (build + push must
  succeed; cache mounts must persist across runs).
- **Static:** `shellcheck` on `scripts/apptainer-run.sh`.
- **Remote (manual, via `ssh sp`):** first-run pull + clone + apply;
  `zsh -l` interactive shell with sheldon/starship/mise working; Bitwarden
  auth succeeds; `chezmoi apply` idempotent on second run; `XDG_RUNTIME_DIR`
  resolves to `$HOME/.run`; kakehashi present after copy-out.
- **Local regression:** `make build` / `make up` / `make exec` unchanged
  (no local files touched).

## §8 Rollout

1. Set GHCR package visibility to public (one-time, GitHub UI).
2. Merge workflow + wrapper + spec.
3. On the remote: `git clone https://github.com/kkiyama117/dotfiles3.git
   ~/.local/share/chezmoi`, create `~/.config/dotfiles-secrets/` with the
   three Bitwarden files (mode 600), run
   `~/.local/share/chezmoi/scripts/apptainer-run.sh`.
