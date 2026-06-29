# 2026-06-29 — Chezmoi apply twice + toolchain pre-pass + bind/volume restructure

> **Spec status:** DRAFT (design phase). Authoritative once approved.
> **Author:** kiyama (with Claude Opus 4.7).
> **Scope target:** `container/Containerfile`, `Makefile`, chezmoi source tree,
> and four `docs/specifications/` files (13, 20, 21, 02). Implementation
> details belong to a follow-up plan produced by the `writing-plans` skill.

## §1 Purpose

Make the dotfiles container a **disposable test environment** that
faithfully reproduces a host `chezmoi apply` result while also pre-installing
heavy Rust-based tooling at build time so the container is usable
immediately on start.

Concretely, run `chezmoi apply` **twice**:

1. **Build-time pre-pass** — evaluate `dot_zshenv` (and any other
   ENV-bearing dotfile) to a scratch destination, source the result, and
   install rustup / mise / cargo binaries with the resolved
   `CARGO_HOME` / `RUSTUP_HOME` / `MISE_DATA_DIR`. Output dotfiles are
   discarded before the final image layer is finalized.
2. **Runtime apply** — at container start, re-run `chezmoi apply` against
   the host-bound chezmoi source root (`~/.local/share/chezmoi`) to write
   the real dotfiles into `$HOME`, optionally resolving Bitwarden secrets
   via `BW_SESSION` from the host shell.

The image stays **secret-free** in both phases. The build-time apply is
secret-free by construction (`build_mode = true` chezmoi data flag); the
runtime apply consumes secrets only into the running container's `$HOME`,
never back into image layers.

## §2 Background and conflict with existing spec

Existing spec at `docs/specifications/13-secret-management.md` §5 and
invariant **I-S4** assert: *"chezmoi apply runs at runtime only. The
built image contains no rendered secret."* That sentence is incompatible
with running `chezmoi apply` during `make build` at all.

The maintainer (kiyama) approved the following on 2026-06-29:

- **Full apply may run at build time for now.** Tighten the rule into
  a *"build-time pre-pass is secret-free; runtime is the only place
  Bitwarden is consulted"* form later, as a future spec issue.
- The image MUST remain secret-free regardless of build-time apply
  scope. Build-time apply MUST guard any Bitwarden template behind
  `{{- if not .build_mode -}}` (or `.chezmoiignore` template-driven
  exclusion).

Future-issue items captured in §10 below.

## §3 Architecture overview

### §3.1 Containerfile stages (5 stages)

| # | Stage | Source | Purpose |
|---|---|---|---|
| 0 | `manjarolinux/base:latest` | — | OCI base image |
| 1 | `base` | `FROM 0` | Existing: pacman mirrorlist + Layer 1 install + user remap + sudoers + (NEW Layer 1-5) XDG toolchain dirs |
| 2 | `build-prepass` (**NEW**) | `FROM base` | COPY chezmoi source via `srcroot` named build-context, write `chezmoi.toml` with `build_mode = true`, run `chezmoi apply --destination /tmp/build-home` |
| 3 | `toolchain` (**NEW**) | `FROM build-prepass` | `source /tmp/build-home/.zshenv` then install rustup / mise / cargo binaries with BuildKit cache mounts on `$CARGO_HOME/{registry,git}` |
| 4 | `runtime` (**NEW**, final) | `FROM toolchain` | `rm -rf /tmp/{chezmoi-src,build-home}` and `/home/$USER/.config/chezmoi` (build-time chezmoi.toml goes too; runtime entrypoint rebuilds it fresh), copy entrypoint script, set `USER`, `WORKDIR`, `ENTRYPOINT`, `CMD` |

The current `no-config-base` stage is **dropped** (its sole purpose,
`base-devel` install, is already done in Layer 1-2).

### §3.2 Runtime mount strategy

`make up` switches from `-v $(HOME_DIR):/home/$USER` (bind, home full) to:

```
$(CURDIR)         ──bind (rw)──→  /home/$USER/.local/share/chezmoi
dotfiles_cargo    ──volume────→   /home/$USER/.local/share/cargo
dotfiles_rustup   ──volume────→   /home/$USER/.local/share/rustup
dotfiles_mise     ──volume────→   /home/$USER/.local/share/mise
```

