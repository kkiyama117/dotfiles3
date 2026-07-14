# pi Agent + Provider Config Managed — Design

**Status:** Approved (review waived by maintainer decision 2026-07-14; see Review trail below)
**Date opened:** 2026-07-14
**Issue:** [`docs/issues/2026-07-14-pi-provider-config-managed.md`](../../issues/2026-07-14-pi-provider-config-managed.md)
**Author:** kiyama
**Supersedes / extends:** [`2026-07-08-pi-agent-container-git-managed-config-design.md`](2026-07-08-pi-agent-container-git-managed-config-design.md) (extends §5.1, §5.3, §7 Q3)
**Review required:** letter A + B + D (touches secret handling, auth flow, and cross-spec consistency; see [`../09-review.md`](../09-review.md) §2.2)
**Review trail:** Review waived by maintainer decision 2026-07-14 (letter A/B/D pass skipped). Treated as Approved for execution. Operators should still spot-check the secret-handling steps (Phase 1 Bitwarden item, Phase 3 `models.json` apiKey templating) against spec 13 I-S3 before merging. Implementation plan: [`docs/plans/2026-07-14-pi-provider-config-managed-impl.md`](../../plans/2026-07-14-pi-provider-config-managed-impl.md). Result log: (pending Phase 6).

## §1 Context & success criteria

### Context

The 2026-07-08 bootstrap design landed `/data/pi-config` consumed by
`dotfiles3` via `.chezmoiexternal.toml.tmpl` into
`~/.local/share/pi-config`, with `run_after_configure-pi-agent.sh.tmpl`
symlinking five resources (`settings.json`, `prompts`, `skills`,
`extensions`, `themes`) into `~/.pi/agent`. Today the `/data/pi-config`
checkout contains only `agent/prompts/commit.md` and empty
`skills/extensions/themes` — no `settings.json`, no provider files — so
none of the live `~/.pi/agent` provider configuration is actually
managed.

The live `~/.pi/agent` directory carries four additional stable files
not yet in `/data/pi-config`:

- `settings.json` — agent + subagent model selection (no secrets).
- `models.json` — DeepSeek provider declaration. **Currently holds a
  plaintext `apiKey: "sk-..."`**, forbidden in `/data/pi-config` by
  spec 11 §"API provider env vars" and spec 13 I-S3.
- `ollama-cloud.json` — `{"webTools": false}`.
- `cursor-sdk.json` — `{"fastDefaults": {}}`.
- `cursor-sdk-context-windows.json` — hand-curated context-window
  overrides (SOP-governed by `~/.pi/agent-sops/cursor-sdk-catalog-refresh.sop.md`).

The container also carries a **per-provider override directory** outside
`agent/`:

- `~/.pi/providers/<provider-id>/config.json` — pi's per-provider user
  override mechanism. The container has `~/.pi/providers/kimi-coding/config.json`
  overriding the built-in `kimi-coding` provider (model params
  `contextWindow`/`maxTokens`/`reasoningMap`, per-tool toggles
  `moonshot_search`/`moonshot_fetch`/`kimi_datasource`,
  `uploads.thresholdBytes`, `protocol`). `kimi-coding` is a built-in
  pi-ai provider (`auth: envApiKeyAuth("Kimi API key", ["KIMI_API_KEY"])`),
  so the override file is **secret-free**. The pi docs do not document
  this directory explicitly (only `PI_CODING_AGENT_DIR` appears in
  `docs/usage.md`), but it is a real, stable feature observed in the
  running container. The host has no `~/.pi/providers/` today because the
  host's `~/.pi` is the legacy `PI_harness` git repo
  (`git@github.com:kkiyama117/PI_harness.git`); per the maintainer's
  decision, `/data/pi-config` is the canonical managed source going
  forward and `PI_harness` is the old/current config being grown out of
  and replaced. See §3 I8 and §5.7 for the retirement migration.

And one generated cache that **must not** be managed:

- `cursor-sdk-model-list.json` — 145 KB, near-daily full rewrites per
  the catalog-refresh SOP.

The DeepSeek key currently lives only as the inline literal in
`models.json`. `DEEPSEEK_API_KEY` is absent from
`.chezmoidata/api_secrets.yaml`, from spec 11's provider env table, and
from `~/.config/zsh/rc/secrets.zsh`. The Bitwarden → `secrets.zsh`
pipeline approved in the 2026-07-11 api-secrets design does not yet
cover DeepSeek.

