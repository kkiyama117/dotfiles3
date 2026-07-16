# SSH-first external repository fallback — Design

**Status:** DRAFT
**Date opened:** 2026-07-16
**Issue:** [Use SSH first for managed external repositories](../../issues/2026-07-16-ssh-first-external-fallback.md)
**Author:** kiyama

## §1 Context & success criteria

`.chezmoi.toml.tmpl` correctly defines
`git@github.com:kkiyama117/pi-config.git` and
`git@github.com:kkiyama117/nvim_config.git` as the default external sources.
The container entrypoint currently replaces both defaults with HTTPS
unconditionally. That avoids the first-run SSH dependency cycle, but it also
bypasses a working persistent SSH configuration on every later startup.

- **S1:** Each managed repository uses its SSH URL when that URL is accessible.
- **S2:** HTTPS is selected only for the repository whose SSH probe fails.
- **S3:** Explicit `PI_CONFIG_URL` and `NVIM_CONFIG_URL` values are used without
  probing or rewriting.
- **S4:** Repository selection is covered by deterministic tests that do not
  contact GitHub.
- **S5:** Existing startup signal handling, readiness ordering, and Bitwarden
  credential handling remain unchanged.

## §2 Alternatives considered

### A1 — Independent SSH preflight (selected)

Probe each default SSH URL with a non-interactive, timeout-bounded
`git ls-remote`. Render the SSH URL on success and that repository's public
HTTPS URL on failure.

This directly distinguishes usable SSH transport from unavailable SSH and
keeps fallback decisions independent.

### A2 — Retry the complete apply over HTTPS

Render SSH first and rerun `chezmoi apply` with HTTPS after any failure.
Rejected because an apply can fail for unrelated template, Bitwarden, or
filesystem reasons; retrying would misclassify those failures and repeat
partial side effects.

### A3 — Split SSH provisioning and external application

Apply only SSH files and key import first, then apply externals. Rejected
because it couples the entrypoint to chezmoi target ordering and introduces a
second apply phase for a transport-selection problem.

## §3 Architecture / invariants

- **I1:** SSH remains the canonical default in `.chezmoi.toml.tmpl`.
- **I2:** The entrypoint defines paired SSH and HTTPS URLs for each managed
  GitHub repository.
- **I3:** URL selection is independent: one repository can use SSH while the
  other falls back to HTTPS.
- **I4:** An explicit environment override bypasses default URL selection.
- **I5:** The SSH probe cannot prompt for credentials and has a finite
  connection timeout.
- **I6:** Probe failure is not fatal; it selects HTTPS for that repository.
- **I7:** The selected URL is used only to render the runtime chezmoi config.
  The entrypoint does not rewrite an existing Git remote.

## §4 Scope / staging breakdown

1. Add failing entrypoint tests for SSH success, failure, independent
   selection, and explicit overrides.
2. Add a small URL-selection function to `entrypoint.sh` and use its results
   while rendering the runtime config.
3. Update `docs/specifications/11-pre-required-env-values.md` to replace the
   unconditional-HTTPS statement with SSH-first behavior.
4. Run the focused entrypoint test module and shell syntax validation.

No changes are required to `.chezmoi.toml.tmpl` or
`.chezmoiexternal.toml.tmpl`; their SSH defaults and data flow are already
correct.

## §5 Selection flow

For each repository:

1. If the corresponding URL environment variable is set, return it unchanged.
2. Otherwise run `git ls-remote` against the SSH default using SSH batch mode
   and a finite connection timeout.
3. On success, return the SSH default.
4. On failure, emit a concise warning and return the public HTTPS fallback.

The two selected values are passed as `PI_CONFIG_URL` and `NVIM_CONFIG_URL`
only to `chezmoi execute-template --init`.

## §6 Error handling and tests

Tests extract and execute the selection function with a fake `git` executable
on `PATH`, allowing success and failure to be controlled without network
access. Assertions verify:

- successful probes return both SSH defaults;
- failed probes return both HTTPS fallbacks;
- mixed probe results select different transports independently;
- explicit overrides are returned unchanged and do not invoke the probe;
- the entrypoint still never calls `git remote set-url`;
- `zsh -n` accepts the modified entrypoint.

Actual `chezmoi apply` errors remain fatal and are not converted into transport
fallbacks.

## §7 Open questions

- **Q1:** None. The maintainer approved independent SSH-first selection for
  both repositories on 2026-07-16.
