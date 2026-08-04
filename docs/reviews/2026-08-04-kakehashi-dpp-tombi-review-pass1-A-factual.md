# kakehashi-dpp-tombi — Review pass-1 (Letter A: factual/spec fidelity)

**Date:** 2026-08-04  
**Reviewer:** Reviewer A  
**Subject:** [2026-08-04-kakehashi-dpp-tombi-design.md](docs/specifications/implementations/2026-08-04-kakehashi-dpp-tombi-design.md)  
**Pass:** 1  
**Status:** done

## 1. Verdict

**Request changes.** The schema misrepresents `MultipleHook`, and the new documents do not satisfy mandatory document structure or lifecycle requirements. Another review pass is required after the HIGH findings are resolved.

## 2. Findings

| ID | Severity | File | Status |
|---|---|---|---|
| A-F1 | HIGH | `docs/specifications/implementations/2026-08-04-kakehashi-dpp-tombi-design.md:9-119` | open |
| A-F2 | HIGH | `dot_config/tombi/dpp.schema.json:21-35` | open |
| A-F3 | MEDIUM | `dot_config/tombi/dpp.schema.json:95-99` | open |
| A-F4 | LOW | `docs/specifications/implementations/2026-08-04-kakehashi-dpp-tombi-design.md:11-15` | open |
| A-F5 | LOW | `docs/specifications/implementations/2026-08-04-kakehashi-dpp-tombi-design.md:25-40`; `dot_config/tombi/config.toml:3-12` | open |
| A-F6 | HIGH | `docs/issues/2026-08-04-kakehashi-dpp-tombi.md:3-28` | open |
| A-F7 | HIGH | `docs/specifications/implementations/2026-08-04-kakehashi-dpp-tombi-design.md:3,82-104` | open |

## 3. Detailed findings

### A-F1

The design does not meet the mandatory design structure in `docs/specifications/00-document-management.md:127-146`:

- §1 lacks labeled success criteria (`S1`, `S2`, …).
- §4 gives scope but no staging breakdown.
- There is no Open questions section with `Q<n>` labels.
- Risks are present, but they do not substitute for the required Open questions section.

Add explicit, labeled success criteria; describe implementation stages; and add an Open questions section, even if it states that there are no remaining questions.

### A-F2

The schema’s `multiple_hooks` definition is incompatible with the cited upstream type. It requires `hooks_file` and rejects every property other than `plugins` and `hooks_file`:

```21:35:dot_config/tombi/dpp.schema.json
"multiple_hooks": {
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "plugins": {
        "type": "array",
        "items": { "type": "string" }
      },
      "hooks_file": { "type": "string" }
    },
    "required": ["plugins", "hooks_file"],
    "additionalProperties": false
  }
}
```

The inspected dpp.vim `MultipleHook` type instead defines:

- required `plugins: string[]`
- optional `hooks_file`
- optional `hook_add`
- optional `hook_source`
- optional `hook_post_source`

Consequently, valid upstream configurations can be rejected, contradicting I-DT2. Update the schema to include all five properties and require only `plugins`.

### A-F3

`dummy_mappings` represents the upstream tuple `[string, string][]`, but its item schema has neither `minItems: 2` nor `maxItems: 2`. `prefixItems` alone does not restrict array length, and the general `items` schema permits zero, one, or more than two strings.

Constrain every mapping to exactly two string elements.

### A-F4

The statement that dpp-ext-toml provides “no syntax” and that `syntax()` is guarded by `if !has('nvim')` is false.

The inspected `autoload/dpp/ext/toml.vim:1-36` executes syntax embedding for Vim and Neovim. Its only Neovim-specific guard is:

```vim
if has('nvim') && exists(':TSBufDisable')
  TSBufDisable highlight
endif
```

This does not undermine the LSP approach, but §1 should accurately describe the extension as providing manual Vim syntax embedding—not schema validation or LSP integration.

### A-F5

The discovery description is incomplete:

- Tombi 1.2.6 checks `/etc/tombi/config.toml` on Linux after user configuration and before built-in defaults.
- `dot_config/tombi/config.toml:6` says “first match wins, walk continues at parent dirs.” The implementation returns immediately after a project-config hit; walking continues only while no usable project config has been found.
- The risk list at design lines 110–113 omits `.tombi.toml`, although it has the highest per-directory precedence and also shadows user configuration.

Document the Linux system-config fallback, clarify traversal wording, and include `.tombi.toml` in the shadowing risk.

### A-F6

The issue does not satisfy the new-document minimum in `docs/specifications/00-document-management.md:103-125`:

- It has no `## Context`.
- It has no `## Notes`.
- `Related` does not link back to the design.
- Its status line links to `2026-08-04-phase-kakehashi-dpp-tombi.md`, which does not exist.

Add the required sections and reciprocal design link. Remove the premature result-log link or create it only at the lifecycle stage prescribed by the spec.

### A-F7

The document is `DRAFT`, but §5 says implementation verification was already executed, while §4 still describes the result-log and issue closure as future scope. This conflicts with the lifecycle in `docs/specifications/00-document-management.md:62-91`, where design approval precedes the implementation plan and execution evidence.

Clarify whether §5 is exploratory evidence or completed implementation. If it is completed implementation, record and reconcile the lifecycle exception; otherwise move these claims into proposed verification steps and execute them through an approved plan/result-log.

## 4. Summary / response obligations

Open HIGH findings `A-F1`, `A-F2`, `A-F6`, and `A-F7` mandate another pass under review spec §2.3.

The next revision must quote these IDs verbatim when recording responses:

- `A-F1`: restore mandatory design structure and labels.
- `A-F2`: correct `MultipleHook` schema fidelity.
- `A-F3`: constrain `dummy_mappings` tuples.
- `A-F4`: correct the syntax-integration description.
- `A-F5`: correct and complete configuration discovery details.
- `A-F6`: bring the issue document into compliance.
- `A-F7`: reconcile design status, implementation, and verification lifecycle.

## 5. Notes

Verified premises:

- Tombi v1.2.6 performs per-document walk-up discovery in the stated project-file precedence.
- A discovered project configuration replaces the user configuration rather than merging.
- Relative schema paths resolve from the configuration directory.
- User-config schema globs can match the canonical absolute document path.
- Schema strictness defaults to true; explicit `additionalProperties` takes precedence.
- The global kakehashi configuration declares tombi for `toml`.
- The nvim configuration lists tombi for the `toml` filetype and is rooted in a Git repository.
- Exactly eight root-level `~/.config/nvim/deps/*.toml` files were observed.
- No test suite was run, as requested.

Residual risks:

- The design’s claimed CLI/LSP diagnostics were not reproduced during this read-only review.
- `tombi` was not available on the review shell’s PATH, so the installed binary version could not be independently confirmed; source claims were checked against tag `v1.2.6`.
- The schema was compared with inspected upstream types and current files, not every possible runtime extension field.