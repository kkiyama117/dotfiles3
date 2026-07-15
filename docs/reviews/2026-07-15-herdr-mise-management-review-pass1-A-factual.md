# herdr-mise-management — Review pass-1 (Letter A: factual / correctness)

**Date:** 2026-07-15
**Reviewer:** review subagent
**Subject:** [`docs/specifications/implementations/2026-07-15-herdr-mise-management-design.md`](docs/specifications/implementations/2026-07-15-herdr-mise-management-design.md)
**Pass:** 1
**Status:** done

## Verdict

**Approve.** Every load-bearing factual claim checks out against the cited sources (mise config, Containerfile, Makefile, `dot_zshenv.tmpl`, issue, prior result-log). Three LOW wording/precision items filed; none block implementation.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| A1 | LOW | addressed | design §1 (l.37–40) | aqua-prefix precedent wording over-stated `node`/`go`/`python` |
| A2 | LOW | addressed | design §5.4 (l.252–265) | single TOML snippet prescribed for both `config.toml` and `config.yml` |
| A3 | LOW | addressed | design §8 Q1 (l.350–357) | enumerated mise-tool list was broader than the result-log itemizes |

### A1 details

§1 originally said the aqua-prefix requirement is one "existing `[tools]` entries (`node`, `go`, `python`, `"npm:…"`, etc.) already follow." Per `dot_config/mise/config.toml` l.60–67, `node/go/python/deno/julia/pnpm/usage` are bare core tools with **no** backend prefix; only `"npm:@earendil-works/pi-coding-agent"` (l.67) demonstrates an explicit-backend key. The core claim (bare `herdr` won't resolve under `disable_default_registry = true`, l.50) is correct; only the illustrative list was imprecise.

**Suggested fix:** cite the `"npm:…"` entry as the precedent, not `node`/`go`/`python`.

**Verification:** re-read `dot_config/mise/config.toml` `[tools]` block.

### A2 details

§5.4 showed one `toml` block (`channel = "stable"`, `version_check = false`, `manifest_check = false`) and prescribed it for **both** `dot_config/herdr/config.toml` **and** `dot_config/herdr/config.yml`. TOML syntax is valid in the `.yml` file only because that file's body is TOML-formatted despite its extension. The design should state this explicitly to avoid a reader inferring YAML syntax is required.

**Suggested fix:** state that `config.yml` is a TOML-formatted legacy variant and the same TOML `[update]` block applies to both files.

**Verification:** `file dot_config/herdr/config.yml` / inspect first lines.

### A3 details

§8 Q1 stated the prior result-log "records a successful full five-stage build with the existing Layer 3-4 mise-managed tools (`node, python, deno, julia, pnpm, go, usage, pi-coding-agent`)." The cited result-log confirms a full ~17-min build and no regression, but does not itemize each mise tool by version. The tool names are corroborated by `config.toml` l.60–67; the claim was a reasonable inference, only slightly stronger than the log's literal text.

**Suggested fix:** state only what the result-log directly proves (successful full build + a working mise-dependent path such as `pi --version`).

**Verification:** re-read `docs/issues/2026-07-15-phase-herdr-container-install.md` acceptance evidence.

## Verified premises

- **P1:** Layer 3-4 runs `mise install --yes` over the rendered config and copies `.config/mise/.` into `$XDG_CONFIG_HOME/mise/` — `container/Containerfile` l.211–223. ✅
- **P2:** Layer 3-8 exists exactly as described (`ARG HERDR_VERSION=0.7.3` l.293, `ARG HERDR_SHA256` l.294, curl l.296, `sha256sum -c` l.298, `install -D -m 0755` + absolute-path `--version` l.299/301). ✅
- **P3:** `dot_zshenv.tmpl` activates shims via `eval "$(mise activate zsh --shims)"` (l.184) and `MISE_DATA_DIR` defaults to `$XDG_DATA_HOME/mise` = `~/.local/share/mise` (l.154, 94). ✅
- **P4:** I4 precedence holds — `.local/bin` is prepended at l.46, shims prepended later at l.185 (after the mise block runs), so with `typeset -U path` (l.21) shims outrank any stale `~/.local/bin/herdr`. ✅
- **P5:** `dotfiles_mise` volume wiring already exists (`Makefile` l.29 `MISE_VOLUME`, l.107 mount); copy-on-first-mount semantics documented l.22–26 — confirms I5/§6 and the "no Makefile change" non-scope. ✅
- **P6:** The `(N-/)` PATH-drop rationale for the old-plan Task 2 correction (§7, l.334–342) matches result-log l.17 verbatim and the glob at `dot_zshenv.tmpl` l.46. ✅
- **P7:** `disable_default_registry = true` is at `config.toml` l.50 exactly as §5.1 cites. ✅
- **P8:** Issue acceptance criteria 1–7 align 1:1 with design S1–S8. ✅

## Open questions

- None blocking. A2's intended `config.yml` format should be clarified in the next revise (non-blocking for approval).
