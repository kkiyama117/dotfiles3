# Migrate `herdr` to mise management — Design

**Status:** Approved
**Date opened:** 2026-07-15
**Issue:** [`../../issues/2026-07-15-herdr-mise-management.md`](../../issues/2026-07-15-herdr-mise-management.md)
**Author:** kiyama
**Review required:** letter A + C + E (changes Containerfile, build flow, and
mise/volume semantics; see [`../09-review.md`](../09-review.md) §2.2)
**Review trail:** [`../../reviews/2026-07-15-herdr-mise-management-review-pass1-A-factual.md`](../../reviews/2026-07-15-herdr-mise-management-review-pass1-A-factual.md),
[`../../reviews/2026-07-15-herdr-mise-management-review-pass1-C-architecture.md`](../../reviews/2026-07-15-herdr-mise-management-review-pass1-C-architecture.md),
[`../../reviews/2026-07-15-herdr-mise-management-review-pass1-E-operability.md`](../../reviews/2026-07-15-herdr-mise-management-review-pass1-E-operability.md),
[`../../reviews/2026-07-15-herdr-mise-management-review-pass1.md`](../../reviews/2026-07-15-herdr-mise-management-review-pass1.md)
**Supersedes:** [`2026-07-15-herdr-container-install-design.md`](2026-07-15-herdr-container-install-design.md)
(the closed container-install design and its issue/result-log/plan remain as
historical evidence — not edited in this phase)

## Finding-response summary

- **A1** (`§1` aqua-prefix precedent wording): **addressed** — narrowed the
  precedent claim to the existing `"npm:@earendil-works/pi-coding-agent"`
  explicit-backend-prefix entry; `node`/`go`/`python` are now described as
  bare core-tool names.
- **A2** (`§5.4` TOML snippet for `.yml`): **addressed** — clarified that
  both `dot_config/herdr/config.toml` and `config.yml` are TOML-formatted
  despite the extension, and the same TOML `[update]` block is applied to
  both. No YAML syntax invented.
- **A3** (`§8 Q1` enumerated tool list): **addressed** — replaced the
  broader tool enumeration with what the 2026-07-15 result-log directly
  proves: a successful full five-stage build plus a working Layer 3-4
  mise-dependent path (`pi --version` PASS implies `mise exec node@latest`
  / aqua `pnpm` success).
- **C findings:** no blockers; **Approve**. Noted config-verification
  asymmetry and PATH-precedence risk are acknowledged and mitigated in
  §6.2.
- **E findings:** no blockers; **Approve**. E1/E2 residual risks retained in
  design §6.1/§8 Q1; 2026-07-09 issue is stale evidence relative to the
  2026-07-15 successful build.

## §1 Context & success criteria

On 2026-07-15 the repository shipped `herdr` v0.7.3 via Containerfile
Layer 3-8: a version-pinned + SHA256-gated curl bootstrap to
`~/.local/bin/herdr`, declared `manager = "custom"`, `layer = 3` in
`dependencies/packages.toml`. That work is closed
([`../../issues/2026-07-15-herdr-container-install.md`](../../issues/2026-07-15-herdr-container-install.md),
[`../../issues/2026-07-15-phase-herdr-container-install.md`](../../issues/2026-07-15-phase-herdr-container-install.md)).

The container toolchain already installs mise-managed tools from the
chezmoi-rendered [`../../../dot_config/mise/config.toml`](../../../dot_config/mise/config.toml)
at Layer 3-4 (`mise install --yes`; see
[`../21-container-build-flow.md`](../21-container-build-flow.md) Layer 3-4).
`dot_zshenv.tmpl` activates mise shims (`eval "$(mise activate zsh --shims)"`);
`MISE_DATA_DIR` defaults to `~/.local/share/mise`, the `dotfiles_mise` named
volume mountpoint. Upstream lists mise among official `herdr` install paths
and disables self-update when installed under mise.

Mise config facts (verified 2026-07-15):

