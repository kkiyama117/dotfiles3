# herdr-mise-management — Review pass-1 aggregate

**Date:** 2026-07-15
**Subject:** [`docs/specifications/implementations/2026-07-15-herdr-mise-management-design.md`](../specifications/implementations/2026-07-15-herdr-mise-management-design.md)
**Issue:** [`docs/issues/2026-07-15-herdr-mise-management.md`](../issues/2026-07-15-herdr-mise-management.md)
**Required letters:** A + C + E
**Pass termination condition:** every finding is `addressed` or `RESOLVED`; no `open` / `REGRESSION` / `blocked` remains.

## Letter reviews

| Letter | Verdict | File |
|---|---|---|
| A — factual / correctness | **Approve** | [`2026-07-15-herdr-mise-management-review-pass1-A-factual.md`](2026-07-15-herdr-mise-management-review-pass1-A-factual.md) |
| C — architecture / senior engineering | **Approve** | [`2026-07-15-herdr-mise-management-review-pass1-C-architecture.md`](2026-07-15-herdr-mise-management-review-pass1-C-architecture.md) |
| E — operability / runtime | **Approve** | [`2026-07-15-herdr-mise-management-review-pass1-E-operability.md`](2026-07-15-herdr-mise-management-review-pass1-E-operability.md) |

## Findings (deduplicated)

| ID | Letter | Severity | Status | Location | Summary |
|---|---|---|---|---|---|
| A1 | A | LOW | addressed | design §1 | aqua-prefix precedent wording over-stated `node`/`go`/`python`; only `"npm:…"` is a backend-prefix precedent |
| A2 | A | LOW | addressed | design §5.4 | TOML snippet prescribed for both `config.toml` and `config.yml`; `.yml` is TOML-formatted legacy variant |
| A3 | A | LOW | addressed | design §8 Q1 | enumerated mise-tool list broader than result-log itemizes; narrowed to what the log directly proves |
| C1 | C | LOW | addressed | design §6.2 | config acceptance command checks only `config.toml`, though `config.yml` is also changed |
| C2 | C | LOW | addressed | design I4 | PATH-precedence mitigation relies on stale binary absence, not ordering |
| E1 | E | LOW | addressed | design §6.1/§6.3 | existing-volume migration depends on raw `podman volume rm dotfiles_mise`; no dedicated make target |
| E2 | E | MEDIUM | addressed | design §8 Q1 / issue 2026-07-09 | aqua backend recurrence risk from 2026-07-09; stale relative to 2026-07-15 successful build, but tracker still open |

## Design-side responses

The author revised the design to address all pass-1 findings:

- **A1:** §1 now cites `"npm:@earendil-works/pi-coding-agent"` as the explicit-backend-prefix precedent and describes `node`/`go`/`python` as bare core-tool names. §2 Alternative B wording aligned.
- **A2:** §5.4 now states both `config.toml` and `config.yml` are TOML-formatted (the `.yml` extension is a legacy variant) and applies an identical TOML `[update]` block to both. No YAML syntax invented.
- **A3:** §8 Q1 now states only what the 2026-07-15 result-log directly proves: a successful full five-stage build plus a working Layer 3-4 mise-dependent path (`pi --version` PASS implies `mise exec node@latest` / aqua `pnpm` success).
- **C1:** §6.2 now includes both a `Config toml` and a `Config yml` acceptance grep.
- **C2:** No design change required; acceptance command `test ! -x $HOME/.local/bin/herdr` plus shim PATH ordering in `dot_zshenv.tmpl` remains the mitigation.
- **E1:** No design change required; raw `podman volume rm dotfiles_mise` is the documented and correct one-time migration step. A dedicated make target is out of scope.
- **E2:** No design change required; §8 Q1 retains the stale-evidence framing and makes recurrence an implementation blocker gated by the mandatory `make build` acceptance command.

## Pass termination judgement

All findings are `addressed`. No `open`, `REGRESSION`, or `blocked` items remain. The termination condition in [`../specifications/09-review.md`](../specifications/09-review.md) §2.3 is satisfied.

**Aggregate verdict: Approve.** The design may proceed to implementation planning.

## Residual risks to carry into implementation

1. **E1:** Operators must run raw `podman volume rm dotfiles_mise` for existing deployments; there is no dedicated make target.
2. **E2:** `herdr` uses the aqua backend. If the 2026-07-09 `pnpm` attestation failure mode recurs, it becomes an implementation blocker and must be diagnosed in the result-log.
3. **C2:** Confirm during implementation that `which herdr` resolves to the mise shim and that no stale `~/.local/bin/herdr` shadows it.
