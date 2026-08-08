# Apptainer Remote Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the dotfiles container run on a remote HPC login node that has only Apptainer, by building the existing Containerfile in GitHub Actions, publishing to GHCR, and providing a wrapper script that runs the image with Apptainer.

**Architecture:** GitHub Actions (BuildKit) builds the unchanged Containerfile with the same named build contexts as the local Makefile and pushes a public GHCR package. On the remote, `scripts/apptainer-run.sh` pulls the SIF, clones the chezmoi source, binds remote-home XDG dirs + Bitwarden secret files, and runs `apptainer run ... zsh -l` so the existing entrypoint (`chezmoi apply` + Bitwarden auth → `exec zsh -l`) works unchanged.

**Tech Stack:** GitHub Actions (`docker/build-push-action`), BuildKit named contexts + `gha` cache, Apptainer/Singularity, bash, GHCR.

## Global Constraints

- The Containerfile, Makefile, and `container/bind/layer_5_files/entrypoint.sh` are **not modified** (design I1/I5/I7).
- CI build args are fixed: `HOST_UID=1000`, `HOST_GID=1000`, `USERNAME=kiyama` (design I2). The wrapper references `/home/kiyama/.local/bin/kakehashi` (design I6).
- The GHCR package must be public for anonymous pull (design I3).
- The wrapper **requires** `~/.config/dotfiles-secrets/{bw_clientid,bw_clientsecret,bw_password}` and exits non-zero if missing (design I4).
- `XDG_RUNTIME_DIR` is overridden to `$HOME/.run` (design I5).
- The wrapper detects `apptainer` or `singularity` (design I8).
- Docs follow `docs/specifications/00-document-management.md` naming; all docs in English.
- Design doc: `docs/specifications/implementations/2026-08-08-apptainer-remote-design.md` (DRAFT until Task 4).
- Issue: `docs/issues/2026-08-08-apptainer-remote.md` + GitHub issue #13.

---

### Task 1: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/build-image.yml`

**Interfaces:**
- Consumes: existing `container/Containerfile` (named contexts `deps`, `srcroot`), `.containerignore`
- Produces: `ghcr.io/kkiyama117/dotfiles-manjaro:latest` + `:<sha>` (consumed by Task 5 remote pull)

- [ ] **Step 1: Create the workflow file**

Create `.github/workflows/build-image.yml` with exactly this content:

```yaml
name: build-image

on:
  push:
    branches: [main]
    paths:
      - "container/**"
      - "dependencies/**"
      - ".github/workflows/build-image.yml"
      - ".chezmoi*"
      - "dot_zshenv.tmpl"
  workflow_dispatch:

permissions:
  contents: read
  packages: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up BuildKit
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: ./container
          file: container/Containerfile
          build-contexts: |
            deps=./dependencies
            srcroot=.
          build-args: |
            HOST_UID=1000
            HOST_GID=1000
            USERNAME=kiyama
          tags: |
            ghcr.io/kkiyama117/dotfiles-manjaro:latest
            ghcr.io/kkiyama117/dotfiles-manjaro:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          push: true
```

- [ ] **Step 2: Validate the YAML syntax**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/build-image.yml')); print('yaml ok')"`
Expected: `yaml ok` (no exception)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/build-image.yml
git commit -m "Add GH Actions workflow to build and push the container image to GHCR (docs/issues/2026-08-08-apptainer-remote.md)"
```

---

### Task 2: Remote wrapper script

**Files:**
- Create: `scripts/apptainer-run.sh`

**Interfaces:**
- Consumes: GHCR image ref `docker://ghcr.io/kkiyama117/dotfiles-manjaro:latest` (Task 1), public repo `https://github.com/kkiyama117/dotfiles3.git`
- Produces: executable `apptainer-run.sh` with flags `--update`, `--dry-run`, `-- <shell args>`; env overrides `SIF_DIR`, `SECRETS_DIR`; used by Task 5 on the remote

- [ ] **Step 1: Create the script**

Create `scripts/apptainer-run.sh` with exactly this content:

```bash
#!/usr/bin/env bash
#
# apptainer-run.sh — start an interactive zsh in the dotfiles container on
# a remote host that has Apptainer (or Singularity) but no Podman.
#
# Lives in the dotfiles source tree (not chezmoi-managed). On the remote it
# is at ~/.local/share/chezmoi/scripts/apptainer-run.sh.
#
# Usage:
#   apptainer-run.sh [--update] [--dry-run] [-- <shell args...>]
#
# Environment overrides:
#   SIF_DIR      where the SIF file lives (default: ~/.apptainer)
#   SECRETS_DIR  dir with bw_clientid / bw_clientsecret / bw_password
#                (default: ~/.config/dotfiles-secrets)
#   PI_CONFIG_URL / NVIM_CONFIG_URL  pass through to the entrypoint
#                (Apptainer forwards the host environment by default)
#
# See docs/specifications/26-apptainer-remote.md.
set -euo pipefail

IMAGE_REF="docker://ghcr.io/kkiyama117/dotfiles-manjaro:latest"
SIF_DIR="${SIF_DIR:-$HOME/.apptainer}"
SIF="$SIF_DIR/dotfiles-manjaro_latest.sif"
SECRETS_DIR="${SECRETS_DIR:-$HOME/.config/dotfiles-secrets}"
SOURCE_DIR="$HOME/.local/share/chezmoi"
RUNTIME_DIR="$HOME/.run"
KAKEHASHI_SRC="/home/kiyama/.local/bin/kakehashi"
KAKEHASHI_DST="$HOME/.local/bin/kakehashi"

UPDATE=0
DRY_RUN=0
SHELL_ARGS=(zsh -l)

while [[ $# -gt 0 ]]; do
  case "$1" in
    --update) UPDATE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --) shift; SHELL_ARGS=("$@"); break ;;
    -h|--help)
      echo "usage: apptainer-run.sh [--update] [--dry-run] [-- <shell args...>]"
      exit 0
      ;;
    *)
      echo "apptainer-run: unknown argument: $1 (see --help)" >&2
      exit 1
      ;;
  esac
done

# --- command detection ---
if command -v apptainer >/dev/null 2>&1; then
  APPTAINER=apptainer
elif command -v singularity >/dev/null 2>&1; then
  APPTAINER=singularity
else
  echo "apptainer-run: error: neither apptainer nor singularity found on PATH." >&2
  exit 1
fi

# --- pull if missing (or --update) ---
if [[ ! -f "$SIF" || $UPDATE -eq 1 ]]; then
  mkdir -p "$SIF_DIR"
  "$APPTAINER" pull "$SIF" "$IMAGE_REF"
fi

# --- clone the chezmoi source if missing (public repo, no auth) ---
if [[ ! -d "$SOURCE_DIR/.git" ]]; then
  mkdir -p "$(dirname "$SOURCE_DIR")"
  git clone https://github.com/kkiyama117/dotfiles3.git "$SOURCE_DIR"
fi

# --- Bitwarden secrets are required ---
missing=0
for f in bw_clientid bw_clientsecret bw_password; do
  if [[ ! -f "$SECRETS_DIR/$f" ]]; then
    echo "apptainer-run: error: missing $SECRETS_DIR/$f" >&2
    missing=1
  fi
done
if [[ $missing -eq 1 ]]; then
  echo "apptainer-run: create $SECRETS_DIR/{bw_clientid,bw_clientsecret,bw_password} (chmod 600) first." >&2
  exit 1
fi

# --- XDG_RUNTIME_DIR override ---
mkdir -p "$RUNTIME_DIR"
chmod 700 "$RUNTIME_DIR"

# --- kakehashi copy-out, optional ---
if [[ ! -x "$KAKEHASHI_DST" ]]; then
  mkdir -p "$(dirname "$KAKEHASHI_DST")"
  if "$APPTAINER" exec "$SIF" cat "$KAKEHASHI_SRC" > "$KAKEHASHI_DST" 2>/dev/null; then
    chmod 755 "$KAKEHASHI_DST"
  else
    echo "apptainer-run: warning: could not copy kakehashi from the image; skipping." >&2
    rm -f "$KAKEHASHI_DST"
  fi
fi

# --- binds: named-volume equivalents + secrets ---
BINDS=(
  "$HOME/.local/share/cargo"
  "$HOME/.local/share/rustup"
  "$HOME/.local/share/mise"
  "$HOME/.local/share/gnupg"
  "$HOME/.ssh"
  "$SECRETS_DIR:/run/secrets"
)
BIND_ARG=""
for b in "${BINDS[@]}"; do
  BIND_ARG+="${BIND_ARG:+,}$b"
done

CMD=(
  "$APPTAINER" run
  --env "XDG_RUNTIME_DIR=$RUNTIME_DIR"
  --bind "$BIND_ARG"
  "$SIF"
  "${SHELL_ARGS[@]}"
)

if [[ $DRY_RUN -eq 1 ]]; then
  printf '%q ' "${CMD[@]}"
  echo
  exit 0
fi

exec "${CMD[@]}"
```

