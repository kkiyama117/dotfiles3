# AGENTS.md

Common protocol for AI agents and human maintainers performing review, design,
and implementation in this repository. This file is the **top-level entry
point**; normative details live in the specifications under
`docs/specifications/`.

---

## §1 Scope

- Target repository: `dotfiles3` (chezmoi source + Podman container)
- Applies to: every action that produces a design / plan / review / result-log
- When doing everything, read related specifications first.
- When writing code, check specs, update specifications if not updated, and follow the protocol. 

### Must Read specs
  - Document placement & naming: [`00-document-management.md`](docs/specifications/00-document-management.md)
  - Review protocol (pass/letter model, output schema, severity, status, aggregate review, response obligations) → [`09-review.md`](docs/specifications/09-review.md)
  - Secret management → [`docs/specifications/11-pre-required-env-values.md`](docs/specifications/11-pre-required-env-values.md)

---

## §2 Revision procedure

This file is itself one of the specs. To revise:

1. File an issue in `docs/issues/` describing the reason
2. For large changes, go through `docs/specifications/implementation/<slug>-agents-rev-design.md`
3. Edit this file; include the issue path in the commit message
4. Synchronize cross-referencing files (e.g. `09-review.md`, `00-document-management.md`) in the same commit

## AI Agent skills

You must follow this local folder rule (especially documents under `docs` folder). 
And you can use AI agents skill in `.agents/skills` folder.
When using any skills and confliction occur between skills and local docs, use local rule normally; ask which should follow to user when you can't decide.
