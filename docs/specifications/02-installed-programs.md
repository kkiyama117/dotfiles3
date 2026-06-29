# 02 — Installed Programs

> Spec status: **DRAFT**. This is the single SoT spec for the tool
> inventory — both the **contract** for how tools are declared and the
> **list** itself (rendered into the AUTO-GEN block below by the planned
> `dependencies/gen.py`). The prior split into a separate
> `02-installed-programs.md` functional doc was removed; everything lives
> here now.

## Source of truth

- Hand-edited SoT for tool definitions: [`../../dependencies/packages.toml`](../../dependencies/packages.toml)
- Generated artifacts (all derived from `packages.toml`):
  - `../../dependencies/layer_<N>.txt` — per-layer install lists for the Containerfile
  - The AUTO-GEN block at the end of this document

`packages.toml` schema is documented at the top of that file. New tool
entries belong there only — never edit the AUTO-GEN block by hand.

## Contract

| Field | Required | Allowed values |
|---|---|---|
| `name`        | yes | string |
| `manager`     | yes | `pacman` / `paru` / `nix` / `mise` / `uv` |
| `layer`       | yes | integer ≥ 1 (Containerfile layer index) |
| `has_configs` | yes | bool — true if config is templated under chezmoi |
| `description` | no  | string — used in the AUTO-GEN block |

## Regeneration

Run `make gen-deps` (planned; tracked in [`08-automations.md`](08-automations.md))
to rewrite the AUTO-GEN block from `packages.toml`.

<!-- BEGIN AUTO-GEN: installed-programs -->
_(empty — populate via `make gen-deps`; until then the canonical list is in [`02-installed-programs.md`](02-installed-programs.md))_
<!-- END AUTO-GEN: installed-programs -->
