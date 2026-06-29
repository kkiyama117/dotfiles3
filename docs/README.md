# `docs/`

The layout, naming conventions, and lifecycle of this directory are defined in [`specifications/00-document-management.md`](specifications/00-document-management.md). For meta-rules targeting AI agents, refer to [`AGENTS.md`](../AGENTS.md) at the repository root.

## Subdirectories

| Dir | Type | Naming |
|-----|------|--------|
| [`issues/`](issues/) | `issue` + `result-log` | `YYYY-MM-DD-<slug>.md` |
| [`plans/`](plans/) | `plan` | `YYYY-MM-DD-<slug>-impl.md` |
| [`references/`](references/) | `reference` | `<topic>.md` or `YYYY-MM-DD-<topic>.md` |
| [`reviews/`](reviews/) | `review` | `YYYY-MM-DD-<slug>-review[-passN][-<letter>-<topic>][-prompt].md` |
| [`specifications/`](specifications/) | `spec` (normative) + `implementation/*-design.md` | `NN-<topic>.md` / `<topic>.md` / `YYYY-MM-DD-<slug>-design.md` |

## Document Lifecycle (Summary)

`issue → design (DRAFT) → review pass-N → design (Approved) → plan (-impl) → result-log → issue (closed)`

For details, see [`specifications/00-document-management.md`](specifications/00-document-management.md) §4.

## Review Perspectives & Output Schema

Refer to [`../AGENTS.md`](../AGENTS.md) §2–§3.