Upstream pi (`docs/models.md` §"Value Resolution") supports three forms
for the `apiKey` field, all resolved at request time for `models.json`:

- **Shell command:** `"!security find-generic-password -ws 'deepseek'"`
- **Env interpolation:** `"$DEEPSEEK_API_KEY"` or `"${DEEPSEEK_API_KEY}"`
  (interpolation also works inside larger literals; missing env →
  unresolved).
- **Literal:** `"sk-..."` (current state).

`apiKey` is optional: auth can also come from `/login`/`auth.json` or
`--api-key`. So a managed `models.json` can carry
`"apiKey": "$DEEPSEEK_API_KEY"` and resolve the real key from the
existing `secrets.zsh` env export, with no secret ever entering git.

**Legacy `PI_harness` repo.** The host's `~/.pi` is itself a git repo
today (`git@github.com:kkiyama117/PI_harness.git`) and already tracks
the provider files — including `agent/models.json` with the **plaintext
DeepSeek key already committed to `PI_harness` history**. Per the
maintainer's decision, `PI_harness` is the old/current config and
`/data/pi-config` is the canonical managed source going forward; the
goal is to grow `/data/pi-config` and replace the `PI_harness`-tracked
config with it. This has two consequences the design must handle:
(a) `PI_harness` must stop tracking the migrated paths so the chezmoi
symlinks do not dirty it, and (b) the leaked DeepSeek key in
`PI_harness` history must be **rotated** (and, if `PI_harness` is or
was ever public, history-rewritten or the repo archived) regardless of
which repo is canonical. See §3 I8, §5.7.

### Success criteria

- **S1:** `/data/pi-config/agent/` contains `settings.json`, `models.json`,
  `ollama-cloud.json`, `cursor-sdk.json`, `cursor-sdk-context-windows.json`,
  with no `sk-...`/`apiKey` literal anywhere in the repo's git history.
- **S2:** `models.json` in `/data/pi-config` uses
  `"apiKey": "$DEEPSEEK_API_KEY"` for the DeepSeek provider (env
  interpolation, resolved by pi at request time). No other secret-bearing
  field is present in any managed file.
- **S3:** `DEEPSEEK_API_KEY` is added to `.chezmoidata/api_secrets.yaml`
  with a Bitwarden item ID / stable item name and a `field` selector,
  matching the shape of the existing `OPENROUTER_API_KEY` /
  `MOONSHOT_API_KEY` / `OLLAMA_API_KEY` / `CURSOR_API_KEY` rows. A
  corresponding Bitwarden Login item with the named custom field is
  created in the user's vault before the plan executes.
- **S4:** Spec 11 §"API provider env vars" gains a `DEEPSEEK_API_KEY` row
  and §"Bitwarden items" gains the corresponding item row. Spec 13 needs
  no new invariant (I-S3 / I-S5 already cover this), but this design
  references them.
- **S5:** `run_after_configure-pi-agent.sh.tmpl` `link_resource`s each
  newly managed file. The `{{ if not .build_mode }}` guard is unchanged;
  build mode continues to skip the whole script.
- **S6:** `cursor-sdk-model-list.json` is explicitly documented as **not
  managed** (generated cache). `/data/pi-config/.gitignore` is extended to
  defend against it and any other generated cache entering the repo
  accidentally.
- **S7:** Verify-before-commit per `pi-model-provider-swap.sop.md` step 4:
  with `DEEPSEEK_API_KEY` exported (via the rendered `secrets.zsh`) and
  `~/.pi/agent/models.json` pointing at the managed file, a real
  `deepseek/deepseek-v4-pro` request succeeds before the design moves to
  Approved. Evidence is captured in the result-log.
- **S8:** No sensitive pi runtime path (`auth.json`, `trust.json`,
  `sessions/`, `npm/`, `cache/`, `run-history.jsonl`,
  `cursor-sdk-model-list.json`) becomes managed or enters
  `/data/pi-config` history.
- **S9:** `~/.pi/providers/` (per-provider user overrides, e.g.
  `providers/kimi-coding/config.json`) is managed via a new top-level
  `providers/` dir in `/data/pi-config` and a new symlink target
  `~/.pi/providers` → `~/.local/share/pi-config/providers`. The override
  files are secret-free; the whole `providers/` tree is managed
  recursively.
