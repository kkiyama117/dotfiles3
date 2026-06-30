# Manage runtime chezmoi.toml via .chezmoi.toml.tmpl — Design

**Status:** DRAFT
**Date opened:** 2026-06-30
**Issue:** [2026-06-30-chezmoi-config-template.md](../../issues/2026-06-30-chezmoi-config-template.md)
**Author:** kiyama

## §1 Context & success criteria

The runtime `~/.config/chezmoi/chezmoi.toml` is hardcoded as a heredoc in
`entrypoint.sh`; the build-prepass one is a static `bind/layer_2_files/`
file `COPY`'d into Stage 2. The goal is to source `chezmoi.toml` from a
single dotfiles-managed template (`.chezmoi.toml.tmpl`) so the content
lives in the chezmoi source, not in `entrypoint.sh`.

- **S1:** `chezmoi.toml` content is defined by a single
  `.chezmoi.toml.tmpl` at the chezmoi source root (repo root);
  `entrypoint.sh` has no config heredoc.
- **S2:** `build_mode` is driven by the `BUILD_MODE` env var (build-prepass
  `true` / runtime unset → `false`).
- **S3:** Both phases render the config with `chezmoi execute-template --init`.
- **S4:** `container/bind/layer_2_files/chezmoi.toml` and its `COPY` are
  removed (the `layer_2_files/` dir is removed).
- **S5:** `BUILD_MODE` is inline in the build-prepass `RUN` (not `ENV`) →
  absent from `podman inspect` / image `Env`.
- **S6:** Layer 5-3 still strips the carried-forward
  `~/.config/chezmoi/chezmoi.toml`.
- **S7:** `make build` green; `.chezmoi.toml.tmpl` ignored by `chezmoi apply`.
- **S8:** `make up` (±`bw_*` secrets): `Up`, `chezmoi apply` OK, runtime
  `chezmoi.toml = build_mode = false` (USERNAME-owned), secrecy unchanged,
  toolchain volumes persist.
- **S9:** build-prepass rendered config is `build_mode = true`.
- **S10:** Host not broken — host `chezmoi init` → `build_mode = false`;
  host `chezmoi apply` (existing config) unaffected.
- **S11:** Specs 01 / 13 / 20 / 21 + entrypoint/Containerfile comments
  updated.

## §2 Alternatives considered

- **A1 (chosen):** `.chezmoi.toml.tmpl` as a single source for both phases,
  `build_mode` via `BUILD_MODE` env, rendered by `chezmoi execute-template
  --init`. Single source of truth; no heredoc; `bind/layer_2_files/` removed.
- **A2 (rejected):** `.chezmoi.toml.tmpl` runtime-only with `build_mode =
  false` hardcoded; build-prepass keeps `bind/layer_2_files/chezmoi.toml`.
  Minimal, but two config sources duplicate the `build_mode` definition and
  break the moment build-prepass is migrated to `chezmoi init`.
- **A3 (rejected):** Manage `~/.config/chezmoi/chezmoi.toml` as a regular
  dotfile (`dot_config/chezmoi/chezmoi.toml.tmpl`) applied by `chezmoi
  apply`. Chicken-and-egg: `chezmoi apply` reads the **existing** config to
  render the config template, so `build_mode` is circular and the build
  vs runtime value cannot be distinguished.
- **A4 (rejected for build-prepass):** Use `chezmoi init` (idiomatic config
  creation) instead of `execute-template --init`. `chezmoi init` git-inits
  its source when no Git repo is detected; the build-prepass scratch
  `/tmp/chezmoi-src` has no `.git` (excluded by `.dockerignore`) → an
  unwanted `git init` side effect. `execute-template --init` is surgical
  and lets both phases use the same command.

## §3 Architecture / Invariants

```
.chezmoi.toml.tmpl   (repo root = chezmoi source root)
      │  chezmoi execute-template --init
      │  BUILD_MODE=true (build) / unset (runtime)
      ▼
~/.config/chezmoi/chezmoi.toml   ──►   chezmoi apply
```

- **I1 (single source):** `chezmoi.toml` content is defined only by
  `.chezmoi.toml.tmpl` at the repo root. No heredoc in `entrypoint.sh`,
  no `bind/layer_2_files/chezmoi.toml`.
