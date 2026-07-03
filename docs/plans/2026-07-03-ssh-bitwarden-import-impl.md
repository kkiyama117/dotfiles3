# SSH Bitwarden import — Implementation Plan

**Status:** executing
**Spec:** [`docs/specifications/implementations/2026-07-03-ssh-bitwarden-import-design.md`](../specifications/implementations/2026-07-03-ssh-bitwarden-import-design.md)
**Parent issue:** [`docs/issues/2026-07-03-ssh-bitwarden-import.md`](../issues/2026-07-03-ssh-bitwarden-import.md)
**Review trail:** conversational approval 2026-07-03 for Bitwarden-as-source-of-truth. The design remains DRAFT and the first real Bitwarden item ID is not yet supplied, so this implementation ships an opt-in sample entry that is disabled until the maintainer fills non-secret metadata.

## Phases

### Phase 1 — Guarded import plumbing

1. Add `.chezmoidata/ssh_keys.yaml` with non-secret import metadata only.
2. Add `.chezmoiscripts/run_after_install-ssh-keys.sh.tmpl`.
3. Gate all Bitwarden attachment evaluation behind:
   `{{ if and (not .build_mode) (eq .runtime "container") (env "BW_SESSION") }}`.
4. Keep sample entries disabled until a real Bitwarden item ID / stable name is supplied.
5. Write key files only under container `~/.ssh`, skip existing private keys, use temporary files in `~/.ssh`, and set OpenSSH-compatible modes.

**Acceptance:** build-mode / no-session template render does not contain Bitwarden attachment calls or private material; runtime-enabled render contains the import logic only when enabled metadata exists.
**Rollback:** delete `.chezmoidata/ssh_keys.yaml` and `.chezmoiscripts/run_after_install-ssh-keys.sh.tmpl`.

### Phase 2 — Documentation sync

1. Update spec 11 with the SSH Bitwarden item metadata contract.
2. Update spec 25 from deferred future work to documented optional automated import.
3. Update the parent issue with design / plan links and the staged status.

**Acceptance:** docs describe that missing `BW_SESSION` remains no-op and that no key material belongs in the repo, image, `.env`, or Podman inspect environment.
**Rollback:** revert the documentation edits.

### Phase 3 — Verification

1. Run static checks for placeholders and forbidden secret-looking content.
2. Render the template in build/no-session mode.
3. If shell access and Bitwarden state permit, run `make build`; runtime import with a real Bitwarden item is a maintainer follow-up because the item ID is not yet configured in this change.

**Acceptance:** all available checks pass, or any unavailable checks are explicitly recorded.
**Rollback:** same as earlier phases.