- **S10:** The legacy `PI_harness` repo (`~/.pi/.git` on host) stops
  tracking the migrated paths (`agent/{settings,models,ollama-cloud,cursor-sdk,cursor-sdk-context-windows,cursor-sdk-model-list}.json`
  and the migrated dirs); those paths are gitignored in `PI_harness` so
  the chezmoi symlinks do not dirty it. `PI_harness` is documented as
  legacy/superseded by `/data/pi-config`.
- **S11:** The DeepSeek API key leaked into `PI_harness` history is
  **rotated** at the provider (DeepSeek console) and the new key is
  stored only in Bitwarden → `secrets.zsh` → `$DEEPSEEK_API_KEY`. If
  `PI_harness` is or was ever public, its history is rewritten or the
  repo is archived after rotation. This is independent of S1
  (`/data/pi-config` never holds the literal) — rotation closes the
  pre-existing leak.

## §2 Alternatives considered

- **A1 — Env interpolation `"apiKey": "$DEEPSEEK_API_KEY"` (chosen).**
  Reuses the existing Bitwarden → `secrets.zsh` pipeline: a new
  `DEEPSEEK_API_KEY` row in `.chezmoidata/api_secrets.yaml` exports the
  key at shell startup; `models.json` reads it at request time via pi's
  native env interpolation. Zero secret in git, zero new auth mechanism.
  Matches the OpenRouter/Kimi/Ollama/Cursor pattern already in the stack.
- **A2 — Shell command `"apiKey": "!bw get password <deepseek-item>"`
  (rejected).** Shells out to `bw` on every request. Pi docs
  (`docs/models.md` §"Value Resolution") warn that pi intentionally does
  not apply TTL, stale reuse, or recovery logic for arbitrary commands;
  a slow or rate-limited `bw` call would degrade every DeepSeek request.
  Also duplicates auth: `BW_SESSION` is already managed by the
  entrypoint / `chezmoi_apply` and would have to be re-derived per
  request. Reject in favor of A1.
- **A3 — Omit `apiKey`, auth via `/login deepseek` → `auth.json`
  (rejected).** `auth.json` is runtime state (`/data/pi-config/.gitignore`
  excludes it), so this does not make the provider "managed"; it just
  moves the secret to another unmanaged file and breaks the
  "config-as-code" goal. Also requires an interactive `/login` per
  machine/checkout, which the container entrypoint cannot do
  non-interactively for an arbitrary provider.
- **A4 — Manage only non-secret provider files, leave `models.json`
  runtime-only (rejected).** The user explicitly asked to template
  `models.json` rather than exclude it. A4 also leaves the most
  churn-prone provider declaration (model list, cost table, thinking
  level map) unmanaged, defeating the purpose of this issue.
- **A5 — Manage `cursor-sdk-model-list.json` too (rejected).** It is a
  generated 145 KB cache regenerated near-daily per
  `cursor-sdk-catalog-refresh.sop.md`. Committing it would replay the
  thousands-of-lines churn already documented in that SOP and pollute
  `/data/pi-config` history. Keep it runtime-only and gitignore it.
- **A6 — Symlink all managed files vs copy all vs split (see §5.3).**
  Symlink-all matches the existing `link_resource` pattern and is
  chosen for `settings.json`, `models.json`, `ollama-cloud.json`,
  `cursor-sdk.json`, `cursor-sdk-context-windows.json`. The dirty-repo
  risk from interactive `/settings` or `/model` edits (Q3 from the
  2026-07-08 design) is handled by §5.3 rule R1 + the SOP's
  verify-before-commit discipline, not by copying.

## §3 Architecture / invariants

- **I1 (extends 2026-07-08 I1):** `/data/pi-config` remains an independent
  git repo. `dotfiles3` only consumes it via `.chezmoiexternal.toml.tmpl`
  and exposes resources via `run_after_configure-pi-agent.sh.tmpl`.
- **I2 (extends 2026-07-08 I5):** No managed secret. `models.json`'s
  `apiKey` field is `"apiKey": "$DEEPSEEK_API_KEY"` — env interpolation,
  not a literal. The real key lives in Bitwarden, is exported by the
  existing `secrets.zsh` pipeline (extended with one new row), and is
  resolved by pi at request time. This refines spec 13 I-S3 (no secret
  in repo/`.env`/image) and reuses I-S5 (chezmoi `bitwarden*` is the
  only secret-CLI path) — no new invariant is needed.
