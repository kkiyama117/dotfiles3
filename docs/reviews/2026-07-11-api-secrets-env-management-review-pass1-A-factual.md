# api-secrets-env-management — Review pass-1 (Letter A: factual / correctness)

**Date:** 2026-07-12
**Reviewer:** pi-subagent reviewer (Letter A)
**Subject:** [`../specifications/implementations/2026-07-11-api-secrets-env-management-design.md`](../specifications/implementations/2026-07-11-api-secrets-env-management-design.md)
**Pass:** 1
**Status:** in-review

## Verdict

**Request changes.** The build-mode guard, sheldon wiring, D1–D4 decisions,
template loop, runtime filter, `bw_session` helper, and static tests all match
the design and cited precedents. However, the file-mode mechanism is factually
broken: `# chezmoi:mode=600` is **not** a recognized chezmoi directive, and the
source file carries no `private_` attribute, so the rendered
`~/.config/zsh/rc/secrets.zsh` will be created at chezmoi's default (~`0644`),
**not** `0600` as required by S4 / I4. The static test only asserts the string is
present, giving false confidence, and the runtime mode check is deferred, so the
defect is currently uncaught.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| A-F1 | HIGH | open | `dot_config/zsh/rc/secrets.zsh.tmpl:1`, design §6 | `# chezmoi:mode=600` is not a valid chezmoi mode mechanism; rendered file will be ~`0644`, not `0600` (S4/I4 unmet) |
| A-F2 | LOW | addressed | `container/tests/container/test_api_secrets.py:24-33` | Build-mode guard test's "tail" assertion is near-vacuous (tail after final `{{- end -}}` is empty); body assertion is the real check |
| A-F3 | LOW | addressed | `dot_config/zsh/rc/secrets.zsh.tmpl:1-2` | `# chezmoi:mode=600` sits outside the `build_mode` guard, so it renders as a literal inert comment in every apply (incl. build-mode stub); harmless as a zsh comment but signals a mode intent that is not enforced |

### A-F1 details

Design §6 states the source file should carry a chezmoi `mode: 0600` attribute
(`.chezmoi.yaml.tmpl` or file-level directive), with a `run_after_chmod` fallback
"if chezmoi `mode` on a `.tmpl` is insufficient." The landed implementation uses
neither — it puts a bare comment on line 1:

```1:2:dot_config/zsh/rc/secrets.zsh.tmpl
# chezmoi:mode=600
{{- if not .build_mode -}}
```

Per chezmoi's documented model (reference/source-state-attributes,
reference/templates/directives, user-guide/manage-different-types-of-file):

- File permissions are set **only** by filename attributes — `private_`
  (clears group/world → `0600` from a `0644` base), `readonly_`, `executable_` —
  or by a `run_` chmod script. There is no per-file `mode:` key in chezmoi
  config, so the design §6 snippet also describes a non-existent feature.
- Template directives take the strict form `chezmoi:template:$KEY=$VALUE` and
  control template options (`missing-key`, delimiters, line-endings) only — never
  file mode. `chezmoi:mode=600` does **not** match that pattern, so chezmoi will
  neither act on it nor strip the line.

The source file is named `secrets.zsh.tmpl` with **no** `private_` prefix
(confirmed: `dot_config/zsh/rc/secrets.zsh.tmpl` is the only match). Therefore
`chezmoi apply` will render `~/.config/zsh/rc/secrets.zsh` at the default file
mode (~`0644`, umask-dependent), leaving a secrets-bearing file group/world
readable. This violates design invariant I4 ("Permissions must be `0600`") and
success criterion S4.

The repo's own precedent contradicts the chosen approach: existing private files
use the filename prefix (`dot_config/fcitx5/private_config`,
`dot_config/zsh-abbr/private_user-abbreviations`), not a mode comment.

**Suggested fix:** Rename the source to `private_secrets.zsh.tmpl` (chezmoi then
renders the target at `0600`), or add the `run_after_chmod-secrets-zsh` step the
design §6 already contemplates. Then add a runtime assertion (stat `%a` == `600`)
per design §10.2. This finding overlaps Letter B (secret-file permission), but is
reported here as a factual correctness defect: a design claim / static-test
assertion that does not achieve its stated effect.

**Verification steps:**
1. `chezmoi cat ~/.config/zsh/rc/secrets.zsh` then `stat -c %a` the applied target
   (currently deferred) — expected to show `644`, not `600`.
2. After fix (`private_` prefix), re-run and confirm `600`.

### A-F2 details

`test_secrets_template_build_mode_guard` computes
`guard_end = text.index("{{- end -}}")` (the single trailing-dash end, i.e. the
last line) and asserts `"bitwarden" not in tail`. Because the entire template
body lives inside the outer guard, `tail` is effectively empty, so that assertion
cannot fail. The meaningful coverage comes from the `body` assertion
(`"bitwardenFields" in body`) plus the `# chezmoi:mode=600` / guard-open string
checks. No correctness defect — noted so the aggregate does not over-credit the
"no bitwarden outside guard" claim to this near-vacuous branch.

### A-F3 details

Line 1 precedes the `{{- if not .build_mode -}}` guard, so it is emitted on every
render, including the build-mode stub. Design §6 explicitly permits "an empty file
(or a comment-only stub)," so build-mode behavior (S3) still holds — no
`bitwarden*` call executes when `build_mode = true`. The only consequence is a
harmless literal `# chezmoi:mode=600` comment line in the output; it does not
affect S3 and is subsumed by A-F1.