Rationale:

- **Host bind for chezmoi source** so `chezmoi cd` / `chezmoi edit` work on
  the real repository files under `$(CURDIR)`. The host's git history is
  the single source of truth.
- **Named volumes for toolchain dirs** because Podman named volumes copy
  the image-side directory contents into the volume on first mount.
  Host bind mounts would hide the build-time-installed tooling
  (overlay semantics) and defeat the purpose of installing at build.
- The `~/.local/share` directory itself is created at image build (Layer
  1-5) with `USERNAME` ownership, so the four child mounts attach
  cleanly with no parent-mount conflict.

### §3.3 Why XDG-compliant paths (not `/opt`)

The user explicitly requires that the container reflect a **host-equivalent
dotfiles environment**, so `CARGO_HOME` / `RUSTUP_HOME` / `MISE_DATA_DIR`
live under `$XDG_DATA_HOME = $HOME/.local/share`, the same as the host
would set when `dot_zshenv` is applied there. Placing them under
`/opt/dotfiles-tools` would diverge from a real host apply and defeat the
goal of using the container as a faithful test environment.

## §4 Containerfile concrete changes

### §4.1 New Layer 1-5 (inside existing `base` stage)

After `USER ${USERNAME}` but before `FROM base AS ...`, switch back to
root briefly to provision the XDG layout, then return to USER:

```dockerfile
USER root
RUN install -d -o ${HOST_UID} -g ${HOST_GID} -m 0755 \
    /home/${USERNAME}/.local/share \
    /home/${USERNAME}/.local/share/cargo \
    /home/${USERNAME}/.local/share/rustup \
    /home/${USERNAME}/.local/share/mise \
    /home/${USERNAME}/.local/share/chezmoi
USER ${USERNAME}
```

Owner-correct directories must exist so the four runtime mounts (one bind,
three volumes) attach to a properly-owned `.local/share/` parent.

### §4.2 Stage 2 `build-prepass`

```dockerfile
FROM base AS build-prepass

COPY --from=srcroot --chown=${HOST_UID}:${HOST_GID} . /tmp/chezmoi-src

RUN mkdir -p /home/${USERNAME}/.config/chezmoi \
 && cat > /home/${USERNAME}/.config/chezmoi/chezmoi.toml <<'TOML'
[data]
build_mode = true
TOML

RUN chezmoi apply \
      --source /tmp/chezmoi-src \
      --destination /tmp/build-home \
      --no-tty \
      --force
```

The `srcroot` build-context is passed by the Makefile as
`--build-context srcroot=$(CURDIR)`. Spec 01 I-FS1 is satisfied: the
primary build context is still `container/`; `srcroot` is an additional
named context.

### §4.3 Stage 3 `toolchain`

```dockerfile
FROM build-prepass AS toolchain

RUN --mount=type=cache,target=/home/${USERNAME}/.cache/cargo-install,uid=${HOST_UID},gid=${HOST_GID} \
    bash -c 'set -e; \
      source /tmp/build-home/.zshenv; \
      curl --proto "=https" --tlsv1.2 -sSf https://sh.rustup.rs \
        | sh -s -- -y --no-modify-path --default-toolchain stable --profile minimal; \
    '

RUN bash -c 'set -e; \
      source /tmp/build-home/.zshenv; \
      curl https://mise.run | sh; \
    '

COPY --from=deps layer_3/cargo.txt /tmp/cargo_tools.txt

RUN --mount=type=cache,target=/home/${USERNAME}/.local/share/cargo/registry,uid=${HOST_UID},gid=${HOST_GID} \
    --mount=type=cache,target=/home/${USERNAME}/.local/share/cargo/git,uid=${HOST_UID},gid=${HOST_GID} \
    bash -c 'set -e; \
      source /tmp/build-home/.zshenv; \
      cargo install --locked $(sed "s/#.*//" /tmp/cargo_tools.txt | xargs); \
    '
```