- **I3 (new):** The set of managed pi paths is closed and enumerated. Under
  `~/.pi/agent/`: `settings.json`, `models.json`, `ollama-cloud.json`,
  `cursor-sdk.json`, `cursor-sdk-context-windows.json`, plus the
  directory resources `prompts/`, `skills/`, `extensions/`, `themes/`.
  Outside `~/.pi/agent/`: `~/.pi/providers/` (recursive — per-provider
  override dirs `<id>/config.json`). Everything else under `~/.pi/agent`
  (notably `auth.json`, `trust.json`, `sessions/`, `npm/`, `cache/`,
  `run-history.jsonl`, `cursor-sdk-model-list.json`, and the
  model-list cache sibling of `cursor-sdk-context-windows.json`) is
  runtime-only.
- **I4 (new):** `cursor-sdk-model-list.json` is generated state. It is
  excluded from management and from `/data/pi-config` history by an
  explicit `.gitignore` entry, not merely by convention.
- **I5 (new):** Provider env vars are exported **synchronously** before
  the first pi invocation (existing sheldon synchronous plugin for
  `secrets.zsh`, per the 2026-07-11 api-secrets design S5). `models.json`
  env interpolation therefore never sees an "unresolved" `$DEEPSEEK_API_KEY`
  at request time on a correctly-apply'd host. The verify step (S7)
  proves this end-to-end.
- **I6 (extends 2026-07-08 I6):** Build mode (`BUILD_MODE=true`) still
  emits no pi-config external and still skips
  `run_after_configure-pi-agent.sh.tmpl` entirely. No new build-time
  behavior is introduced.
- **I7 (new):** Verify-before-commit is mandatory. Per
  `pi-model-provider-swap.sop.md` step 4 and `cursor-sdk-catalog-refresh.sop.md`
  step 3, the implementation must prove `deepseek/deepseek-v4-pro`
  resolves end-to-end (env export → managed `models.json` → pi request)
  **before** the design moves DRAFT → Approved and **before** any
  `/data/pi-config` commit that touches `models.json`. This is the exact
  failure mode the SOP was written to prevent (commit-then-revert-later
  on `settings.json`/`models.json`).
- **I8 (new — legacy retirement):** `/data/pi-config` is the canonical
  managed source for pi config. `PI_harness` (`~/.pi/.git` on host,
  `git@github.com:kkiyama117/PI_harness.git`) is the legacy/current
  config being replaced. The migrated paths are untracked from
  `PI_harness` and gitignored there so the chezmoi symlinks (host-side)
  do not dirty it. `PI_harness` is not deleted in this design — it is
  left as a legacy archive; whether to remove `~/.pi/.git` entirely is
  Q8. The plaintext DeepSeek key already in `PI_harness` history is
  rotated at the provider; `/data/pi-config` never receives the literal.
- **I9 (new — secret scope):** Spec 11 / spec 13's forbidden-secret
  location list is extended to explicitly name `PI_harness.git` (and
  any host `~/.pi` git repo) alongside `/data/pi-config`, `.env`,
  `.chezmoidata`, and this repository. The specs previously had a blind
  spot for `PI_harness` because it predated the 2026-07-08 design.

## §4 Scope / staging breakdown

0. **`PI_harness` retirement (host)** — rotate the leaked DeepSeek key at
   the provider; untrack the migrated paths from `PI_harness`
   (`git -C ~/.pi rm --cached ...`); extend `~/.pi/.gitignore` so the
   chezmoi symlinks do not dirty `PI_harness`; decide Q8 (keep
   `~/.pi/.git` as archive vs remove). This phase is host-only and does
   not touch the container.
1. **Secret pipeline extension** — create the DeepSeek Bitwarden Login
   item with the named custom field; add the `DEEPSEEK_API_KEY` row to
   `.chezmoidata/api_secrets.yaml`; verify
   `chezmoi apply` renders `secrets.zsh` exporting `DEEPSEEK_API_KEY`
   on host and container.
2. **Spec 11 update** — add `DEEPSEEK_API_KEY` to the provider env table
   and the Bitwarden items table.