- [`../../../dot_config/mise/config.toml`](../../../dot_config/mise/config.toml)
  sets `disable_default_registry = true`, so tools from the default aqua
  registry must use an explicit `aqua:<owner>/<repo>` key in `[tools]` —
  a bare `herdr = "latest"` would not resolve.
- The existing `[tools]` entry `"npm:@earendil-works/pi-coding-agent" =
  "latest"` already demonstrates the explicit-backend-prefix pattern that
  `disable_default_registry = true` requires; `node`, `go`, `python`, etc.
  are bare core-tool names resolved without a prefix. `herdr` joins the
  explicit-prefix group as `"aqua:ogulcancelik/herdr" = "latest"`.
- Layer 3-4 copies `/tmp/build-home/.config/mise/config.toml` into
  `${XDG_CONFIG_HOME}/mise/config.toml` and runs `mise install --yes`; installs
  land under `$MISE_DATA_DIR/installs/` and shims under
  `$MISE_DATA_DIR/shims/`.

Approved product decisions for this migration:

- **mise is the sole install/version/update authority** on host and container.
- **`latest` policy** in mise config; ongoing upgrades via
  `mise upgrade aqua:ogulcancelik/herdr`, not image rebuilds or `herdr
  update`.
- **Disable Herdr's own update checks** in chezmoi-managed config and set
  `[update] channel = "stable"` as a defense-in-depth default.
- **Remove** the `packages.toml` `custom` entry and Containerfile Layer 3-8.
- **Preserve** the closed container-install issue, result-log, plan, and old
  design as history; mark the old design `superseded` during implementation.
- **One-time `dotfiles_mise` volume recreation** for existing deployments;
  later upgrades do not require volume removal.

Success criteria:

- **S1** [`../../../dot_config/mise/config.toml`](../../../dot_config/mise/config.toml)
  gains `"aqua:ogulcancelik/herdr" = "latest"` under `[tools]`.
- **S2** `dependencies/packages.toml` no longer declares `herdr`; `make
  gen-deps` removes `herdr` from the spec 02 AUTO-GEN block (no Layer 3
  `custom` row).
- **S3** Containerfile Layer 3-8 (`ARG HERDR_VERSION` / `ARG HERDR_SHA256`,
  curl + `sha256sum` + `install` to `~/.local/bin/herdr`) is deleted; `herdr`
  is installed only by Layer 3-4 `mise install --yes` alongside other
  mise-managed tools.
- **S4** [`../../../dot_config/herdr/config.toml`](../../../dot_config/herdr/config.toml)
  and [`../../../dot_config/herdr/config.yml`](../../../dot_config/herdr/config.yml)
  set `[update] channel = "stable"`, `version_check = false`, and
  `manifest_check = false`. Herdr MUST NOT treat its own channel/checks as
  an upgrade authority; mise is the sole update path.
- **S5** After `make build` and rollout (§6), `podman exec <c> zsh -ic 'herdr
  --version'` exits 0; `which herdr` resolves under `$MISE_DATA_DIR/shims`,
  not `~/.local/bin/herdr`.
