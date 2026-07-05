# Container Locale Gen — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** executed
**Spec:** [`docs/specifications/21-container-build-flow.md`](../specifications/21-container-build-flow.md), [`docs/specifications/20-container-rules.md`](../specifications/20-container-rules.md)
**Parent issue:** Direct user request (2026-07-04; no issue file opened)
**Review trail:** Task and final reviews in `.superpowers/sdd` are local execution artifacts for this direct request.

**Goal:** Generate exactly the container image locales required by the existing `.zshenv` defaults so `ja_JP.UTF-8` and `en_US.UTF-8` work inside the Manjaro Podman image without generating extra `/etc/locale.gen` entries inherited from the base image.

**Architecture:** Extend `container/Containerfile` Layer 1-2, while it is still running as root, to comment out any currently enabled `/etc/locale.gen` entries, append exactly the two required UTF-8 locale entries, run `locale-gen`, and write `/etc/locale.conf`. Update the container build-flow spec so Layer 1-2 documents locale generation as part of base OS setup. No host-side chezmoi script is added.

**Tech Stack:** Manjaro base image, Arch/Manjaro `locale-gen`, Podman, Makefile-driven container build, Markdown specs.

## Global Constraints

- Scope is container-only; do not add host `locale-gen` scripts or host `/etc/locale.gen` management.
- Generate exactly `ja_JP.UTF-8 UTF-8` and `en_US.UTF-8 UTF-8`, matching `LANG=ja_JP.UTF-8` and `LC_CTYPE=en_US.UTF-8` in `dot_zshenv.tmpl`.
- Keep package installation sourced from `dependencies/packages.toml` and generated `dependencies/layer_<N>/<manager>.txt`; do not add ad-hoc package installs.
- Keep the image secret-free; locale setup must not read Bitwarden, `.env`, host files outside existing build contexts, or runtime secrets.
- Use `make build` for the full verification path; it is the repository-authorized target for `podman build`.
- Do not create a git commit unless the user explicitly asks for one.

## Phases

### Phase 1 — Generate Locales During Container Build

**Files:**
- Modify: `container/Containerfile`
- Reference: `dot_zshenv.tmpl`

**Interfaces:**
- Consumes: existing `/tmp/pacman_deps.txt` package install flow in Layer 1-2; existing locale env exports in `dot_zshenv.tmpl`.
- Produces: exactly two uncommented image-level `/etc/locale.gen` entries (`ja_JP.UTF-8 UTF-8` and `en_US.UTF-8 UTF-8`), generated locale archive, and `/etc/locale.conf` containing `LANG=ja_JP.UTF-8`.

- [x] **Step 1: Confirm the target locale environment**

  Run:

  ```bash
  rg -n 'LANG|LC_CTYPE|LANGUAGE' dot_zshenv.tmpl
  ```

  Expected output includes:

  ```text
  66:    export LANG="${LANG:-ja_JP.UTF-8}"
  67:    export LC_CTYPE=en_US.UTF-8
  68:    export LANGUAGE=ja_JP.UTF-8:en_US.UTF-8:C # fallback
  ```

- [x] **Step 2: Update Layer 1-2 comments**

  In `container/Containerfile`, describe Layer 1-2 as seeding the mirrorlist, installing the Layer 1 pacman package set, and generating the UTF-8 locales used by `dot_zshenv.tmpl`.

- [x] **Step 3: Add locale generation to the Layer 1-2 `RUN`**

  In `container/Containerfile`, extend the Layer 1-2 package install command:

  ```dockerfile
  RUN --mount=type=cache,target=/var/cache/pacman/pkg \
      pacman -Syu --noconfirm --needed $(sed 's/#.*//' /tmp/pacman_deps.txt | xargs) \
 && sed -i -e '/^[[:space:]]*[^#[:space:]]/ s/^/#/' /etc/locale.gen \
 && printf '%s\n' 'ja_JP.UTF-8 UTF-8' 'en_US.UTF-8 UTF-8' >> /etc/locale.gen \
   && locale-gen \
   && printf 'LANG=ja_JP.UTF-8\n' > /etc/locale.conf
  ```

  Expected behavior:

  - Any locale entries already uncommented by the base image are commented out before locale generation.
  - Exactly `ja_JP.UTF-8 UTF-8` and `en_US.UTF-8 UTF-8` are appended as the only enabled `/etc/locale.gen` entries.
  - `locale-gen` generates both UTF-8 locales in the image.
  - `/etc/locale.conf` sets the system default `LANG` without forcing `LC_ALL`.

- [x] **Step 4: Build the image**

  Run:

  ```bash
  make build
  ```

  Expected result: command exits 0 and tags `localhost/dotfiles-manjaro:latest`.