3. **`/data/pi-config` population** — copy the five chosen files from
   `~/.pi/agent` into `/data/pi-config/agent/`; in `models.json`, replace
   the `sk-...` literal with `"$DEEPSEEK_API_KEY"`; copy the container's
   `~/.pi/providers/kimi-coding/config.json` (and any other
   `providers/<id>/config.json` that should be managed) into
   `/data/pi-config/providers/`; extend `/data/pi-config/.gitignore`
   with `cursor-sdk-model-list.json` and any other generated cache name.
4. **`dotfiles3` symlink extension** — add `link_resource` calls for
   `models.json`, `ollama-cloud.json`, `cursor-sdk.json`,
   `cursor-sdk-context-windows.json` to
   `run_after_configure-pi-agent.sh.tmpl`, plus a new link for
   `~/.pi/providers` → `~/.local/share/pi-config/providers` (outside the
   `agent/` pair — see §5.4).
5. **End-to-end verify** — `chezmoi apply --refresh-externals=always`;
   confirm `~/.pi/agent/models.json` is a symlink to the managed file;
   confirm `~/.pi/providers` is a symlink to the managed dir and
   `~/.pi/providers/kimi-coding/config.json` resolves through it;
   confirm `DEEPSEEK_API_KEY` is exported in the interactive shell;
   run `pi` and resolve `deepseek/deepseek-v4-pro` with a real request.
6. **Result-log** — record the verify evidence in
   `docs/issues/2026-07-14-phase-pi-provider-config-managed.md` per spec
   00 §6.6.

## §5 Implementation detail

### §5.1 `/data/pi-config` layout (extends 2026-07-08 §5.1)

```text
/data/pi-config/
├── README.md
├── .gitignore
├── agent/
│   ├── settings.json
│   ├── models.json
│   ├── ollama-cloud.json
│   ├── cursor-sdk.json
│   ├── cursor-sdk-context-windows.json
│   ├── prompts/
│   │   └── commit.md
│   ├── skills/
│   ├── extensions/
│   └── themes/
└── providers/
    └── kimi-coding/
        └── config.json
```

`providers/` is a top-level dir in `/data/pi-config` (sibling of
`agent/`), mirroring pi's own `~/.pi/providers/` layout. Each
`providers/<id>/config.json` is a per-provider user override; the whole
tree is managed recursively.

`.gitignore` additions beyond the 2026-07-08 set:

```gitignore
# Generated cache — never managed (cursor-sdk-catalog-refresh.sop.md)
cursor-sdk-model-list.json
cursor-sdk-model-list.*.json
```

### §5.2 `models.json` secret handling

The DeepSeek provider block becomes:

```json
{
  "providers": {
    "deepseek": {
      "baseUrl": "https://api.deepseek.com",
      "api": "openai-completions",
      "apiKey": "$DEEPSEEK_API_KEY",
      "models": [ /* unchanged model entries */ ]
    }
  }
}
```

Per `docs/models.md` §"Value Resolution": `"$DEEPSEEK_API_KEY"` is env
interpolation, resolved by pi at request time; missing env → unresolved
(pi `/model` availability checks use configured auth presence and do
not execute shell commands, so a missing env surfaces as an
unavailable model, not a crash). This is the same shape as the
`google-generative-ai` example in `docs/models.md` line ~104.

No other field in any managed file carries secret material. The four
other files (`settings.json`, `ollama-cloud.json`, `cursor-sdk.json`,
`cursor-sdk-context-windows.json`) contain no `apiKey`/token fields.

### §5.3 Symlink vs copy (resolves 2026-07-08 Q3, extended)

**Decision: symlink all five new files**, matching the existing
`link_resource` pattern and the 2026-07-08 design's §5.3.

**R1 (dirty-repo mitigation):** the dirty-repo risk from interactive
`/settings` or `/model` edits writing through the symlink into
`/data/pi-config` is handled by:

- operator discipline: edit `/data/pi-config` directly and re-apply,
  not through pi's interactive `/settings` against the live symlink;
- the `pi-model-provider-swap.sop.md` verify-before-commit discipline
  (S7 / I7), which already gates every `settings.json`/`models.json`
  change;
- the `/data/pi-config` post-commit hook path documented in
  `programs/chezmoi_pi_commit.sh` (host runtime only), which catches
  accidental dirty state on `chezmoi add`/`edit`.

**R2 (why not copy):** copying would diverge the deployed `~/.pi/agent`
file from the managed source after any in-place edit, with no signal to
the operator. The symlink gives a single source of truth and surfaces
drift as a dirty `/data/pi-config` working tree, which the auto-commit
hook already reports.