- **I2 (env-driven `build_mode`):** The config template is executed prior
  to reading the source state, so it cannot read `[data]` it is generating.
  `build_mode` is therefore read from `BUILD_MODE` env
  (`{{ env "BUILD_MODE" | default "false" }}`), the only phase switch.
- **I3 (no env leak):** `BUILD_MODE` is set inline in the build-prepass
  `RUN` (`BUILD_MODE=true chezmoi ...`), never via `ENV`, so it does not
  persist into image `Env` or `podman inspect`.
- **I4 (surgical render):** Both phases use `chezmoi execute-template --init`
  (not `chezmoi init`), avoiding git/clone side effects and keeping the
  two phases symmetric.
- **I5 (ownership):** The build-prepass render runs as `USER ${USERNAME}`,
  so the carried-forward config is USERNAME-owned; the runtime entrypoint
  (also `${USERNAME}`) can overwrite it. Layer 5-3 strips it regardless
  (I6), so ownership is a defense-in-depth, not a dependency.
- **I6 (clean-slate strip):** Layer 5-3 `rm -f
  ~/.config/chezmoi/chezmoi.toml` is preserved so the entrypoint always
  renders the config fresh from the template (no stale carry-forward).
- **I7 (special file):** `.chezmoi.toml.tmpl` is a chezmoi config template
  (special file), not a source entry → `chezmoi apply` ignores it; there
  is no apply-conflict on `~/.config/chezmoi/chezmoi.toml`.
- **I8 (host safety):** On the host, `chezmoi apply` uses the existing
  `~/.config/chezmoi/chezmoi.toml` (the template is only re-rendered by
  `chezmoi init`). A host `chezmoi init` renders `build_mode = false`
  (BUILD_MODE unset), which is the correct host/runtime value. No host
  breakage.

## §4 Scope / staging breakdown

**In scope:** `.chezmoi.toml.tmpl` (new, repo root); Containerfile Stage 2
build-prepass + Stage 5 comments; `entrypoint.sh`; removal of
`container/bind/layer_2_files/`; specs 01 / 13 / 20 / 21.

**Out of scope:** wiring the actual `{{ if .build_mode }}` guard into
`.zshenv` (separate follow-up, tracked in spec 21 #6 known drift); a
`make bw-secrets` helper; concrete `bitwarden*` templates + item IDs.

## §5 `.chezmoi.toml.tmpl` (new file, repo root)

```
{{- /* chezmoi config — rendered by `chezmoi execute-template --init`.
   build_mode is driven by the BUILD_MODE env var so the same template
   serves the build-prepass (BUILD_MODE=true) and the runtime entrypoint
   (BUILD_MODE unset -> false). This is a chezmoi config template
   (.chezmoi.$FORMAT.tmpl), executed prior to reading the source state,
   so it cannot read [data] it is generating — hence the env var. */ -}}
[data]
build_mode = {{ if eq (env "BUILD_MODE" | default "false") "true" }}true{{ else }}false{{ end }}
```

Renders to:

- build-prepass (`BUILD_MODE=true`): `build_mode = true`
- runtime / host (`BUILD_MODE` unset): `build_mode = false`

## §6 Containerfile — Stage 2 build-prepass

Replace the `COPY bind/layer_2_files/chezmoi.toml ...` with a render step:

```dockerfile
RUN mkdir -p /home/${USERNAME}/.config/chezmoi
# Render the chezmoi config from the source-root template (.chezmoi.toml.tmpl)
# with build_mode=true. BUILD_MODE is inline (not ENV) so it never reaches
# image Env / podman inspect. Runs as USER ${USERNAME} -> USERNAME-owned.
RUN BUILD_MODE=true chezmoi execute-template --init \
      < /tmp/chezmoi-src/.chezmoi.toml.tmpl \
      > /home/${USERNAME}/.config/chezmoi/chezmoi.toml
RUN mkdir -p /tmp/build-home \
 && chezmoi apply --source /tmp/chezmoi-src --destination /tmp/build-home --no-tty --force
```

The `COPY bind/layer_2_files/chezmoi.toml` line and the `# TODO: Check to
make "Build-only" dotfiles can work` note are removed (the template is now
the source of the build config).

## §7 Containerfile — Stage 5 runtime / entrypoint

Layer 5-3 keeps `rm -f /home/${USERNAME}/.config/chezmoi/chezmoi.toml`
(I6). The change is in `entrypoint.sh`: the heredoc is replaced by a
template render.

```bash
mkdir -p "$(dirname "$RUNTIME_CONFIG")"
# Render the chezmoi config from the source-root template (.chezmoi.toml.tmpl)
# via `chezmoi execute-template --init`. build_mode is driven by BUILD_MODE env
# (unset here -> false, the runtime value). The config content lives in the
# dotfiles, not hardcoded in this script.
chezmoi execute-template --init \
  < "${CHEZMOI_SOURCE}/.chezmoi.toml.tmpl" \
  > "$RUNTIME_CONFIG"
```

`CHEZMOI_SOURCE` (`~/.local/share/chezmoi`, the host bind) contains
`.chezmoi.toml.tmpl` at its root (committed at the repo root). `BUILD_MODE`
is unset in the entrypoint → `build_mode = false`.

## §8 Removals

- Delete `container/bind/layer_2_files/chezmoi.toml`.
- Delete the now-empty `container/bind/layer_2_files/` directory.
- Remove the Stage 2 `COPY bind/layer_2_files/chezmoi.toml ...` line.

## §9 Spec + comment updates

- **01-file-structures.md:** remove `layer_2_files/` from the
  `container/bind/` tree; add `.chezmoi.toml.tmpl` to the repo-root
  (chezmoi source root) tree.
- **13-secret-management.md §5a:** rewrite the `build_mode` mechanism —
  set via `.chezmoi.toml.tmpl` rendered by `execute-template --init`,
  driven by `BUILD_MODE` env (build `true` / runtime `false`); remove the
  `bind/layer_2_files/chezmoi.toml` + entrypoint-heredoc wording.
- **21-container-build-flow.md:** Stage 2 row — "render `.chezmoi.toml.tmpl`
  via `chezmoi execute-template --init` with `BUILD_MODE=true`" (was
  `COPY bind/layer_2_files/chezmoi.toml`); runtime/entrypoint row —
  "entrypoint renders `chezmoi.toml` from `.chezmoi.toml.tmpl`" (was
  heredoc); notes narrative updated.
