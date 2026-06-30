# chezmoi-config-template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded `chezmoi.toml` heredoc in `entrypoint.sh` and the static `bind/layer_2_files/chezmoi.toml` with a single dotfiles-managed `.chezmoi.toml.tmpl` rendered by `chezmoi execute-template --init`, with `build_mode` driven by the `BUILD_MODE` env var.

**Architecture:** A new `.chezmoi.toml.tmpl` at the repo root (chezmoi source root) renders `~/.config/chezmoi/chezmoi.toml` in both the Containerfile Stage 2 build-prepass (`BUILD_MODE=true`) and the runtime entrypoint (`BUILD_MODE` unset → `false`). Both phases use `chezmoi execute-template --init` (surgical, no `chezmoi init` git side effects). Layer 5-3 still strips the carried-forward config so the entrypoint renders it fresh.

**Tech Stack:** Containerfile (podman build 5.8.3), bash entrypoint, chezmoi (`execute-template --init`), TOML, Makefile.

## Global Constraints

- `BUILD_MODE` is set **inline in a `RUN`** (e.g. `BUILD_MODE=true chezmoi ...`), never via `ENV` — it must NOT appear in `podman inspect` / image `Env` (design I3).
- Image stays secret-free (spec 20 I4); build is non-root (spec 20 I7). The `bw` auth block in `entrypoint.sh` is **unchanged** — this plan does not touch secret handling.
- Layer 5-3 `rm -f ~/.config/chezmoi/chezmoi.toml` is **preserved** (design I6).
- `.chezmoi.toml.tmpl` is a chezmoi special file (config template); `chezmoi apply` must ignore it (design I7).
- Repo doc protocol: issue → design (Approved) → plan → execution → result-log. This plan's parent issue is `docs/issues/2026-06-30-chezmoi-config-template.md`; design is `docs/specifications/implementations/2026-06-30-chezmoi-config-template-design.md`.
- Each Phase is a single commit. Verification uses the smoke gate (build + `make up` + checks), not unit tests (this is infra config, not unit-testable code).
- Working directory: `/data/dotfiles3`; `.env` has `USERNAME=kiyama`; build context root is `container/` (`BUILD_CTX`).
- All secrecy checks use **quiet** `grep -qi` (presence/absence only) — never print credential values.

---

## File Structure

- **Create:** `.chezmoi.toml.tmpl` (repo root = chezmoi source root) — the single config template.
- **Modify:** `container/Containerfile` — Stage 2 build-prepass (replace `COPY` with render); comments.
- **Modify:** `container/bind/layer_5_files/entrypoint.sh` — replace the `cat >` heredoc with `chezmoi execute-template --init`; add a template-exists guard.
- **Delete:** `container/bind/layer_2_files/chezmoi.toml` and the now-empty `container/bind/layer_2_files/` directory.
- **Modify (docs):** `docs/specifications/01-file-structures.md`, `docs/specifications/13-secret-management.md`, `docs/specifications/20-container-rules.md`, `docs/specifications/21-container-build-flow.md`.

---

## Phase 1 — Add `.chezmoi.toml.tmpl` + verify the render mechanism (resolves Q1)

**Files:**
- Create: `.chezmoi.toml.tmpl`

**Interfaces:**
- Produces: `.chezmoi.toml.tmpl` at the repo root, rendering `[data] build_mode = <true|false>` based on `BUILD_MODE` env. Consumed by Phase 2 (Stage 2 render) and Phase 3 (entrypoint render).

- [ ] **Step 1: Create `.chezmoi.toml.tmpl` at the repo root**

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

- [ ] **Step 2: Verify Q1 — `env` works inside `chezmoi execute-template --init`**

Use the existing image's `chezmoi` (no rebuild needed) to de-risk before touching the Containerfile. Run a throwaway template through both `BUILD_MODE=true` and unset:

```bash
cd /data/dotfiles3
printf '[data]\nbuild_mode = {{ if eq (env "BUILD_MODE" | default "false") "true" }}true{{ else }}false{{ end }}\n' > /tmp/q1.tmpl
echo "=== BUILD_MODE=true ==="
podman run --rm -e BUILD_MODE=true --entrypoint /bin/sh localhost/dotfiles-manjaro:latest -c 'chezmoi execute-template --init < /dev/stdin' < /tmp/q1.tmpl
echo "=== BUILD_MODE unset ==="
podman run --rm --entrypoint /bin/sh localhost/dotfiles-manjaro:latest -c 'chezmoi execute-template --init < /dev/stdin' < /tmp/q1.tmpl
rm -f /tmp/q1.tmpl
```

Expected:
- `BUILD_MODE=true` run prints `build_mode = true`.
- unset run prints `build_mode = false`.

If `env` is NOT available in `--init` (e.g. error or empty), stop and fall back: use `chezmoi init` for runtime (bind has `.git`, no side effect) and `chezmoi execute-template --init --promptString "BUILD_MODE=true"` for build, or reconsider. Record the outcome in the result-log.

- [ ] **Step 3: Render the actual `.chezmoi.toml.tmpl` to confirm byte-exact output**

```bash
cd /data/dotfiles3
echo "=== BUILD_MODE=true ==="
BUILD_MODE=true podman run --rm -e BUILD_MODE=true --entrypoint /bin/sh localhost/dotfiles-manjaro:latest -c 'chezmoi execute-template --init < /dev/stdin' < .chezmoi.toml.tmpl
echo "=== unset ==="
podman run --rm --entrypoint /bin/sh localhost/dotfiles-manjaro:latest -c 'chezmoi execute-template --init < /dev/stdin' < .chezmoi.toml.tmpl
```

Expected:
- true →
  ```
  [data]
  build_mode = true
  ```
- unset →
  ```
  [data]
  build_mode = false
  ```
  (The `{{- ... -}}` comment block must NOT leave a leading blank line; `{{-` trims preceding whitespace.)

- [ ] **Step 4: Commit**

```bash
cd /data/dotfiles3
git add .chezmoi.toml.tmpl
git commit -m "feat(chezmoi): add .chezmoi.toml.tmpl config template (build_mode via BUILD_MODE env)"
```

**Acceptance:** `.chezmoi.toml.tmpl` exists; `chezmoi execute-template --init` renders `build_mode = true` with `BUILD_MODE=true` and `build_mode = false` unset. Q1 resolved.
**Rollback:** `git rm .chezmoi.toml.tmpl && git commit`.

---

## Phase 2 — Containerfile Stage 2: render config from template; remove `bind/layer_2_files/`

**Files:**
- Modify: `container/Containerfile` (Stage 2 build-prepass, ~lines 122-129)
- Delete: `container/bind/layer_2_files/chezmoi.toml`, `container/bind/layer_2_files/`

**Interfaces:**
- Consumes: `.chezmoi.toml.tmpl` (from Phase 1) at `/tmp/chezmoi-src/.chezmoi.toml.tmpl` (the srcroot COPY already brings the repo root into `/tmp/chezmoi-src`, and `.chezmoi.toml.tmpl` is NOT excluded by `.dockerignore`).
- Produces: a Stage 2 `~/.config/chezmoi/chezmoi.toml` with `build_mode = true`, USERNAME-owned.

- [ ] **Step 1: Replace the Stage 2 `COPY` with a render `RUN`**

In `container/Containerfile`, find the build-prepass block:

```dockerfile
# generate temporary chezmoi config
RUN mkdir -p /home/${USERNAME}/.config/chezmoi
# TODO: Check to make "Build-only" dotfiles can work
COPY bind/layer_2_files/chezmoi.toml /home/${USERNAME}/.config/chezmoi/chezmoi.toml
```

Replace with:

```dockerfile
# generate temporary chezmoi config from the source-root template
RUN mkdir -p /home/${USERNAME}/.config/chezmoi
# Render the chezmoi config from .chezmoi.toml.tmpl with build_mode=true.
# BUILD_MODE is inline (not ENV) so it never reaches image Env / podman
# inspect. Runs as USER ${USERNAME} -> USERNAME-owned (the runtime
# entrypoint can overwrite it, and Layer 5-3 strips it regardless).
RUN BUILD_MODE=true chezmoi execute-template --init \
      < /tmp/chezmoi-src/.chezmoi.toml.tmpl \
      > /home/${USERNAME}/.config/chezmoi/chezmoi.toml
```

- [ ] **Step 2: Delete `bind/layer_2_files/`**

```bash
cd /data/dotfiles3
git rm -r container/bind/layer_2_files
```

- [ ] **Step 3: Build the image**

```bash
cd /data/dotfiles3
make build 2>&1 | tee /tmp/build-cct.log | tail -5
```

Expected: `Successfully tagged localhost/dotfiles-manjaro:latest` with a new image ID. The build must reach `chezmoi apply` (Stage 2) and proceed through all 5 stages — i.e. `.chezmoi.toml.tmpl` is ignored by `chezmoi apply` (special file) and the render produced a valid `build_mode = true` config.

- [ ] **Step 4: Verify the build-prepass rendered config is `build_mode = true`**