**R3 (per-file carve-out):** if a future file turns out to be
mutated by pi at runtime (the way `cursor-sdk-model-list.json` is), it
is moved to the not-managed list and gitignored, not copied. That is
the I3/I4 rule, not a symlink exception.

### §5.4 `run_after_configure-pi-agent.sh.tmpl` extension

Add four `link_resource` calls after the existing `settings.json` line:

```bash
link_resource "settings.json"
link_resource "models.json"
link_resource "ollama-cloud.json"
link_resource "cursor-sdk.json"
link_resource "cursor-sdk-context-windows.json"
link_resource "prompts"
link_resource "skills"
link_resource "extensions"
link_resource "themes"
```

`link_resource` links `${pi_config_dir}/${name}` → `${pi_agent_dir}/${name}`
with `pi_config_dir=~/.local/share/pi-config/agent` and
`pi_agent_dir=~/.pi/agent`. `providers/` lives under `~/.pi/`, not
`~/.pi/agent/`, so it needs a separate link. Add a second helper
`link_pi_root_resource` that links `~/.local/share/pi-config/<name>` →
`~/.pi/<name>`, and one call:

```bash
link_pi_root_resource "providers"
```

`link_pi_root_resource` reuses the same `backup_existing` and
idempotent-symlink logic as `link_resource`, just with
`pi_config_root="${HOME}/.local/share/pi-config"` and
`pi_root="${HOME}/.pi"` in place of the `agent` pair. The whole
`providers/` tree is symlinked as one dir, matching the
`prompts/skills/extensions/themes` dir-symlink pattern; pi reads
`~/.pi/providers/<id>/config.json` by path, so a symlinked dir is
transparent to it.

The `link_resource` / `link_pi_root_resource` functions already no-op
when the source is absent, so a `/data/pi-config` ref that predates a
given file (or predates `providers/` entirely) does not break apply on
older checkouts — including the container, where today
`~/.local/share/pi-config/providers` does not exist yet. The
`{{ if not .build_mode }}` guard is unchanged.

### §5.5 Secret pipeline (extends 2026-07-11 api-secrets design)

Add to `.chezmoidata/api_secrets.yaml`:

```yaml
  - env: DEEPSEEK_API_KEY
    item: "<bitwarden-item-id-or-stable-name>"   # filled in plan Phase 1
    source: custom_field
    field: main
    runtime: both
```

The Bitwarden Login item is created by the operator (one-time) before
plan Phase 1 verification:

```
bw create item <json>   # Login item named e.g. "deepseek.com"
                        # custom field: main = <real DeepSeek key>
```

Spec 11 §"API provider env vars" gains:

| Variable | Required | Source | Used by |
|---|---|---|---|
| `DEEPSEEK_API_KEY` | no | `secrets.zsh` | pi, DeepSeek API |

Spec 11 §"Bitwarden items" gains the corresponding row, matching the
existing `OLLAMA_API_KEY` / `CURSOR_API_KEY` shape.

No new spec 13 invariant is introduced; I-S3 (no secret in
repo/`.env`/image) and I-S5 (chezmoi `bitwarden*` only) already cover
this.

### §5.6 Files deliberately not managed (I3 / I4)

| Path | Reason |
|---|---|
| `auth.json` | runtime OAuth/auth state (`/data/pi-config/.gitignore`) |
| `trust.json` | runtime trust decisions (`/data/pi-config/.gitignore`) |
| `sessions/` | runtime session state (`/data/pi-config/.gitignore`) |
| `npm/` | downloaded package clones (`/data/pi-config/.gitignore`) |
| `cache/` | runtime cache (`/data/pi-config/.gitignore`) |
| `run-history.jsonl` | runtime history (`/data/pi-config/.gitignore`) |
| `cursor-sdk-model-list.json` | generated cache, near-daily full rewrites (`cursor-sdk-catalog-refresh.sop.md`); new `.gitignore` entry (§5.1) |
| `cursor-sdk-context-windows.json` | **managed** — hand-curated, SOP-governed, changes rarely and by hand |
| `intercom/` | runtime inter-process state |

### §5.7 `PI_harness` retirement (host-only)

The host's `~/.pi` is currently the `PI_harness` git repo and tracks the
provider files (including `models.json` with the plaintext DeepSeek key
in history). Per the maintainer decision, `/data/pi-config` is canonical
and `PI_harness` is legacy. The retirement is host-only and runs once:

1. **Rotate the leaked key (S11).** Generate a new DeepSeek API key in
   the DeepSeek console; revoke the old `sk-6a27768a...`. Store the new
   key only in Bitwarden (the Login item from §5.5). Do this **before**
   the managed `models.json` goes live so the old literal is dead by the
   time `$DEEPSEEK_API_KEY` resolves it.
2. **Untrack migrated paths from `PI_harness`.** On host:
   ```bash
   git -C ~/.pi rm --cached \
     agent/settings.json \
     agent/models.json \
     agent/ollama-cloud.json \
     agent/cursor-sdk.json \
     agent/cursor-sdk-context-windows.json \
     agent/cursor-sdk-model-list.json
   ```
   (and any migrated dirs the operator decides to move). Commit the
   removal in `PI_harness` with a message pointing at this design + the
   new canonical location.
3. **Gitignore migrated paths in `PI_harness`.** Extend `~/.pi/.gitignore`
   so the chezmoi-created symlinks (host-side apply) do not reappear as
   untracked entries:
   ```gitignore
   # Migrated to /data/pi-config (canonical). These are now chezmoi
   # symlinks on apply; do not track them here.
   agent/settings.json
   agent/models.json
   agent/ollama-cloud.json
   agent/cursor-sdk.json
   agent/cursor-sdk-context-windows.json
   agent/cursor-sdk-model-list.json
   providers/
   ```
   The existing `agent/auth.json`, `agent/sessions/**`, `agent/trust.json`,
   `agent/run-history.jsonl` entries stay.
4. **Archive / rewrite decision (Q8 / S11).** If `PI_harness` is or was
   ever public, the old `sk-6a27768a...` is in pushed history → after
   rotation, either `git filter-repo` the secret out of `PI_harness`
   history + force-push, or archive `PI_harness` and mark it superseded.
   If `PI_harness` was always private, rotation alone closes the leak
   and the repo can stay as a legacy archive. The plan records which
   branch was taken and why.

`PI_harness` is **not** deleted in this design — it remains as a legacy
archive of the old config. Whether to eventually remove `~/.pi/.git`
entirely (so `~/.pi` becomes a plain runtime dir like the container) is
Q8, intentionally left for a later cleanup pass.

## §6 Verification plan

- `chezmoi execute-template --init` renders host/runtime config without
  template errors; `BUILD_MODE=true chezmoi execute-template --init`
  emits no pi-config external (unchanged from 2026-07-08 §6).
- `chezmoi apply --refresh-externals=always` on host:
  - `~/.pi/agent/models.json` is a symlink to
    `~/.local/share/pi-config/agent/models.json`.
  - `~/.pi/agent/settings.json`, `ollama-cloud.json`, `cursor-sdk.json`,
    `cursor-sdk-context-windows.json` are likewise symlinked.
  - `~/.pi/agent/cursor-sdk-model-list.json` is **not** a symlink (still
    runtime-owned).
  - `~/.pi/providers` is a symlink to
    `~/.local/share/pi-config/providers`, and
    `~/.pi/providers/kimi-coding/config.json` resolves through it.
  - `~/.config/zsh/rc/secrets.zsh` exports `DEEPSEEK_API_KEY` (mode 0600).
- End-to-end (S7 / I7):
  - In a fresh interactive shell: `echo "$DEEPSEEK_API_KEY"` is non-empty.
  - `pi --model deepseek/deepseek-v4-pro --print 'ping'` (or equivalent
    `/model` resolution + a one-turn request) exits 0 and returns a
    real response.
  - `git -C /data/pi-config log -p -- agent/models.json` shows no
    `sk-...` literal at any commit.
  - `git -C /data/pi-config grep -E 'sk-[A-Za-z0-9]{16,}' -- agent/`
    returns nothing.
- Build safety (unchanged): `make build` does not fetch or bake
  `/data/pi-config`, `~/.local/share/pi-config`, or `~/.pi/agent`
  runtime state.
- Container: `podman exec dotfiles-manjaro zsh -ic 'pi --version'`
  exits 0; `podman exec dotfiles-manjaro zsh -ic 'readlink ~/.pi/agent/models.json'`
  points at the managed target after runtime apply.
