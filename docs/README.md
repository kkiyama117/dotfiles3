# `docs/`

The layout, naming conventions, and lifecycle of this directory are defined in [`specifications/00-document-management.md`](specifications/00-document-management.md).
And you also need to read or update specifications in [`specifications/`](specifications/)

## Subdirectories

| Dir | Type | Naming |
|-----|------|--------|
| [`issues/`](issues/) | `issue` + `result-log` | `YYYY-MM-DD-<slug>.md` |
| [`plans/`](plans/) | `plan` | `YYYY-MM-DD-<slug>-impl.md` |
| [`references/`](references/) | `reference` | `<topic>.md` or `YYYY-MM-DD-<topic>.md` |
| [`reviews/`](reviews/) | `review` | `YYYY-MM-DD-<slug>-review[-passN][-<letter>-<topic>][-prompt].md` |
| [`specifications/`](specifications/) | `spec` (normative) + `implementations/*-design.md` | `NN-<topic>.md` / `<topic>.md` / `YYYY-MM-DD-<slug>-design.md` |

## Document Lifecycle (Summary)

`issue → design (DRAFT) → review pass-N → design (Approved) → plan (-impl) → result-log → issue (closed)`

For details, see [`specifications/00-document-management.md`](specifications/00-document-management.md) §4.

## Review Perspectives & Output Schema

Refer to [`specifications/09-review.md`](specifications/09-review.md) (pass/letter model, required letters, output schema, severity, status, aggregate review, and response obligations).