## Verified premises

- **P1 — build_mode guard (S1/S3/I-S6):** All three `bitwarden`/`bitwardenFields`
  calls sit inside the outer `{{- if not .build_mode -}} … {{- end -}}`
  (`secrets.zsh.tmpl:9-15`). Build-mode apply renders no Bitwarden resolution.
- **P2 — `.runtime` / `.build_mode` data flags exist:** `.chezmoi.toml.tmpl:12-13`
  defines `build_mode` (from `BUILD_MODE`) and `runtime` (from `DOTFILES_RUNTIME`,
  default `"host"`). The template's `$.runtime` comparison is well-defined.
- **P3 — runtime filter (§6):** `$rt := default "both" .runtime` +
  `$rtOk := or (eq $rt "both") (eq $rt $.runtime)` correctly renders `both`
  always, `host`/`container` only when `$.runtime` matches. Same compound-guard
  spirit as `dot_config/git/config.tmpl:4` (`and (not .build_mode) (eq .runtime "host")`).
- **P4 — template loop matches design §6 and SSH precedent:**
  `{{- range .api_secrets }}` mirrors `{{- range .ssh_keys }}` in
  `run_after_install-ssh-keys.sh.tmpl:56`; root data key `api_secrets` →
  `.api_secrets` as designed.
- **P5 — dynamic-field access is a correct, necessary deviation:** design §3 table
  shows dotted `(bitwardenFields …).<field>.value`, but the impl uses
  `(index $fields .field).value` (`secrets.zsh.tmpl:11`). Because `.field` is a
  loop variable (dynamic key), Go templates require `index`; the two forms are
  equivalent. Not a defect.
- **P6 — sheldon wiring (S5/§7):** `[plugins.my_secrets]` uses
  `apply = ["source"]`, `local = "~/.config/zsh/rc"`, `use = ["secrets.zsh"]`, no
  `defer` (`plugins.toml:110-114`). Order is
  `my_conf_defered` (105) → `my_secrets` (111) → `my_functions` (117), matching
  §7 and both order/sync static tests.
- **P7 — D1–D4:** Data file lists `GH_TOKEN`, `OPENROUTER_API_KEY`,
  `MOONSHOT_API_KEY`, `OLLAMA_API_KEY`, each `field: api_key`, no `enabled:`, no
  `OLLAMA_HOST` (`api_secrets.yaml:9-31`); tests assert all four + absence of
  `enabled:` / `OLLAMA_HOST`.
- **P8 — bw_session (S7/spec 13 §4):** `bw_session.zsh` uses
  `bw unlock --passwordfile /run/secrets/bw_password --raw` when the secret is
  readable, else `bw unlock --raw`; exports `BW_SESSION` in the current shell
  only, documents that entrypoint auth (§4) already handles runtime apply, and
  does not persist to a keyring — matching spec 13 §4 and Q2's interactive
  re-unlock recipe. Non-template file loaded by `[plugins.my_functions]`.
- **P9 — I3/I-S5:** No `bw` subprocess appears in `secrets.zsh.tmpl`; only
  `bitwardenFields` / `bitwarden` functions are used.
- **P10 — static tests pass:** `make test-container` → `20 passed in 0.51s`
  (re-run 2026-07-12), matching the result-log evidence table.
- **P11 — dash-trim false-negative avoided:** the corrected test matches
  `{{- if not .build_mode -}}` verbatim (`test_api_secrets.py:27`); the result-log
  documents the earlier grep/dash mismatch that was fixed in Phase 3.

## Open questions

- **Q1 (author):** How is `~/.config/zsh/rc/secrets.zsh` intended to reach mode
  `0600`? `# chezmoi:mode=600` does not do this. Will the fix be a `private_`
  filename prefix or a `run_after_chmod` step (design §6 fallback)? — must be
  resolved before S4/I4 can be marked met. (Ties to A-F1.)
- **Q2 (author):** Since all seed entries are `runtime: both`, the
  `host`/`container` filter path is exercised by no committed data and no test.
  Is a data-driven or fixture test of the `runtime` filter desired, or is the
  render-time behavior considered adequately covered by inspection?

## Deferred runtime verification (flagged from result-log)

Per `docs/issues/2026-07-11-phase-api-secrets-env-management.md`, the following
design §10 steps are **DEFERRED** (operator must fill real Bitwarden item IDs and
run `make up`), so they are not evidenced in this pass:

- §10.2 Runtime render + `secrets.zsh` mode `0600` — **DEFERRED**, and A-F1
  indicates it will currently render `~0644`; deferral is the reason this was not
  caught.
- §10.3 Interactive `printenv GH_TOKEN` non-empty — **DEFERRED** (needs real
  vault items).
- §10.4 `podman inspect` shows no provider keys / no `BW_*` — **DEFERRED**
  (Letter B primary scope).
- §10.1/§10.5 build secret-free + host-path render — statically consistent with
  the guard, but not runtime-evidenced.

Placeholder item IDs (`REPLACE_WITH_BITWARDEN_ITEM_ID`) remain in
`api_secrets.yaml`; per D4 a missing item fails loudly at template resolution,
which is the intended fail-loud signal rather than a silent empty export.