- [x] **Step 5: Verify generated locales in a one-shot container**

  Run:

  ```bash
  podman run --rm --entrypoint /usr/bin/env localhost/dotfiles-manjaro:latest zsh -lc 'awk "BEGIN { n=0 } /^[[:space:]]*($|#)/ { next } { enabled[++n]=\$0 } END { if (n != 2 || enabled[1] != \"ja_JP.UTF-8 UTF-8\" || enabled[2] != \"en_US.UTF-8 UTF-8\") exit 1 }" /etc/locale.gen && locale -a | sort | awk "/^(en_US|ja_JP)\\.utf8$/ { print }"; printf "LANG=%s\nLC_CTYPE=%s\n" "$LANG" "$LC_CTYPE"; locale charmap'
  ```

  Expected output includes:

  ```text
  en_US.utf8
  ja_JP.utf8
  LANG=ja_JP.UTF-8
  LC_CTYPE=en_US.UTF-8
  UTF-8
  ```

- [x] **Step 6: Check the build no longer emits locale warnings**

  Run:

  ```bash
  make build 2>&1 | tee /tmp/dotfiles3-locale-build.log
  rg 'setlocale|cannot change locale|No such file or directory' /tmp/dotfiles3-locale-build.log
  ```

  Expected result: no matching lines. `rg` exits 1 when there are no matches; that is the desired result for this check.

**Acceptance:** `make build` exits 0; the final image has exactly two uncommented `/etc/locale.gen` entries (`ja_JP.UTF-8 UTF-8` and `en_US.UTF-8 UTF-8`); the final image contains both `ja_JP.utf8` and `en_US.utf8`; `LANG=ja_JP.UTF-8`, `LC_CTYPE=en_US.UTF-8`, and `locale charmap` reports `UTF-8`; the build log has no locale warning matches.

**Rollback:** Revert the Layer 1-2 comment and `RUN` changes in `container/Containerfile`, then rebuild with `make build` to return to the previous image behavior.

### Phase 2 — Update Container Build-Flow Documentation

**Files:**
- Modify: `docs/specifications/21-container-build-flow.md`
- Modify: `docs/specifications/20-container-rules.md`

**Interfaces:**
- Consumes: Phase 1's Containerfile behavior for Layer 1-2.
- Produces: updated normative documentation that says Layer 1-2 installs Layer 1 pacman packages and generates exactly the two UTF-8 locales used by `.zshenv`; spec 20 points to the build-flow locale acceptance coverage.

- [x] **Step 1: Update the Layer 1-2 stage-ordering row**

  In `docs/specifications/21-container-build-flow.md`, update the Layer 1-2 row to describe `mirrorlist + pacman -Syu + /etc/locale.gen reset + locale-gen`, with exactly `ja_JP.UTF-8` and `en_US.UTF-8` generation for `.zshenv`.

- [x] **Step 2: Add a current-state note for locale generation**

  In `docs/specifications/21-container-build-flow.md`, under `### Notes on the current state`, document that `base` Layer 1-2 comments out any enabled `/etc/locale.gen` entries, then generates exactly `ja_JP.UTF-8` and `en_US.UTF-8` before later stages source the rendered `.zshenv`.

- [x] **Step 3: Add an acceptance criterion for locale availability**

  In `docs/specifications/21-container-build-flow.md`, under `## Acceptance criteria`, add the locale availability criterion:

  ```markdown
  The final image generates exactly the `/etc/locale.gen` entries used by
  `.zshenv`: the only uncommented entries are `ja_JP.UTF-8 UTF-8` and
  `en_US.UTF-8 UTF-8`; `locale -a` inside
  `localhost/dotfiles-manjaro:latest` includes `ja_JP.utf8` and
  `en_US.utf8`; and `locale charmap` under a `zsh` command environment
  reports `UTF-8`.
  ```

- [x] **Step 4: Update container rules acceptance traceability**

  In `docs/specifications/20-container-rules.md`, reference the spec-21 locale acceptance criterion so the container rules spec points to the normative build-flow verification.

- [x] **Step 5: Verify documentation references are consistent**

  Run:

  ```bash
  rg -n 'locale-gen|ja_JP|en_US|Layer 1-2' container/Containerfile docs/specifications/21-container-build-flow.md docs/specifications/20-container-rules.md dot_zshenv.tmpl
  ```

  Expected output includes references from `container/Containerfile`, `docs/specifications/21-container-build-flow.md`, `docs/specifications/20-container-rules.md`, and `dot_zshenv.tmpl`.

**Acceptance:** The normative specs describe the same exact locale behavior implemented in `container/Containerfile`; `rg` finds the locale terms in the implementation, build-flow spec, container rules spec, and `.zshenv` template.