- `source /tmp/build-home/.zshenv` propagates ENV across the multi-RUN
  toolchain stage. Each `RUN` is a fresh shell, so each must `source`
  again.
- `--mount=type=cache` is used **only** for transient caches (registry
  index, git clones, cargo-install scratch); installed binaries live in
  `$CARGO_HOME/bin`, which is part of the image layer (so the volume
  copy-on-first-mount can see them).
- The `uid=` / `gid=` parameters on `--mount=type=cache` require
  **Podman ≥ 4.0** (BuildKit syntax v1.4+). Verify locally with
  `podman --version` before merging. If unavailable, the cache mounts
  fall back to root ownership and the subsequent `chown` inside the
  RUN body is required to make `$USERNAME` use them.

### §4.4 Stage 4 `runtime`

```dockerfile
FROM toolchain AS runtime

USER root
RUN rm -rf /tmp/chezmoi-src /tmp/build-home /home/${USERNAME}/.config/chezmoi
COPY --chown=root:root container/bind/layer_4_files/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

USER ${USERNAME}
WORKDIR /home/${USERNAME}
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["zsh"]
```

The build-time `chezmoi.toml` (with `build_mode = true`) is removed too —
the entrypoint re-creates it with `build_mode = false` before runtime
apply, so the file is rebuilt fresh per container start.

## §5 Chezmoi source-tree changes

### §5.1 `dot_zshenv` — append toolchain HOME section

Inside the existing XDG section, after `XDG_STATE_HOME` / `XDG_RUNTIME_DIR`:

```sh
: "Toolchain HOMEs (XDG-compliant)" && {
  export CARGO_HOME="${CARGO_HOME:-$XDG_DATA_HOME/cargo}"
  export RUSTUP_HOME="${RUSTUP_HOME:-$XDG_DATA_HOME/rustup}"
  export MISE_DATA_DIR="${MISE_DATA_DIR:-$XDG_DATA_HOME/mise}"
  path=($CARGO_HOME/bin(N-/) $MISE_DATA_DIR/shims(N-/) $path)
}
```

### §5.2 `.chezmoiignore` — add toolchain & self-bind paths

```
# Toolchain volume mountpoints — never managed by chezmoi
.local/share/cargo
.local/share/rustup
.local/share/mise

# Self bind-mount target (chezmoi source root) — chezmoi must not manage itself
.local/share/chezmoi
```

### §5.3 `.dockerignore` — new at repo root

Required because the `srcroot` named build-context copies the entire
repository. The full set of items to exclude is a future-issue
(spec 21 Q2 new), but the immediately-known exclusions are:

```
.git
docs
.env
container/bind/home_dir
```

`.env.example` / `README.md` / `AGENTS.md` may stay (they don't bloat
build noticeably and don't risk leaks; the build only consumes `dot_*`
and `.chezmoi*` entries anyway).

## §6 New runtime entrypoint

`container/bind/layer_4_files/entrypoint.sh` (new file):

```bash
#!/usr/bin/env bash
set -euo pipefail

CHEZMOI_SOURCE="${HOME}/.local/share/chezmoi"
RUNTIME_CONFIG="${HOME}/.config/chezmoi/chezmoi.toml"

if [[ ! -d "$CHEZMOI_SOURCE/.git" ]]; then
  echo "entrypoint: $CHEZMOI_SOURCE is not a chezmoi source (no .git)." >&2
  echo "entrypoint: did make up bind the repo root into ~/.local/share/chezmoi?" >&2
  exit 1
fi

mkdir -p "$(dirname "$RUNTIME_CONFIG")"
cat > "$RUNTIME_CONFIG" <<'TOML'
[data]
build_mode = false
TOML

chezmoi apply --no-tty --force

exec "$@"
```

Failure modes:

- Bind missing → fail fast with a hint about `make up`.
- `chezmoi apply` failure (e.g. `BW_SESSION` set but vault locked) →
  `set -e` propagates, container exits non-zero. Operator must
  re-export `BW_SESSION` or unset it for a secret-free apply and rerun
  `make up`.

## §7 Makefile changes

### §7.1 Variables

