# API provider secrets as environment variables (Bitwarden + chezmoi)

**Date:** 2026-07-11
**Status:** open
**Related:** [design](../specifications/implementations/2026-07-11-api-secrets-env-management-design.md), [plan](../plans/2026-07-11-api-secrets-env-management-impl.md), [review prompt pass 1](../reviews/2026-07-11-api-secrets-env-management-review-prompt-pass1.md), [result-log](2026-07-11-phase-api-secrets-env-management.md)

## Context

The host inventory (`docs/references/host_config_list.md`) lists
`~/.config/zsh/rc/secrets.zsh` as a confidential file that must be
ported to chezmoi templates. The new repository has Bitwarden runtime
auth (spec 13 §4) and sheldon plugin loading (`dot_config/sheldon/plugins.toml`),
but no API-key env exports yet.

Consumers include `gh` (`GH_TOKEN`), pi and other AI agents
(`OPENROUTER_API_KEY`, `MOONSHOT_API_KEY`, `OLLAMA_API_KEY`, etc.).

## Problem

How should GitHub and AI-provider API keys be sourced from Bitwarden,
rendered by chezmoi at runtime apply, exported as shell environment
variables, and loaded into interactive zsh — without baking secrets into
image layers, the repository, or `.env`?

## Acceptance criteria

- **A1:** `chezmoi apply` on host (with `BW_SESSION`) and container
  (entrypoint auto-auth) renders `~/.config/zsh/rc/secrets.zsh` with
  configured provider env exports.
- **A2:** No resolved API key appears in git, `.env`, image layers, or
  `podman inspect` env.
- **A3:** Rendered `secrets.zsh` is mode `0600` and owned by the dotfiles
  user.
- **A4:** sheldon loads `secrets.zsh` synchronously so child processes
  inherit provider env vars.
- **A5:** `.chezmoidata/api_secrets.yaml` holds only non-secret metadata
  (item IDs, env var names, field names); spec 11 Bitwarden-items table
  is populated.
- **A6:** `bw_session.zsh` helper exists for interactive re-unlock inside
  `podman exec` shells (spec 13 §4 recipe).
- **A7:** Design passes review letters A + B + D before implementation.

## Notes

- Follows spec 13 invariants (I-S1..I-S6); does not add Tier-1 podman
  secrets for API keys.
- Pi runtime credentials under `~/.pi/agent` remain out of scope per
  spec 11.