- **20-container-rules.md I10:** the runtime `chezmoi.toml` is rendered by
  the entrypoint from `.chezmoi.toml.tmpl` (not a heredoc).
- **entrypoint.sh / Containerfile comments:** updated to describe the
  template render.

## §10 Verification

1. `make build` green; confirm `.chezmoi.toml.tmpl` is ignored by
   `chezmoi apply` (build reaches `chezmoi apply` without trying to apply
   the config template as a dotfile).
2. Inspect the build-prepass rendered config:
   `BUILD_MODE=true chezmoi execute-template --init < .chezmoi.toml.tmpl`
   → `build_mode = true`; unset → `build_mode = false` (host-side sanity).
3. `podman inspect` + `podman image inspect` `Env` contains no `BUILD_MODE`.
4. `make up` with `bw_*` secrets: `Up`, auth OK, `chezmoi apply` OK,
   `~/.config/chezmoi/chezmoi.toml` = `build_mode = false` (USERNAME-owned);
   no `BW_*` in any environ; toolchain volumes persist.
5. `make up` without secrets (S4 no-secret path): `Up`, auth skipped,
   apply OK, `chezmoi.toml = build_mode = false`.
6. `make down && make up` restart idempotency.
7. Baked image (entrypoint bypassed): `~/.config/chezmoi/chezmoi.toml`
   absent (stripped in Layer 5-3); `.zshenv` present; no bash remnants.

## §11 Open questions

- **Q1:** Does `env` work inside `chezmoi execute-template --init`? It is
  a standard chezmoi template function and the `.chezmoi.$FORMAT.tmpl`
  doc states template functions are available, so this is expected to
  work. Verify on the first implementation run; if not, fall back to
  `--promptString "BUILD_MODE=true"` or a `chezmoi init`-based render.
- **Q2:** Should the entrypoint guard against a missing
  `${CHEZMOI_SOURCE}/.chezmoi.toml.tmpl` (e.g. an older source bind) with
  a loud `exit 1`, or rely on the existing `$CHEZMOI_SOURCE/.git` check?
  Proposal: add a `[ -f ... ]` guard + loud fail (the template is now
  required for the entrypoint to produce a config). Decide in plan.