- **S6** `make down && make up` preserves `herdr` across restarts once the
  aqua install is present in `dotfiles_mise` (named-volume persistence, analog
  of spec 21 acceptance #14).
- **S7** Specs 02, 20, and 21 are updated: I-HERDR1..I-HERDR3 and Layer 3-8
  rows/acceptance #25 are replaced with mise-based invariants and acceptance
  criteria; spec 21 documents the one-time `dotfiles_mise` migration.
- **S8** [`2026-07-15-herdr-container-install-design.md`](2026-07-15-herdr-container-install-design.md)
  status becomes `superseded` with a forward link to this design; the closed
  issue and result-log are left byte-identical as history. The old
  implementation plan is marked `executed` with a forward link and its Task 2
  snippet corrected to the actually shipped `install -D` + absolute-path form.

## §2 Alternatives considered

- **A — Keep Containerfile Layer 3-8 SHA pinning (status quo).** Rejected:
  duplicates install authority, bypasses mise on a tool upstream supports via
  aqua, and leaves `herdr update` / `version_check` competing with the image
  pin (old design §6 accepted drift; this migration removes that class of
  drift entirely).
- **B — `manager = "mise"` entry in `packages.toml` + generated
  `layer_3/mise.txt`.** Rejected: the repo retired that dual-SoT path in
  favour of [`../../../dot_config/mise/config.toml`](../../../dot_config/mise/config.toml)
  as the sole hand-edited mise inventory (see
  [`../../superpowers/plans/2026-07-04-mise-config-source.md`](../../superpowers/plans/2026-07-04-mise-config-source.md)).
  `herdr` follows the same rule as `"npm:…"` and other explicit-prefix
  entries; the bare `go` / `node` / `python` keys are core tools and do not
  demonstrate the prefix pattern.
- **C — Pin an explicit aqua version (e.g. `"aqua:ogulcancelik/herdr" =
  "0.7.3"`) instead of `latest`.** Rejected per approved direction: `latest`
  at install time with `mise upgrade` for bumps matches how other global mise
  tools in this config are managed.
- **D — Leave Herdr `version_check = true` and rely on mise anyway.** Rejected:
  two update authorities produce noisy prompts and invite `herdr update`
  rewriting a shim-managed install; approved direction disables Herdr checks
  and sets `[update] channel = "stable"` as a defense-in-depth default.

## §3 Architecture / Invariants

- **I1 (single mise authority):** `herdr` is installed, versioned, and
  upgraded only through mise (`mise install`, `mise upgrade
  aqua:ogulcancelik/herdr`). No Containerfile curl bootstrap, no
  `packages.toml` entry, no `herdr update`, no image-rebuild version bumps
  for routine upgrades.
- **I2 (explicit aqua backend):** Because `disable_default_registry = true`,
  the mise config key MUST be the fully qualified aqua id
  `"aqua:ogulcancelik/herdr"`. Mise resolves the aqua registry backend,
  downloads the platform artifact, and installs under
  `$MISE_DATA_DIR/installs/aqua-ogulcancelik-herdr/…` (exact directory name
  is mise-derived; verification uses shim resolution, not a hardcoded path).
- **I3 (`latest` policy):** The config value `"latest"` means mise resolves
  the newest aqua release at `mise install` / `mise upgrade` time. This is
  intentionally non-reproducible at the config layer (the exact version
  installed depends on the time of `mise install`). Aqua/mise still verifies
  the downloaded artifact (registry checksum / signature verification where
  enabled); the implementation build is the acceptance gate that confirms
  the resolved version works. This replaces the old `ARG HERDR_VERSION` /
  `ARG HERDR_SHA256` reproducibility gate; build reproducibility for `herdr`
  is intentionally traded for alignment with other mise-managed globals
  (`node = "latest"`, etc.).
- **I4 (shim discovery):** `herdr` is on PATH via mise shims activated in
  `dot_zshenv.tmpl`, not via `~/.local/bin/herdr`. The Layer 3-8 install path
  is removed; any stale `~/.local/bin/herdr` in an old image layer disappears
  after rebuild (and must not take precedence over shims once mise owns the
  tool).
- **I5 (named-volume first-mount semantics):** Layer 3-4 installs `herdr` into
  `$MISE_DATA_DIR` inside the image. On the **first** `make up` with an empty
  `dotfiles_mise` volume, Podman copy-on-first-mount seeds the volume from the
  image tree (same pattern as spec 21 acceptance #14 for go/python/deno). If
  `dotfiles_mise` already exists from before this change, it will **not**
  gain the aqua install on `make up` alone — operators must run a one-time
  `podman volume rm dotfiles_mise` (see §6 rollout; `make clean` is broader
  and also removes the image and other volumes).
- **I6 (update-check suppression):** Chezmoi-managed Herdr config sets
  `[update] channel = "stable"`, `version_check = false`, and
  `manifest_check = false`. Herdr MUST NOT prompt for or apply self-updates;
  operators use `mise upgrade aqua:ogulcancelik/herdr` on host or inside the
  container.
- **I7 (config unchanged in role):** `~/.config/herdr/` remains
  chezmoi-managed (`dot_config/herdr/`); runtime `chezmoi apply` still renders
  it. Only the `[update]` section changes; no secret material is involved
  (extends spec 20 I4).
- **I8 (historical doc preservation):** The closed container-install issue,
  result-log, plan, and commits remain as audit trail. The old design file is
  marked `superseded` (not deleted) with a link here; this design is the
  operative spec for implementation.

## §4 Scope / staging breakdown

### In scope (implementation phase — not part of this doc-only task)

1. **`dot_config/mise/config.toml`** — add `"aqua:ogulcancelik/herdr" =
   "latest"` under `[tools]`.
2. **`dependencies/packages.toml`** — remove the `herdr` `[[tool]]` block;
   run `make gen-deps` to refresh spec 02 AUTO-GEN.
3. **`container/Containerfile`** — delete Layer 3-8 entirely; Layer 3-4
   unchanged in structure (already runs `mise install --yes` over the full
   rendered config, so it picks up `herdr` automatically once the config
   declares it).
4. **`dot_config/herdr/config.toml`** and **`dot_config/herdr/config.yml`** —
   set `[update] channel = "stable"`, `version_check = false`, and
   `manifest_check = false`.
5. **Spec sync** —
   - spec 02: note `herdr` is mise-managed via `dot_config/mise/config.toml`
     (AUTO-GEN loses the Layer 3 `custom` row).
   - spec 20: replace I-HERDR1..I-HERDR3 with mise-based invariants (this
     §3 I1–I7 distilled for the build/runtime contract).
   - spec 21: remove Layer 3-8 row and acceptance #25; add acceptance
     criterion for mise-shim `herdr --version` + one-time `dotfiles_mise`
     rollout note.
6. **Historical header edits** —
   - Set old design
     [`2026-07-15-herdr-container-install-design.md`](2026-07-15-herdr-container-install-design.md)
     to `superseded` with forward link (only header/status edit).
   - Set old plan
     [`../../plans/2026-07-15-herdr-container-install-impl.md`](../../plans/2026-07-15-herdr-container-install-impl.md)
     to `executed` with forward link and correct the Task 2 snippet to the
     actually shipped `install -D` + absolute-path form.

### Explicit non-scope

- No `Makefile` change (`dotfiles_mise` wiring already exists).
- No `.chezmoiignore` change (`MISE_DATA_DIR` is already excluded like
  cargo/rustup).
- No `dot_zshenv.tmpl` change (mise shims already activated).
- No entrypoint change.
- No edits to the closed
  [`../../issues/2026-07-15-herdr-container-install.md`](../../issues/2026-07-15-herdr-container-install.md),
  [`../../issues/2026-07-15-phase-herdr-container-install.md`](../../issues/2026-07-15-phase-herdr-container-install.md),
  or [`../../plans/2026-07-15-herdr-container-install-impl.md`](../../plans/2026-07-15-herdr-container-install-impl.md)
  bodies (historical preservation).
- No plan or result-log for this migration in this task (follows normal
  lifecycle after design approval).
- No host-only install script; host installs `herdr` via the same mise config
  when the user runs `mise install` / `mise upgrade` on the host.
- No change to `pi-coding-agent` install path (still npm via Layer 3-5 despite
  also being listed in mise config — out of scope).

## §5 Implementation detail

### §5.1 Mise config addition

In [`../../../dot_config/mise/config.toml`](../../../dot_config/mise/config.toml)
`[tools]`:

```toml
"aqua:ogulcancelik/herdr" = "latest"
```

Placement: alongside other global tools (after the existing `"npm:…"` entry is
fine). `disable_default_registry = true` (line 50) makes the `aqua:` prefix
mandatory.

### §5.2 Containerfile change

Delete the Layer 3-8 block (currently `ARG HERDR_VERSION`, `ARG HERDR_SHA256`,
and the curl/`sha256sum`/`install` `RUN` in
[`../../../container/Containerfile`](../../../container/Containerfile)). No
replacement `RUN` is added — Layer 3-4's existing `mise install --yes` installs
`herdr` when the rendered config includes the aqua entry.

### §5.3 packages.toml removal

Remove the `[[tool]]` block for `name = "herdr"` (`manager = "custom"`,
`layer = 3`). `make gen-deps` regenerates spec 02; `herdr` disappears from the
AUTO-GEN Layer 3 table. This disappearance is intentional: the hand-edited
mise config in `dot_config/mise/config.toml` becomes the sole declaration for
`herdr`, consistent with `go`, `node`, `python`, and other mise-managed tools.
The tool remains documented in spec 02 prose as mise-managed (implementation
updates the contract paragraph mirroring `dot_config/mise/config.toml` SoT).

### §5.4 Herdr config update-check suppression

Both managed variants currently contain the same TOML `[update]` block. Apply
an identical TOML block in
[`../../../dot_config/herdr/config.toml`](../../../dot_config/herdr/config.toml)
and [`../../../dot_config/herdr/config.yml`](../../../dot_config/herdr/config.yml)
(even though the latter has a `.yml` extension, its body is TOML):

```toml
[update]
channel = "stable"
version_check = false
manifest_check = false
```

Do not invent YAML syntax; the `.yml` file is a TOML-formatted legacy variant
kept under chezmoi. Optional template gating by `DOTFILES_RUNTIME` is **not**
required — mise owns updates on both host and container. With both checks
disabled the `channel` field does not trigger upgrades, but `"stable"` is the
required default to avoid surprise preview channels if a future config change
re-enables checks.

### §5.5 Upgrade procedure (steady state)

```bash
mise upgrade aqua:ogulcancelik/herdr
```

Run on host or via `podman exec <container> zsh -ic '…'` after design
approval. Rebuild the image (`make build`) only when the mise config itself
changes (e.g. adding/removing tools), not for routine `herdr` version bumps.

## §6 Rollout, rollback, and testing

### §6.1 Rollout (one-time volume migration)

For deployments that already have a `dotfiles_mise` volume from before this
change:

1. `make build` (image no longer contains Layer 3-8; Layer 3-4 bake includes
   aqua `herdr` under `$MISE_DATA_DIR`).
2. `make down`
3. `podman volume rm dotfiles_mise` — **one-time**; do **not** use `make
   clean` unless a full reset of all named volumes and the image is intended
   (see spec 21 rollout notes for cargo/gnupg/ssh).
4. `make up` — empty volume copy-on-first-mounts the image's mise installs,
   including `herdr`.
5. Verify §6.2 commands.

New deployments (no pre-existing `dotfiles_mise` volume) skip step 3.

### §6.2 Testing / acceptance commands

| Check | Command | Expected |
|---|---|---|
| Build | `make build` | Succeeds; no Layer 3-8 execution |
| Version | `podman exec <c> zsh -ic 'herdr --version'` | Exit 0; version string |
| Shim path | `podman exec <c> zsh -ic 'which herdr'` | Path under `$MISE_DATA_DIR/shims` |
| Not old path | `podman exec <c> zsh -ic 'test ! -x $HOME/.local/bin/herdr'` | True after rebuild (or old binary absent) |
| Mise list | `podman exec <c> zsh -ic 'mise ls aqua:ogulcancelik/herdr'` | Shows installed version |
| Persistence | `make down && make up` then `herdr --version` | Still works |
| Config toml | `podman exec <c> zsh -c 'grep -E "channel\|version_check\|manifest_check" ~/.config/herdr/config.toml'` | `channel = "stable"`; both checks `false` |
| Config yml | `podman exec <c> zsh -c 'grep -E "channel\|version_check\|manifest_check" ~/.config/herdr/config.yml'` | `channel = "stable"`; both checks `false` |
| Regression | `podman exec <c> zsh -ic 'go version; node --version; pi --version'` | Unaffected mise/npm tools still work |
| gen-deps | `make gen-deps` twice | Second run no-op; no `herdr` in AUTO-GEN |

### §6.3 Rollback

1. `git revert` the implementation commits (or restore prior files from
   `develop` history).
2. Confirm `packages.toml` `herdr` `custom` entry and Containerfile Layer 3-8
   are restored.
3. Remove `"aqua:ogulcancelik/herdr"` from mise config; restore Herdr
   `[update]` flags if desired.
4. `make build && make down && podman volume rm dotfiles_mise && make up` to
   re-sync volume with the reverted image (parallel to forward migration).
5. Mark this design `superseded` or abandon the issue if rollback is
   permanent.

## §7 Historical document treatment

| Document | Treatment |
|---|---|
| [`../../issues/2026-07-15-herdr-container-install.md`](../../issues/2026-07-15-herdr-container-install.md) | **Preserve** (closed, with result-log link) |
| [`../../issues/2026-07-15-phase-herdr-container-install.md`](../../issues/2026-07-15-phase-herdr-container-install.md) | **Preserve** (result-log evidence) |
| [`../../plans/2026-07-15-herdr-container-install-impl.md`](../../plans/2026-07-15-herdr-container-install-impl.md) | **Executed, then linked** — status → `executed`; add forward link to this design; correct the Task 2 snippet to the actually shipped `install -D` + absolute-path form; body otherwise preserved as historical checklist |
| [`2026-07-15-herdr-container-install-design.md`](2026-07-15-herdr-container-install-design.md) | **Supersede** during implementation: status → `superseded`, forward link to this file; body kept for audit |
| This design + issue | Operative spec for the migration |

The old design §2 option D ("mise-managed install — Rejected") is overturned
by explicit product approval; this design documents the replacement rationale
(§2) without rewriting the historical rejection text in the old file.

The old implementation plan (`docs/plans/2026-07-15-herdr-container-install-impl.md`)
was executed as written for the shipped container-install work. During Task 2,
the initial brief's `source /tmp/build-home/.zshenv` + bare `herdr --version`
snippet was corrected in the actual commit to the approved design §5.1 form
(`install -D -m 0755` + absolute-path `"$HOME/.local/bin/herdr" --version`)
because `.zshenv`'s `(N-/)` glob qualifier dropped `~/.local/bin` from
`PATH` before the directory existed. The plan file will be updated during
implementation to: (a) status `executed`, (b) a forward link to this design,
(c) the Task 2 snippet corrected to the shipped `install -D` + absolute-path
form. Its body otherwise remains a historical checklist.

## §8 Open questions

- **Q1 (aqua attestations on first install):** The open issue
  [`../../issues/2026-07-09-mise-pnpm-go-build-failures.md`](../../issues/2026-07-09-mise-pnpm-go-build-failures.md)
  documents past aqua/core failures for `pnpm` and `go`. That issue predates
  this work and is stale evidence: the 2026-07-15 Herdr container-install
  result-log ([`../../issues/2026-07-15-phase-herdr-container-install.md`](../../issues/2026-07-15-phase-herdr-container-install.md))
  records a successful full five-stage build and a working Layer 3-4
  mise-dependent path (e.g. `pi --version` PASS, which depends on `mise exec
  node@latest` and therefore proves the aqua `pnpm` install succeeded). The
  `make build` acceptance command in §6.2 remains mandatory; if
  `aqua:ogulcancelik/herdr` hits an attestation failure, that recurrence is
  an implementation blocker and must be diagnosed (with a result-log note)
  before the issue can close — it is not a design blocker.
- **Q2 (host sync):** Host users must run `mise install` / `mise upgrade
  aqua:ogulcancelik/herdr` after chezmoi applies the updated config; no
  separate host install script is in scope. Document in spec 02 / quickstart
  only if reviewers request it.