- `PI_harness` retirement (host, S10/S11):
  - `git -C ~/.pi ls-files agent/models.json agent/settings.json
    agent/ollama-cloud.json agent/cursor-sdk.json
    agent/cursor-sdk-context-windows.json` returns nothing (untracked).
  - `git -C ~/.pi check-ignore agent/models.json providers/` exits 0
    (ignored, so symlinks do not dirty `PI_harness`).
  - `git -C ~/.pi grep -E 'sk-6a27768a'` either returns nothing (after
    history rewrite) or the plan records that `PI_harness` was always
    private and the key was rotated at the provider (S11).
  - A real `pi` request using `$DEEPSEEK_API_KEY` succeeds with the
    **new** rotated key, proving the old literal is dead.

## §7 Open questions

- **Q1:** What is the Bitwarden item ID / stable item name for the
  DeepSeek Login item? The plan Phase 1 fills the `item:` field in
  `.chezmoidata/api_secrets.yaml` after the operator creates the vault
  entry. (Not blocking for design approval; blocking for plan
  execution.)
- **Q2 (resolves 2026-07-08 Q3):** Symlink vs copy. Resolved here in
  §5.3 R1–R3: **symlink all five new files**, with dirty-repo
  mitigation via operator discipline + the
  `pi-model-provider-swap.sop.md` verify-before-commit gate + the
  existing `chezmoi_pi_commit.sh` post-hook. Per-file carve-out only
  for files pi mutates at runtime (none of the five currently qualify;
  `cursor-sdk-model-list.json` is the canonical runtime-mutated file
  and is excluded by I3/I4).
- **Q3:** Should `cursor-sdk-context-windows.json` be managed given it
  is SOP-governed? **Yes** — it is hand-curated, changes rarely, and the
  SOP (`cursor-sdk-catalog-refresh.sop.md`) already treats it as the
  curated override snapshot (as opposed to the generated model-list).
  Managing it gives reviewable history for the curated values. The
  generated `cursor-sdk-model-list.json` stays runtime-only (I4).
- **Q4:** Does any other provider in `models.json` need the same
  env-interpolation treatment in this pass? Current `models.json`
  declares only `deepseek` (other providers — `ollama-cloud`,
  `cursor`, `anthropic`, `openrouter`, `moonshot` — are built-in or
  extension-registered and read their keys from env exported by
  `secrets.zsh` already). So no further `models.json` change is
  required for them in this design. If a future provider is added with
  an inline key, the same `"$ENV_VAR"` rule applies.
- **Q5:** Should `/data/pi-config/.gitignore` also defensively list
  `cursor-sdk-context-windows.json`-adjacent generated snapshots
  (e.g. `cursor-sdk-*.json` excluding the curated name)? The §5.1
  gitignore uses the narrower `cursor-sdk-model-list.json` +
  `cursor-sdk-model-list.*.json` to avoid accidentally ignoring the
  curated `cursor-sdk-context-windows.json`. Reviewer B (security)
  should confirm this is not too narrow.
- **Q6 (resolved by maintainer decision 2026-07-14):** `/data/pi-config`
  is canonical; `PI_harness` (`~/.pi/.git` on host) is legacy and is
  retired per §5.7. The host-side `~/.pi/providers` symlink is accepted;
  `PI_harness` gitignores `providers/` and the migrated `agent/*` files
  so the symlinks do not dirty it. No host/container split in management
  model — both follow Model A (the 2026-07-08 design).
- **Q7:** Should the whole `providers/` tree be one dir symlink (chosen,
  §5.4), or should each `providers/<id>/` be symlinked individually so a
  future unmanaged provider can coexist? Dir-symlink is simpler and
  matches the `prompts/skills/extensions/themes` pattern; per-provider
  symlinks allow mixing managed and unmanaged providers under
  `~/.pi/providers/`. Reviewer A (factual) should confirm pi reads
  `~/.pi/providers/<id>/config.json` correctly when `providers/` itself
  is a symlink (expected yes, same as the existing dir symlinks).
- **Q8 (new):** Should `~/.pi/.git` (the `PI_harness` repo) be removed
  entirely after retirement so the host's `~/.pi` becomes a plain
  runtime dir like the container, or should `PI_harness` remain as a
  legacy archive? This design leaves `~/.pi/.git` in place (§5.7 step 4)
  and only untracks + gitignores the migrated paths. Removing the repo
  is a separate cleanup pass, intentionally out of scope here.