The build-prepass config does not survive into the final image (Layer 5-3 strips it), so verify it inside the Stage 2 scratch by re-running the render at the same image layer is not possible post-build. Instead, confirm the render output directly (host-side, same mechanism as Phase 1) AND confirm the build succeeded (which means Stage 2's `chezmoi apply` saw `build_mode = true`):

```bash
cd /data/dotfiles3
echo "=== render check (true) ==="
BUILD_MODE=true podman run --rm -e BUILD_MODE=true --entrypoint /bin/sh localhost/dotfiles-manjaro:latest -c 'chezmoi execute-template --init < /dev/stdin' < .chezmoi.toml.tmpl
echo "=== build reached chezmoi apply (Stage 2) ==="
rg -c 'chezmoi apply' /tmp/build-cct.log
```

Expected: render prints `build_mode = true`; the build log shows the Stage 2 `chezmoi apply` ran (build green is the proof the config was valid).

- [ ] **Step 5: Commit**

```bash
cd /data/dotfiles3
git add container/Containerfile
git commit -m "feat(container): render build-prepass chezmoi.toml from .chezmoi.toml.tmpl (BUILD_MODE=true); drop bind/layer_2_files"
```

**Acceptance:** `make build` green; `bind/layer_2_files/` removed; build-prepass render yields `build_mode = true`.
**Rollback:** revert the Containerfile change and `git checkout container/bind/layer_2_files`.

---

## Phase 3 — `entrypoint.sh`: render config from template + guard

**Files:**
- Modify: `container/bind/layer_5_files/entrypoint.sh`

**Interfaces:**
- Consumes: `.chezmoi.toml.tmpl` at `${CHEZMOI_SOURCE}/.chezmoi.toml.tmpl` (the host bind root).
- Produces: `~/.config/chezmoi/chezmoi.toml` with `build_mode = false`, USERNAME-owned, rendered fresh each `make up`.

- [ ] **Step 1: Replace the heredoc with a template render + add the template-exists guard (Q2)**

In `container/bind/layer_5_files/entrypoint.sh`, find:

```bash
mkdir -p "$(dirname "$RUNTIME_CONFIG")"
cat > "$RUNTIME_CONFIG" <<'TOML'
[data]
build_mode = false
TOML
```

Replace with:

```bash
mkdir -p "$(dirname "$RUNTIME_CONFIG")"
# Render the chezmoi config from the source-root template (.chezmoi.toml.tmpl)
# via `chezmoi execute-template --init`. build_mode is driven by BUILD_MODE env
# (unset here -> false, the runtime value). The config content lives in the
# dotfiles, not hardcoded in this script. Fail loudly if the template is
# missing (an older/incomplete source bind) — the entrypoint cannot produce a
# valid config without it.
CONFIG_TEMPLATE="${CHEZMOI_SOURCE}/.chezmoi.toml.tmpl"
if [[ ! -f "$CONFIG_TEMPLATE" ]]; then
  echo "entrypoint: $CONFIG_TEMPLATE is missing — cannot render chezmoi.toml." >&2
  echo "entrypoint: did make up bind the repo root (with .chezmoi.toml.tmpl) into ~/.local/share/chezmoi?" >&2
  exit 1
fi
chezmoi execute-template --init \
  < "$CONFIG_TEMPLATE" \
  > "$RUNTIME_CONFIG"
```

- [ ] **Step 2: Update the entrypoint header comment (step 2 description)**

In the same file, find the comment block near the top:

```bash
#   2. Re-renders ~/.config/chezmoi/chezmoi.toml with build_mode = false
#      (the build-prepass toml is stripped in the runtime cleanup,
#      Layer 5-4, so this creates it fresh as ${USERNAME}).
```

Replace with:

```bash
#   2. Renders ~/.config/chezmoi/chezmoi.toml from the source-root template
#      (.chezmoi.toml.tmpl) via `chezmoi execute-template --init`
#      (build_mode = false; BUILD_MODE unset at runtime). The build-prepass
#      toml is stripped in the runtime cleanup (Layer 5-3), so this creates
#      it fresh as ${USERNAME}.
```

(Note: the previous comment said "Layer 5-4"; the strip is in Layer 5-3 per the current Containerfile — fix the layer number here too.)

- [ ] **Step 3: Rebuild**

```bash
cd /data/dotfiles3
make build 2>&1 | tail -3
```

Expected: green, new image ID.

- [ ] **Step 4: `make up` with `bw_*` secrets — verify runtime config + apply + secrecy**

```bash
cd /data/dotfiles3
make down 2>/dev/null | tail -1
make up 2>&1 | tail -1
sleep 14
echo "=== status ==="
podman ps -a --filter name=dotfiles-manjaro --format '{{.Names}} {{.Status}}'
echo "=== logs (quiet) ==="
(podman logs dotfiles-manjaro 2>&1 | rg -qi 'error|permission denied|empty session|missing.*cannot render' && echo HAS_ISSUE || echo OK)
echo "=== runtime chezmoi.toml ==="
podman exec dotfiles-manjaro sh -c 'cat ~/.config/chezmoi/chezmoi.toml; ls -l ~/.config/chezmoi/chezmoi.toml'
```

Expected:
- Status `Up`.
- Logs: no error (auth OK, no "missing ... cannot render").
- `~/.config/chezmoi/chezmoi.toml` =
  ```
  [data]
  build_mode = false
  ```
  owned by `kiyama` (USERNAME).

- [ ] **Step 5: Secrecy + toolchain persistence (quiet)**

```bash
cd /data/dotfiles3
echo "=== BUILD_MODE not in inspect/image Env (I3) ==="
(podman inspect dotfiles-manjaro --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -qiE 'BUILD_MODE' && echo FAIL || echo OK_INSPECT)
(podman image inspect localhost/dotfiles-manjaro:latest --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -qiE 'BUILD_MODE' && echo FAIL || echo OK_IMAGE)
echo "=== all-proc environ: no BW_* ==="
found=0; for pid in $(podman exec dotfiles-manjaro sh -c 'ls /proc 2>/dev/null | grep -E "^[0-9]+$"'); do podman exec dotfiles-manjaro sh -c "cat /proc/$pid/environ 2>/dev/null | tr '\0' '\n' | grep -qiE 'BW_CLIENTID|BW_CLIENTSECRET|BW_SESSION|BW_PASSWORD|BW_MASTERPASS'" && { echo "LEAK_PID_$pid"; found=1; }; done; [ $found -eq 0 ] && echo OK_ALL_CLEAN || echo FAIL
echo "=== toolchain ==="
podman exec dotfiles-manjaro zsh -lc 'rustc --version' 2>/dev/null
```

Expected: `OK_INSPECT`, `OK_IMAGE`, `OK_ALL_CLEAN`, `rustc 1.96.0 ...`.

- [ ] **Step 6: No-secret startup (S4 path)** — skip removing the user's real secrets; instead verify the entrypoint guard logic is gated on `/run/secrets/bw_password` (unchanged) and the config render is unconditional. Confirm via the logs above (auth block skipped when no secrets is already covered by prior work; the config render runs regardless). If a no-secret run is desired without destroying the user's secrets, temporarily test by checking the entrypoint source path is not gated on secrets:

```bash
cd /data/dotfiles3
rg -n 'CONFIG_TEMPLATE|chezmoi execute-template|/run/secrets/bw_password' container/bind/layer_5_files/entrypoint.sh
```

Expected: the config render block is OUTSIDE the `/run/secrets/bw_password` `if` (i.e. config render is unconditional; auth is the only secret-gated part).

- [ ] **Step 7: Commit**

```bash
cd /data/dotfiles3
git add container/bind/layer_5_files/entrypoint.sh
git commit -m "feat(entrypoint): render chezmoi.toml from .chezmoi.toml.tmpl via execute-template --init (drop heredoc); guard on template presence"
```

**Acceptance:** `make up` → `Up`, runtime `chezmoi.toml = build_mode = false` (USERNAME-owned), no `BUILD_MODE` in inspect/image, no `BW_*` in any environ, toolchain persists.
**Rollback:** revert the entrypoint change.

---

## Phase 4 — Specs + comments sync

**Files:**
- Modify: `docs/specifications/01-file-structures.md`, `docs/specifications/13-secret-management.md`, `docs/specifications/20-container-rules.md`, `docs/specifications/21-container-build-flow.md`

**Interfaces:**
- Consumes: the implemented flow from Phases 2-3.
- Produces: specs consistent with the implementation.

- [ ] **Step 1: `01-file-structures.md` — remove `layer_2_files/`, add `.chezmoi.toml.tmpl`**

Find:

```
│       ├── layer_1_files/
│       │   └── pacman_mirrorlist  # Layer 1 pacman mirrorlist (Stage 1-2)
│       ├── layer_2_files/
│       │   └── chezmoi.toml       # build-prepass chezmoi config (`build_mode = true`; Stage 2 COPY)
│       └── layer_5_files/
│           └── entrypoint.sh  # runtime chezmoi-apply entrypoint (Stage 5-4; see 21-...md)
```

Replace with:

```
│       ├── layer_1_files/
│       │   └── pacman_mirrorlist  # Layer 1 pacman mirrorlist (Stage 1-2)
│       └── layer_5_files/
│           └── entrypoint.sh  # runtime chezmoi-apply entrypoint (Stage 5-4; see 21-...md)
```

And in the repo-root (chezmoi source root) tree, add `.chezmoi.toml.tmpl` next to `.chezmoiignore`. Find the `.chezmoiignore` line:

```
├── .chezmoiignore      # chezmoi ignore rules
```

Replace with:

```
├── .chezmoiignore      # chezmoi ignore rules
├── .chezmoi.toml.tmpl  # chezmoi config template (build_mode via BUILD_MODE env; rendered by `chezmoi execute-template --init`)
```

- [ ] **Step 2: `13-secret-management.md §5a` — rewrite the `build_mode` mechanism**

Find:

```
The `build_mode` data flag (set in `chezmoi.toml`: the build-prepass
`bind/layer_2_files/chezmoi.toml` is COPY'd by Containerfile Stage 2
with `build_mode = true`; the runtime `~/.config/chezmoi/chezmoi.toml`
is written by the entrypoint with `build_mode = false`) is the single
switch. For any dotfile, ask: **does Stage 3 need to source this to get
the toolchain ENV?**
```

Replace with:

```
The `build_mode` data flag is the single switch. It is set in
`~/.config/chezmoi/chezmoi.toml`, which is rendered from a single
dotfiles-managed config template `.chezmoi.toml.tmpl` (chezmoi source
root) by `chezmoi execute-template --init`: the Containerfile Stage 2
build-prepass renders it with `BUILD_MODE=true` (inline in the `RUN`, not
`ENV`), the runtime entrypoint renders it with `BUILD_MODE` unset
(`false`). The template cannot read `[data]` it is generating, so
`build_mode` is read from the `BUILD_MODE` env var
(`{{ env "BUILD_MODE" | default "false" }}`). For any dotfile, ask:
**does Stage 3 need to source this to get the toolchain ENV?**
```

- [ ] **Step 3: `21-container-build-flow.md` — Stage 2 row + notes**

Find the build-prepass table row (the one Phase-4-of-the-prior-PR edited):

```
| `build-prepass` (`FROM base`) | 2 | `COPY --from=srcroot`; `COPY bind/layer_2_files/chezmoi.toml` -> `~/.config/chezmoi/chezmoi.toml` (`build_mode = true`); `chezmoi apply --destination /tmp/build-home` | Scratch render of ENV-bearing dotfiles with `build_mode = true`; secret-free. | `srcroot` named build-context, `bind/layer_2_files/chezmoi.toml` |
```

Replace with:

```
| `build-prepass` (`FROM base`) | 2 | `COPY --from=srcroot`; `BUILD_MODE=true chezmoi execute-template --init < /tmp/chezmoi-src/.chezmoi.toml.tmpl > ~/.config/chezmoi/chezmoi.toml` (`build_mode = true`); `chezmoi apply --destination /tmp/build-home` | Scratch render of ENV-bearing dotfiles with `build_mode = true`; secret-free. | `srcroot` named build-context, `.chezmoi.toml.tmpl` |
```

Find the notes paragraph that mentions `bind/layer_2_files/chezmoi.toml`:

```
  (`build_mode = true`, `COPY`'d from `bind/layer_2_files/chezmoi.toml`
  as root) rides the Stage chain (`toolchain` -> `aur` -> `runtime`)
  into the runtime image and is **stripped** in Layer 5-3 (not
  replaced); the runtime `~/.config/chezmoi/chezmoi.toml`
  (`build_mode = false`) is **created fresh by the entrypoint** as
  `${USERNAME}` before `chezmoi apply` (see acceptance #5a / invariant
  I10).
```

Replace with:

```
  (`build_mode = true`, rendered from `.chezmoi.toml.tmpl` by
  `chezmoi execute-template --init` with `BUILD_MODE=true`, USERNAME-owned)
  rides the Stage chain (`toolchain` -> `aur` -> `runtime`) into the
  runtime image and is **stripped** in Layer 5-3 (not replaced); the
  runtime `~/.config/chezmoi/chezmoi.toml` (`build_mode = false`) is
  **re-rendered from the same `.chezmoi.toml.tmpl` by the entrypoint**
  (BUILD_MODE unset) as `${USERNAME}` before `chezmoi apply` (see
  acceptance #5a / invariant I10).
```

- [ ] **Step 4: `20-container-rules.md I10` — runtime config rendered from template**

Find the I10 sentence that says the runtime config is "created fresh by the entrypoint":

```
  (`build_mode = true`, root-owned, `COPY`'d from `bind/layer_2_files/chezmoi.toml`) rides the Stage chain into the runtime image and is **stripped** in Layer 5-3; the runtime `~/.config/chezmoi/chezmoi.toml` (`build_mode = false`) is **created fresh by the entrypoint** as `${USERNAME}` before `chezmoi apply`.
```

Replace with:

```
  (`build_mode = true`, rendered from `.chezmoi.toml.tmpl` by `chezmoi execute-template --init` with `BUILD_MODE=true`, USERNAME-owned) rides the Stage chain into the runtime image and is **stripped** in Layer 5-3; the runtime `~/.config/chezmoi/chezmoi.toml` (`build_mode = false`) is **re-rendered from the same `.chezmoi.toml.tmpl` by the entrypoint** (`BUILD_MODE` unset) as `${USERNAME}` before `chezmoi apply`. `BUILD_MODE` is inline in the Stage 2 `RUN` (not `ENV`), so it never appears in image `Env` / `podman inspect`.
```

- [ ] **Step 5: Verify no stale `layer_2_files` / heredoc references remain in specs**

```bash
cd /data/dotfiles3
rg -n 'layer_2_files|bind/layer_2|cat >.*chezmoi.toml|heredoc.*chezmoi|chezmoi.toml.*heredoc' docs/specifications/ docs/issues/ docs/plans/ 2>/dev/null
```

Expected: no matches in specs 01/13/20/21 (the design/plan/issue for THIS topic may still mention them as the "old" state — that's fine; the authoritative specs must not).

- [ ] **Step 6: Commit**

```bash
cd /data/dotfiles3
git add docs/specifications/01-file-structures.md docs/specifications/13-secret-management.md docs/specifications/20-container-rules.md docs/specifications/21-container-build-flow.md
git commit -m "docs: sync specs 01/13/20/21 to .chezmoi.toml.tmpl config template (drop bind/layer_2_files + heredoc wording)"
```

**Acceptance:** specs 01/13/20/21 describe the `.chezmoi.toml.tmpl` + `execute-template --init` + `BUILD_MODE` mechanism; no stale `layer_2_files`/heredoc references in authoritative specs.
**Rollback:** revert the doc commits.

---

## Phase 5 — E2E smoke gate + result-log + close issue

**Files:**
- Create: `docs/issues/2026-06-30-phase-chezmoi-config-template.md` (result-log)
- Modify: `docs/issues/2026-06-30-chezmoi-config-template.md` (status → closed)

- [ ] **Step 1: Final rebuild + full smoke gate**

```bash
cd /data/dotfiles3
make build 2>&1 | tail -3
make down 2>/dev/null | tail -1
make up 2>&1 | tail -1
sleep 14
podman ps -a --filter name=dotfiles-manjaro --format '{{.Names}} {{.Status}}'
podman exec dotfiles-manjaro sh -c 'cat ~/.config/chezmoi/chezmoi.toml'
```

Expected: build green; `Up`; `chezmoi.toml` = `build_mode = false`.

- [ ] **Step 2: Baked-state + restart + env-leak consolidated check**

```bash
cd /data/dotfiles3
echo "=== baked (entrypoint bypassed): no chezmoi.toml, .zshenv present ==="
podman run --rm --entrypoint /bin/sh localhost/dotfiles-manjaro:latest -c 'ls ~/.config/chezmoi/ 2>&1; ls -l ~/.zshenv'
echo "=== restart reliability ==="
make down 2>/dev/null | tail -1; make up 2>&1 | tail -1; sleep 14
podman ps --filter name=dotfiles-manjaro --format '{{.Status}}'
(podman logs dotfiles-manjaro 2>&1 | rg -qi 'error|missing.*cannot render' && echo HAS_ISSUE || echo OK)
podman exec dotfiles-manjaro sh -c 'grep build_mode ~/.config/chezmoi/chezmoi.toml'
echo "=== env leak (BUILD_MODE) + secrecy ==="
(podman inspect dotfiles-manjaro --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -qiE 'BUILD_MODE|BW_CLIENT|BW_PASSWORD|BW_SESSION' && echo FAIL || echo OK)
(podman image inspect localhost/dotfiles-manjaro:latest --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -qiE 'BUILD_MODE|BW_CLIENT|BW_PASSWORD|BW_SESSION|BW_MASTER' && echo FAIL || echo OK)
```

Expected: baked image has no `chezmoi.toml` (stripped) but has `.zshenv`; restart `Up`, no error, `build_mode = false`; `OK` / `OK` (no BUILD_MODE, no BW_* in inspect/image Env).

- [ ] **Step 3: Host-safety check (S10)**

```bash
cd /data/dotfiles3
echo "=== host render (BUILD_MODE unset) ==="
podman run --rm --entrypoint /bin/sh localhost/dotfiles-manjaro:latest -c 'chezmoi execute-template --init < /dev/stdin' < .chezmoi.toml.tmpl
```

Expected: prints `build_mode = false` (the host/runtime value). (This confirms a host `chezmoi init` would render the correct runtime config; a host `chezmoi apply` with an existing config is unaffected because `apply` does not re-render the config template.)

- [ ] **Step 4: Write the result-log**

Create `docs/issues/2026-06-30-phase-chezmoi-config-template.md` with: summary, acceptance evidence table (S1–S11 → PASS + the actual check output paraphrased), the Q1 outcome (env works in `execute-template --init`), the Q2 outcome (guard added), commit trail, and any deviations/follow-ups. Do NOT print any credential values.

- [ ] **Step 5: Close the issue**

In `docs/issues/2026-06-30-chezmoi-config-template.md`, change `**Status:** open` to `**Status:** closed (see [result-log](2026-06-30-phase-chezmoi-config-template.md))`.

- [ ] **Step 6: Commit + push**

```bash
cd /data/dotfiles3
make down 2>/dev/null | tail -1
git add docs/issues/2026-06-30-phase-chezmoi-config-template.md docs/issues/2026-06-30-chezmoi-config-template.md
git commit -m "docs: close chezmoi-config-template issue with result-log (.chezmoi.toml.tmpl verified)"
git push origin develop 2>&1 | tail -3
```

**Acceptance:** all S1–S11 pass; result-log written; issue closed; develop pushed.
**Rollback:** N/A (verification-only phase; revert earlier phases if a criterion fails).

---

## Self-Review

**Spec coverage:** S1 (template) → Phase 1; S2 (BUILD_MODE) → Phase 1/2/3; S3 (execute-template --init) → Phase 2/3; S4 (remove layer_2_files) → Phase 2; S5 (inline BUILD_MODE) → Phase 2 + verified Phase 3/5; S6 (Layer 5-3 strip preserved) → Phase 3 (no change to strip) + verified Phase 5; S7 (build green, .chezmoi.toml.tmpl ignored) → Phase 2/5; S8 (make up ±secrets) → Phase 3/5; S9 (build-prepass build_mode=true) → Phase 2; S10 (host safety) → Phase 5; S11 (specs) → Phase 4. All covered.

**Placeholder scan:** No TBD/TODO in steps (the issue's plan link "TBD" is in the issue, not this plan). Q1/Q2 from the design are resolved by Phase 1 (Q1) and Phase 3 (Q2). All code blocks contain actual content.

**Type consistency:** `CONFIG_TEMPLATE="${CHEZMOI_SOURCE}/.chezmoi.toml.tmpl"` (Phase 3) matches `${CHEZMOI_SOURCE}` already defined in `entrypoint.sh` (`CHEZMOI_SOURCE="${HOME}/.local/share/chezmoi"`). `RUNTIME_CONFIG` is the existing variable. `.chezmoi.toml.tmpl` path consistent across phases (`/tmp/chezmoi-src/.chezmoi.toml.tmpl` build; `${CHEZMOI_SOURCE}/.chezmoi.toml.tmpl` runtime).