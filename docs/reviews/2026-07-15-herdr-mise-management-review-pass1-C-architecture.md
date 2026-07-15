# herdr-mise-management — Review pass-1 (Letter C: architecture / senior engineering)

**Date:** 2026-07-15
**Reviewer:** review subagent
**Subject:** [`docs/specifications/implementations/2026-07-15-herdr-mise-management-design.md`](docs/specifications/implementations/2026-07-15-herdr-mise-management-design.md)
**Pass:** 1
**Status:** done

## Verdict

**Approve.** The six coherence targets hold up against the source files. No blockers; two non-blocking notes.

## Findings

| ID | Severity | Status | Location | Summary |
|---|---|---|---|---|
| C1 | LOW | addressed | design §6.2 (l.288) | config verification checks only `config.toml`, though `config.yml` is also changed |
| C2 | LOW | addressed | design I4 (l.135) | PATH-precedence mitigation relies on stale binary absence, not ordering |

### C1 details

S4/§5.4 update **both** `config.toml` and `config.yml`, but the §6.2 "Config" acceptance command greps only `~/.config/herdr/config.toml`. Not a defect (the table is a sample), but adding a `config.yml` check would make the acceptance surface match the stated change surface.

**Suggested fix:** add a `config.yml` grep to §6.2.

**Verification:** re-read §6.2 after revise.

### C2 details

I4 warns a stale `~/.local/bin/herdr` must not shadow the shim; §6.2 mitigates via `test ! -x $HOME/.local/bin/herdr`. Since `~/.local/bin` may precede shims in PATH, the mitigation rests on the binary being absent post-rebuild rather than on ordering. Adequate for a design; worth a one-line confirmation during implementation.

**Suggested fix:** none required at design level; keep the existing acceptance command.

**Verification:** implementation build confirms `which herdr` resolves to shim.

## Verified premises

- **Correct — Herdr removed from `packages.toml` (not converted).** Current block `dependencies/packages.toml:508-515` (`manager = "custom"`, `layer = 3`) is deleted per S2 / §4.2 / §5.3. This is the only coherent option: the schema allowed-`manager` set (`02-installed-programs.md:29`, and `packages.toml:14`) excludes `mise`, and `test_mise_manager.py:20-41` actively rejects `manager = "mise"` and any `layer_3/mise.txt`. Alternative B (`manager = "mise"`) is correctly rejected (design §2 B) as it would violate that contract. Consistent.
- **Correct — Intentional AUTO-GEN disappearance.** `custom` entries render into the AUTO-GEN block (`02-installed-programs.md:55-60`), so removing the entry + `make gen-deps` legitimately drops the Layer 3 row. §5.3 names the disappearance "intentional" and §6.2 gates it (`make gen-deps` twice → idempotent, no `herdr`). Matches the "never hand-edit AUTO-GEN" rule (`02:19`). Coherent.
- **Correct — Sole mise authority.** I1/S1 + product decisions route install/version/update solely through `mise` with `"aqua:ogulcancelik/herdr" = "latest"`; I2 correctly requires the fully-qualified `aqua:` id given `disable_default_registry = true`. Spec 02 already names `dot_config/mise/config.toml` the mise SoT (`02:11`, `02:20-21`). I6/S4/§5.4 disable Herdr's own `version_check`/`manifest_check` so no second authority competes. Internally consistent.
- **Correct — Historical treatment.** §7 table + I8 + S8 preserve the closed issue/result-log/plan bodies byte-identical, mark old design `superseded` (header/status only), and old plan `executed` with a forward link and the Task 2 `install -D` snippet correction. §7 explicitly overturns old §2 option D by product approval "without rewriting the historical rejection text." Non-scope list (§4) reinforces no body edits. Coherent and self-consistent.
- **Correct — `latest` tradeoff.** I3 states plainly that `latest` is non-reproducible at the config layer, that this replaces the old `ARG HERDR_VERSION`/`ARG HERDR_SHA256` gate, and that build reproducibility is deliberately traded for parity with `node = "latest"` etc.; the `make build` acceptance (§6.2) is the compensating gate. Alternative C (pinned version) is explicitly weighed and rejected. Sound reasoning.
- **Correct — Rollback.** §6.3 mirrors the forward migration: `git revert` → restore `packages.toml` entry + Containerfile Layer 3-8 → drop mise entry / restore `[update]` flags → `make build && make down && podman volume rm dotfiles_mise && make up`. The volume-rm step is consistent with the first-mount seed semantics in I5 / §6.1. Coherent.

## Open questions

- None blocking.