```makefile
# New
CARGO_VOLUME  := dotfiles_cargo
RUSTUP_VOLUME := dotfiles_rustup
MISE_VOLUME   := dotfiles_mise

# Removed
- HOME_DIR := $(CURDIR)/container/bind/home_dir
```

### §7.2 `build` target

Add `--build-context srcroot=$(CURDIR)` alongside the existing
`--build-context deps=...`.

### §7.3 `up` target

```makefile
up: _require_username
	podman run -d --replace --name $(CONTAINER) \
		--userns=keep-id \
		-v $(CURDIR):/home/$(USERNAME)/.local/share/chezmoi \
		-v $(CARGO_VOLUME):/home/$(USERNAME)/.local/share/cargo \
		-v $(RUSTUP_VOLUME):/home/$(USERNAME)/.local/share/rustup \
		-v $(MISE_VOLUME):/home/$(USERNAME)/.local/share/mise \
		$(IMAGE) sleep infinity
```

The bind to `$(CURDIR)` is **rw** so `chezmoi edit` (and editor invocations
through it) write back to the host repository. No `:U` / `:Z` flag is
used, per spec 20 I3 (`--userns=keep-id` already preserves ownership).

### §7.4 `clean` target (new)

```makefile
clean: down ## Full reset: remove container, image, and toolchain volumes
	-podman volume rm $(CARGO_VOLUME) $(RUSTUP_VOLUME) $(MISE_VOLUME)
	-podman rmi $(IMAGE)
```

`make down` keeps volumes (so `make build && make up` reuses cached
toolchains). `make clean` is the explicit reset path.

### §7.5 `.PHONY` and `help`

Add `clean` to `.PHONY` and document it in `help`.

## §8 Spec edits (Phase B of the plan)

| File | Change |
|---|---|
| `13-secret-management.md` | §5 reworded to permit build-time scratch apply; I-S4 reworded to scope "build-time scratch + runtime $HOME"; §8 adds Q3 (build_mode flag vs `.chezmoiignore` template guard) |
| `20-container-rules.md` | I4 reworded to call out the secret-free build pre-pass; Q1 reword to point to the revised §5 |
| `21-container-build-flow.md` | Stage ordering table replaced with the 5-stage layout (Layer 1-5 added; `no-config-base` removed; stages 2/3/4 added). Acceptance criteria gain items 5-8 (scratch-removed assertion, XDG ENV assertion, host bind visibility assertion). Q1 partially-resolved note refreshed; Q2 added about `.dockerignore` policy. |
| `02-installed-programs.md` | `cargo` added as a manager (allowed values + manager rules) |
| `01-file-structures.md` | (optional) `container/bind/layer_4_files/entrypoint.sh` and `dependencies/layer_3/cargo.txt` added to the tree diagram |
| `dependencies/packages.toml` | Cargo entries appended (initial list TBD per §10 open item 1) |
| `programs/generate_deps/main.py` | Accept `cargo` manager; write `dependencies/layer_3/cargo.txt`; render in AUTO-GEN block |
| `container/.gitignore` | Remove the `home_dir` entry (the directory itself is no longer used) |
| `.gitignore` (repo root) | Confirm `container/bind/home_dir` is not separately ignored at root level |

## §9 Acceptance criteria

A change-set realising this design lands only when **all** hold:

1. `make build` completes without manual intervention.
2. `podman run --rm $(IMAGE) /bin/bash -c 'test ! -d /tmp/chezmoi-src && test ! -d /tmp/build-home'` exits 0 (scratch removed).
3. `podman run --rm $(IMAGE) /bin/bash -lc 'rustc --version && cargo --version && mise --version'` reports versions for all three.
4. `make up && podman exec $(CONTAINER) test -f /home/$(USERNAME)/.zshenv` exits 0 (runtime apply succeeded with no `BW_SESSION`).
5. `podman exec $(CONTAINER) bash -lc 'echo $CARGO_HOME'` outputs `/home/$(USERNAME)/.local/share/cargo`.
6. `podman exec $(CONTAINER) ls /home/$(USERNAME)/.local/share/chezmoi/.git` exits 0 (host bind is rw and source root visible).
7. `make down && make up` preserves toolchain binaries (named volume not removed).
8. `make clean` removes the image and the three named volumes; a subsequent `make build && make up` re-creates everything from scratch.
9. Spec edits in §8 land in the same change-set as the Containerfile / Makefile edits (or in an immediately-preceding spec-only commit).
10. `dependencies/layer_3/cargo.txt` is generated by `make gen-deps`, never hand-edited (spec 20 I8 extended to layer 3).