**Rollback:** Revert only the locale-related documentation edits in `docs/specifications/21-container-build-flow.md` and `docs/specifications/20-container-rules.md`. If Phase 1 is also rolled back, remove the locale acceptance criterion from spec 21 at the same time.

### Phase 3 — Final Verification And Handoff

**Files:**
- Verify: `container/Containerfile`
- Verify: `docs/specifications/20-container-rules.md`
- Verify: `docs/specifications/21-container-build-flow.md`
- Verify: `dot_zshenv.tmpl`
- Update: `docs/plans/2026-07-04-container-locale-gen-impl.md`
- Update: `.superpowers/sdd/task-3-report.md`

**Interfaces:**
- Consumes: Phase 1 image behavior and Phase 2 documentation.
- Produces: a verified working tree ready for user review or an explicit user-requested commit.

- [x] **Step 1: Inspect the working tree**

  Run:

  ```bash
  git status --short
  git diff -- container/Containerfile docs/specifications/21-container-build-flow.md docs/specifications/20-container-rules.md docs/plans/2026-07-04-container-locale-gen-impl.md
  ```

  Expected result:

  - `container/Containerfile` only changes Layer 1-2 comments and the Layer 1-2 `RUN`.
  - `docs/specifications/21-container-build-flow.md` documents the locale generation behavior.
  - `docs/specifications/20-container-rules.md` references the spec-21 locale acceptance coverage.
  - `docs/plans/2026-07-04-container-locale-gen-impl.md` contains this implementation plan.

- [x] **Step 2: Run the dependency generator test suite**

  Run:

  ```bash
  make test-deps
  ```

  Expected output:

  ```text
  python3 -m pytest programs/generate_deps/tests/ -q
  ```

  The pytest summary must exit 0. This change should not affect dependency generation; this check guards accidental package-list edits.

- [x] **Step 3: Run the container verification command**

  Run:

  ```bash
  podman run --rm --entrypoint /usr/bin/env localhost/dotfiles-manjaro:latest zsh -lc 'awk "BEGIN { n=0 } /^[[:space:]]*($|#)/ { next } { enabled[++n]=\$0 } END { exit (n == 2 && enabled[1] == \"ja_JP.UTF-8 UTF-8\" && enabled[2] == \"en_US.UTF-8 UTF-8\") ? 0 : 1 }" /etc/locale.gen && test "$(locale charmap)" = UTF-8 && locale -a | awk "BEGIN { ja=0; en=0 } /^ja_JP\\.utf8$/ { ja=1 } /^en_US\\.utf8$/ { en=1 } END { exit (ja && en) ? 0 : 1 }"'
  ```

  Expected result: the command exits 0 and prints no output; `/etc/locale.gen` has exactly the two target uncommented entries.

- [x] **Step 4: Verify the plan schema**

  Run:

  ```bash
  rg -n '^\*\*(Status|Spec|Parent issue|Review trail):\*\*|^## Phases$|^### Phase [0-9]+|^\*\*Acceptance:\*\*|^\*\*Rollback:\*\*' docs/plans/2026-07-04-container-locale-gen-impl.md
  ```

  Expected result: the plan has all required metadata fields, `## Phases`, and one `Acceptance` plus one `Rollback` label for each phase.

- [x] **Step 5: Report status without committing**

  Report:

  ```text
  Implemented container-only locale generation for exactly ja_JP.UTF-8 and en_US.UTF-8. Verified with make build, make test-deps, exact /etc/locale.gen and locale checks inside localhost/dotfiles-manjaro:latest, and a focused plan-schema rg check. No commit was created.
  ```

**Acceptance:** `make test-deps` exits 0; the one-shot container locale command exits 0 and verifies exactly the two uncommented `/etc/locale.gen` entries; the focused `rg` schema check finds `Status`, `Spec`, `Parent issue`, `Review trail`, `## Phases`, and phase-level `Acceptance`/`Rollback` labels; no commit is created.

**Rollback:** Revert the documentation-only schema rewrite in `docs/plans/2026-07-04-container-locale-gen-impl.md` and remove the appended schema-fix note from `.superpowers/sdd/task-3-report.md`. This rollback does not affect the already-built image or container implementation files.

## Self-Review Notes

- Spec coverage: container-only scope, `dot_zshenv.tmpl` locale alignment, build-flow documentation, container-rule traceability, and verification are all covered by Phases 1-3.
- Placeholder scan: the plan contains no deferred implementation markers; each edit and command is concrete.
- Interface consistency: Phase 2 documents the exact behavior implemented by Phase 1; Phase 3 verifies the same image tag produced by `make build`.