- [ ] **Step 2: Make it executable and syntax-check**

Run: `chmod +x scripts/apptainer-run.sh && bash -n scripts/apptainer-run.sh && echo "syntax ok"`
Expected: `syntax ok`

- [ ] **Step 3: Run shellcheck**

Run: `shellcheck scripts/apptainer-run.sh`
Expected: no findings (exit 0)

- [ ] **Step 4: Dry-run test with a fake apptainer**

Run:

```bash
TMP=$(mktemp -d)
mkdir -p "$TMP/bin" "$TMP/sif" "$TMP/secrets" "$TMP/home/.local/share/chezmoi/.git"
printf '#!/bin/sh\necho "apptainer $*"\n' > "$TMP/bin/apptainer"
chmod +x "$TMP/bin/apptainer"
touch "$TMP/sif/dotfiles-manjaro_latest.sif"
for f in bw_clientid bw_clientsecret bw_password; do printf 'x\n' > "$TMP/secrets/$f"; done
HOME="$TMP/home" SIF_DIR="$TMP/sif" SECRETS_DIR="$TMP/secrets" PATH="$TMP/bin:$PATH" \
  ./scripts/apptainer-run.sh --dry-run
```

Expected: prints one line starting with `apptainer run --env XDG_RUNTIME_DIR=<TMP>/home/.run --bind <TMP>/home/.local/share/cargo,<TMP>/home/.local/share/rustup,<TMP>/home/.local/share/mise,<TMP>/home/.local/share/gnupg,<TMP>/home/.ssh,<TMP>/secrets:/run/secrets <TMP>/sif/dotfiles-manjaro_latest.sif zsh -l` (exact temp path varies). The kakehashi copy-out runs first and succeeds against the fake apptainer (harmless).

- [ ] **Step 5: Negative test — missing secrets**

Run:

```bash
TMP=$(mktemp -d)
mkdir -p "$TMP/bin" "$TMP/sif" "$TMP/home/.local/share/chezmoi/.git"
printf '#!/bin/sh\necho "apptainer $*"\n' > "$TMP/bin/apptainer"
chmod +x "$TMP/bin/apptainer"
touch "$TMP/sif/dotfiles-manjaro_latest.sif"
HOME="$TMP/home" SIF_DIR="$TMP/sif" SECRETS_DIR="$TMP/secrets" PATH="$TMP/bin:$PATH" \
  ./scripts/apptainer-run.sh --dry-run; echo "exit=$?"
```

Expected: three `apptainer-run: error: missing ...` lines, the "create ... first" hint, and `exit=1`.

- [ ] **Step 6: Commit**

```bash
git add scripts/apptainer-run.sh
git commit -m "Add apptainer-run.sh wrapper for remote Apptainer hosts (docs/issues/2026-08-08-apptainer-remote.md)"
```

---

### Task 3: Spec 26 — Apptainer remote contract

**Files:**
- Create: `docs/specifications/26-apptainer-remote.md`

**Interfaces:**
- Consumes: design `docs/specifications/implementations/2026-08-08-apptainer-remote-design.md` (approved content), Task 1/2 artifacts
- Produces: normative spec referenced by the wrapper script header and Task 5 result-log

- [ ] **Step 1: Create the spec**

Create `docs/specifications/26-apptainer-remote.md` with exactly this content:

```markdown
# 26 — Apptainer remote contract

> Spec status: **active**. Normative spec for running the dotfiles
> container on a remote host that has Apptainer (formerly Singularity)
> instead of Podman. Design:
> [`implementations/2026-08-08-apptainer-remote-design.md`](implementations/2026-08-08-apptainer-remote-design.md).

## Scope

- Target: the login node of an HPC cluster (accessed via `ssh sp`),
  x86_64, rootless, with internet access.
- Image: built by GitHub Actions from the existing Containerfile
  (unchanged) and published to GHCR as a public package.
- Runtime: ephemeral `apptainer run` per shell. The existing entrypoint
  runs `chezmoi apply` (Bitwarden auth from `/run/secrets`) and then
  `exec zsh -l`.

## Invariants

- I-AP1: The image source is `ghcr.io/kkiyama117/dotfiles-manjaro:latest`
  (public, anonymous pull).
- I-AP2: The Containerfile is unchanged. CI build args are fixed:
  `HOST_UID=1000`, `HOST_GID=1000`, `USERNAME=kiyama`. Apptainer runs the
  container as the invoking user, so the baked uid/gid/username are
  irrelevant at runtime.
- I-AP3: The remote home is `$HOME`. The five Podman named volumes are
  replaced by binds of the remote home's XDG directories
  (`~/.local/share/{cargo,rustup,mise,gnupg}`, `~/.ssh`).
- I-AP4: Bitwarden credentials are files in
  `~/.config/dotfiles-secrets/{bw_clientid,bw_clientsecret,bw_password}`
  (mode 600) bound to `/run/secrets`. The wrapper exits non-zero if any
  file is missing (without `BW_SESSION`, `private_secrets.zsh.tmpl`'s
  `bitwarden*` templates fail and `chezmoi apply` cannot succeed).
- I-AP5: `XDG_RUNTIME_DIR` is overridden to `$HOME/.run` (created by the
  wrapper). `dot_zshenv.tmpl` uses `${XDG_RUNTIME_DIR:-/run/user/$UID}`, so
  the preset env var wins; Apptainer's `/run` is a root-owned tmpfs.
- I-AP6: The entrypoint is unchanged. It reads `/run/secrets/*`, uses
  `${HOME}` for the chezmoi source, and `exec "$@"`. The readiness
  sentinel and `make up` polling are podman-only and unused on the remote
  (foreground run).
- I-AP7: The baked kakehashi binary (`/home/kiyama/.local/bin/kakehashi`)
  is hidden by the home mount; the wrapper copies it out once to
  `$HOME/.local/bin/kakehashi` (optional; warning on failure).
- I-AP8: The wrapper detects `apptainer` or `singularity` (legacy name).
- I-AP9: The remote's native (non-container) shell also sees the applied
  dotfiles (choice A side effect). The container shell is the supported
  shell.

## Usage (remote)

```bash
# one-time setup
git clone https://github.com/kkiyama117/dotfiles3.git ~/.local/share/chezmoi
mkdir -p ~/.config/dotfiles-secrets && chmod 700 ~/.config/dotfiles-secrets
# place bw_clientid / bw_clientsecret / bw_password there (chmod 600)

# every shell
~/.local/share/chezmoi/scripts/apptainer-run.sh
# flags: --update (re-pull the image), --dry-run (print the command),
#        -- <shell args...> (override the default `zsh -l`)
```

## Mapping (podman → Apptainer)

| podman (local) | Apptainer (remote) |
|---|---|
| `--secret` (podman secrets) | files bound to `/run/secrets` |
| named volumes (cargo/rustup/mise/gnupg/ssh) | binds of remote-home XDG dirs |
| `--userns=keep-id` | not needed (runs as invoking user) |
| `--init` | not needed (Apptainer starter handles signals) |
| baked `/run/user/<uid>` | irrelevant (`XDG_RUNTIME_DIR` env override) |
| baked USERNAME/HOST_UID | irrelevant (CI-fixed build args) |
| `make up` readiness polling | not needed (foreground run) |

## Rollout

1. Set the GHCR package visibility to public (one-time, GitHub UI or
   `gh api --method PATCH /user/packages/container/dotfiles-manjaro -f visibility=public`).
2. On the remote: clone the source, create the secrets dir, run the
   wrapper (see Usage).
```

- [ ] **Step 2: Verify cross-references**

Run: `grep -n "26-apptainer-remote" docs/specifications/implementations/2026-08-08-apptainer-remote-design.md scripts/apptainer-run.sh`
Expected: the design §4.3 and the script header both reference the spec (they already do; this confirms the link target exists).

- [ ] **Step 3: Commit**

```bash
git add docs/specifications/26-apptainer-remote.md
git commit -m "Add spec 26 for the Apptainer remote contract (docs/issues/2026-08-08-apptainer-remote.md)"
```

---

### Task 4: Review per spec 09 and approve the design

**Files:**
- Modify: `docs/specifications/implementations/2026-08-08-apptainer-remote-design.md` (status DRAFT → Approved)
- Create: `docs/reviews/2026-08-08-apptainer-remote-review-pass1.md` (aggregate)

**Interfaces:**
- Consumes: design doc + cited sources (spec 20/21, Containerfile, entrypoint, `.chezmoi.toml.tmpl`)
- Produces: Approved design (gate for Task 5)

- [ ] **Step 1: Dispatch a letter-A reviewer**

Per spec 09 §2.2 (ordinary design → letter A minimum), dispatch a
factual/correctness reviewer agent with the design doc and its cited
sources. The reviewer checks: claims vs. citations, false premises,
logical gaps (e.g. the `/run/secrets` bind assumption, CI build-arg
fixing, kakehashi copy-out mechanics).

- [ ] **Step 2: Address findings**

Quote each finding ID verbatim in the response; fix the design doc where
the finding is valid; mark RESOLVED / addressed / INCOMPLETE per spec 09
§4. Re-dispatch if any P1 finding is unresolved.

- [ ] **Step 3: Write the aggregate review**

Create `docs/reviews/2026-08-08-apptainer-remote-review-pass1.md` per
spec 09 §3 (per-letter findings + aggregate verdict).

- [ ] **Step 4: Mark the design Approved**

Edit the design doc status line: `**Status:** DRAFT` → `**Status:** Approved`.

- [ ] **Step 5: Commit**

```bash
git add docs/specifications/implementations/2026-08-08-apptainer-remote-design.md docs/reviews/2026-08-08-apptainer-remote-review-pass1.md
git commit -m "Approve apptainer-remote design after letter-A review (docs/issues/2026-08-08-apptainer-remote.md)"
```

---

### Task 5: Push, CI verification, remote verification, result-log

**Files:**
- Create: `docs/issues/2026-08-08-phase-apptainer-remote.md` (result-log)

**Interfaces:**
- Consumes: Task 1 workflow (CI build), Task 2 wrapper, Task 3 spec, Task 4 approved design
- Produces: built public GHCR image, verified remote shell, closed GitHub issue #13

- [ ] **Step 1: Push to main**

Run: `git push origin main`
Expected: push succeeds; the `build-image` workflow starts (check with `gh run list --workflow=build-image`).

- [ ] **Step 2: Watch the CI build**

Run: `gh run watch --workflow=build-image --exit-status` (or `gh run list` + poll)
Expected: the build job succeeds (BuildKit named contexts + gha cache work; image pushed to GHCR).

- [ ] **Step 3: Make the GHCR package public**

Run: `gh api --method PATCH /user/packages/container/dotfiles-manjaro -f visibility=public`
Expected: JSON response with `"visibility": "public"`.

- [ ] **Step 4: Remote verification (operator step — run via `ssh sp` or hand to the user)**

```bash
ssh sp
git clone https://github.com/kkiyama117/dotfiles3.git ~/.local/share/chezmoi
mkdir -p ~/.config/dotfiles-secrets && chmod 700 ~/.config/dotfiles-secrets
# place bw_clientid / bw_clientsecret / bw_password (chmod 600) — operator action
~/.local/share/chezmoi/scripts/apptainer-run.sh
```

Expected: SIF pull succeeds; entrypoint runs `chezmoi apply` with Bitwarden
auth; an interactive zsh prompt appears. Then verify inside the shell:

```bash
echo $XDG_RUNTIME_DIR        # -> /home/<user>/.run
which kakehashi              # -> /home/<user>/.local/bin/kakehashi
pi --version                 # -> version string (mise shim)
zoxide query -l -- | grep chezmoi   # seeded source path
```

Exit the shell and re-run the wrapper: the second run must be idempotent
(no re-clone, no re-pull, apply succeeds again).

- [ ] **Step 5: Write the result-log**

Create `docs/issues/2026-08-08-phase-apptainer-remote.md` per
00-document-management.md (result-log type): evidence of the CI build,
public package, and remote verification commands + outputs.

- [ ] **Step 6: Close the issue and commit**

```bash
gh issue close 13
git add docs/issues/2026-08-08-phase-apptainer-remote.md
git commit -m "Close apptainer-remote phase with result log (docs/issues/2026-08-08-apptainer-remote.md)"
git push origin main
```