## §10 Open items (resolved at writing-plans phase or as future issues)

1. **Concrete cargo install list.** Default proposal (placeholder, not
   approved): `starship`, `eza`, `bat`, `fd-find`, `ripgrep`, `zoxide`,
   `bottom`, `tealdeer`. The maintainer (kiyama) must confirm or
   replace this list before implementation. A safer starting point is
   to land the infrastructure with **zero** cargo entries and grow the
   list via `make gen-deps` later.
2. **`programs/generate_deps/main.py` schema bump.** Whether the
   `packages.toml` `schema` constant needs to go 1 → 2 to admit
   `manager = "cargo"` is implementation-dependent; resolve by reading
   the script.
3. **`.dockerignore` policy.** Beyond the must-exclude set listed in
   §5.3, additional paths to exclude from the `srcroot` build context
   (e.g. transient editor swap files, large untracked subtrees) need a
   convention. Future spec issue against spec 21.
4. **`make clean` scope.** Currently includes `podman rmi $(IMAGE)`.
   If users prefer image-preserving cleanup, split into `make clean`
   (volumes only) and `make distclean` (volumes + image).
5. **Runtime apply failure UX.** `entrypoint.sh` currently fails-fast
   on `chezmoi apply` errors. An alternative is to log the failure and
   still `exec "$@"` so the user lands in a usable shell to debug
   (e.g. `chezmoi diff`). Pick one before merging.
6. **`build_mode` convention for future Bitwarden templates.** Adopt
   `{{- if not .build_mode -}}` (in-template guard) or
   `.chezmoiignore` template-based exclusion. To be resolved with the
   first Bitwarden-bound dotfile. (Tracked: spec 13 §8 Q3.)
7. **AUR / `paru` build scheduling and cache mount.** Out of scope for
   this design; tracked in spec 21 Q1.

## §11 Rollback

The change-set is reversible via `git revert` on the spec + code commits.
Because the reverted Makefile will no longer know the volume names, the
**ordering matters**:

1. **Before** running `git revert`, run `make clean` (against the
   not-yet-reverted Makefile) to delete the three named volumes
   (`dotfiles_cargo`, `dotfiles_rustup`, `dotfiles_mise`) and the
   image. If `make clean` was already removed locally, run the
   `podman volume rm` / `podman rmi` commands manually with the names
   above before reverting.
2. Run `git revert` on the spec + code commits.
3. `mkdir -p container/bind/home_dir` to restore the directory the old
   `make up` expects (the old target did `mkdir -p` on it, so a fresh
   `make up` after revert also works without this step — it just
   creates the directory on the fly).

If revert happens out of order (Makefile gone, volumes still present),
the volumes are not lost — clean them up manually with
`podman volume rm dotfiles_cargo dotfiles_rustup dotfiles_mise`.

No data loss risk: the build-time scratch never touches host paths;
runtime data lives in named volumes that are explicit to delete.

## §12 References

- `docs/specifications/13-secret-management.md` (§5 / I-S4 — to be revised)
- `docs/specifications/20-container-rules.md` (I4 / Q1 — to be revised)
- `docs/specifications/21-container-build-flow.md` (Stage ordering table + acceptance criteria — to be revised)
- `docs/specifications/02-installed-programs.md` (manager rules — to be extended with `cargo`)
- `docs/specifications/01-file-structures.md` (tree diagram — minor extension)
- `container/Containerfile` (current 5099 bytes, 102 lines — to be rewritten)
- `Makefile` (current 2429 bytes — to be extended with `clean`, `srcroot`, volume vars)
- `dot_zshenv` (current 3056 bytes — to be appended with toolchain HOMEs)
