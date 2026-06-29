# Specifications

Normative specs for `dotfiles3`. Conventions: see [`00-document-management.md`](00-document-management.md).
TODO: refactor and classify documents

## Index

### 0x — Repository-wide conventions

| Spec | Status | Summary |
|---|---|---|
| [`00-document-management.md`](00-document-management.md) | active | Document placement, naming, lifecycle. SoT for all docs. |
| [`01-automations.md`](01-automations.md) | DRAFT (stub) | Make targets and generators (`make gen-deps`, chezmoi deploy). |
| [`02-installed-programs.md`](02-installed-programs.md) | DRAFT | Normative contract for tool inventory. Pairs with [`02-installed-programs.md`](02-installed-programs.md). |
| [`03-makefile.md`](03-makefile.md) | empty (stub) | Target naming + dependency contract for `Makefile`. |

### 1x — Host / install prerequisites?

| Spec | Status | Summary |
|---|---|---|
| [`11-pre-required-env-values.md`](11-pre-required-env-values.md) | DRAFT | Secrets, Bitwarden items, env vars required before apply/build. |
| [`12-quickstart.md`](12-quickstart.md) | DRAFT | User-facing quickstart (local + container). |

### 2x — Container

| Spec | Status | Summary |
|---|---|---|
| [`20-container-rules.md`](20-container-rules.md) | DRAFT (stub) | Rootless / userns / bind-mount invariants. |
| [`21-container-build-flow.md`](21-container-build-flow.md) | empty (stub) | Containerfile layer breakdown and stage ordering. |
| [`22-container-build-pre-required-envs.md`](22-container-build-pre-required-envs.md) | DRAFT | Build-time envs (`HOST_UID`, `HOST_GID`, `BW_ID`, `JOBS`). |

### Functional docs (non-`NN-`)

| Doc | Pairs with | Summary |
|---|---|---|
| [`02-installed-programs.md`](02-installed-programs.md) | `02-installed-programs.md` | Current tool inventory (hand-edited until `gen-deps` lands). |
| `implementation/` | `00-document-management.md §3` | Per-issue design DRAFTs. Not created yet. |

> `api.md` was removed — the scope was never settled (chezmoi data / Make entrypoints / container runtime contract all already had owners). Do not link to `specifications/api.md` from new docs.

## Status legend

- **active** — used in steady state
- **DRAFT** — has structure but content is incomplete; safe to read but cite with care
- **DRAFT (stub)** — section headers only; content TBD
- **empty (stub)** — placeholder file; nothing useful yet
