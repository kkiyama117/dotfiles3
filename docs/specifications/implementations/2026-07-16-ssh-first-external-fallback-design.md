# SSH-first external repository fallback — Design

**Status:** Approved
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

- **S1:** Each managed repository uses its SSH URL when that URL is accessible,
  for both new clones and existing managed checkouts.
- **S2:** HTTPS is selected only for the repository whose SSH probe fails.
- **S3:** Explicit `PI_CONFIG_URL` and `NVIM_CONFIG_URL` values are used without
  probing or rewriting.
- **S4:** Repository selection is covered by deterministic tests that do not
  contact GitHub.
- **S5:** Existing startup signal handling, readiness ordering, and Bitwarden
  credential handling remain unchanged.
- **S6:** `make up` forwards non-secret URL/ref overrides to the container.
- **S7:** Environment-derived external URLs and refs cannot inject TOML.

## §2 Alternatives considered

### A1 — Independent SSH preflight (selected)

Probe each default SSH URL with a non-interactive `git ls-remote` wrapped in
an outer wall-clock timeout. Render the SSH URL on success and that
repository's fixed public HTTPS URL on failure.

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
- **I5:** An override means a non-empty value. URL/ref overrides are
  non-secret configuration and must not contain credentials.
- **I6:** The SSH probe uses `BatchMode=yes`, `GIT_TERMINAL_PROMPT=0`, an SSH
  five-second connection timeout, and a ten-second outer wall-clock timeout
  around the complete `git ls-remote`, followed by a two-second forced-kill
  grace if the child ignores `TERM`. The timeout command runs through
  `run_interruptible` so startup signals continue to reach the active child.
- **I6a:** URL selection runs in the entrypoint's parent shell and writes its
  result to a global `SELECTED_EXTERNAL_URL`; it is never invoked through
  command substitution, which would hide `child_pid` updates from the parent
  signal trap.
- **I7:** Probe failure is not fatal and does not weaken SSH host-key
  checking. Any probe failure, including an unknown or changed host key,
  selects that repository's fixed HTTPS URL and emits a warning.
- **I8:** The selected URL is used to render the runtime chezmoi config and is
  applied to an existing managed checkout's `origin` before
  `chezmoi apply`. Remote migration failure is fatal.
- **I9:** URL/ref values are quoted at the final TOML sink.
- **I10:** `make up` forwards `PI_CONFIG_URL`, `PI_CONFIG_REF`,
  `NVIM_CONFIG_URL`, and `NVIM_CONFIG_REF` when supplied by the operator.
- **I11:** Selection and remote migration do not log arbitrary override
  values.

## §4 Scope / staging breakdown

1. Add failing entrypoint tests for SSH success, failure, independent
   selection, explicit overrides, bounded probe execution, existing-remote
   migration, render integration, and TOML quoting.
2. Add a small URL-selection function to `entrypoint.sh` and use its results
   while rendering the runtime config. Update an existing managed checkout's
   `origin` to the selected URL before apply.
3. Forward optional URL/ref overrides in `Makefile`.
4. Quote URL/ref data at the final sink in `.chezmoiexternal.toml.tmpl`.
5. Update `docs/specifications/11-pre-required-env-values.md` and
   `docs/specifications/21-container-build-flow.md`.
6. Run the focused entrypoint test module and shell syntax validation.

No change is required to `.chezmoi.toml.tmpl`; its SSH defaults and
environment data flow are already correct.

## §5 Selection flow

For each repository:

1. If the corresponding URL environment variable is non-empty, validate that
   it contains no credential-bearing HTTP(S) userinfo and return it unchanged.
2. Otherwise run `git ls-remote` against the SSH default using SSH batch mode,
   disabled Git terminal prompting, a five-second SSH connection timeout, and
   a ten-second outer wall-clock timeout with a two-second forced-kill grace.
3. On success, return the SSH default.
4. On failure, emit a concise warning and return the public HTTPS fallback.

The two selected values are passed as `PI_CONFIG_URL` and `NVIM_CONFIG_URL`
to `chezmoi execute-template --init`. If `~/.pi` or `~/.config/nvim` is
already a Git checkout, the entrypoint sets its `origin` to the selected URL
before `chezmoi apply`. This makes the selected transport effective for both
new and existing checkouts.

The selector is called directly in the parent shell and assigns
`SELECTED_EXTERNAL_URL`. The caller copies that value into the repository's
named variable before selecting the next repository. It must not capture the
selector with `$(...)`, because that would isolate `run_interruptible` and its
`child_pid` from the parent signal trap.

## §6 Error handling and tests

Tests extract and execute the selection function with a fake `git` executable
on `PATH`, allowing success and failure to be controlled without network
access. Assertions verify:

- successful probes return both SSH defaults;
- failed probes return both HTTPS fallbacks;
- mixed probe results select different transports independently;
- explicit overrides are returned unchanged and do not invoke the probe;
- an empty override behaves as unset;
- a hanging fake probe is terminated by the outer timeout;
- a fake probe that ignores `TERM` is killed after the forced-kill grace;
- sending `TERM` during a hanging probe terminates its child and exits the
  entrypoint path with status 143;
- credential-bearing HTTP(S) overrides fail without being logged;
- existing managed checkouts have `origin` changed to the selected URL;
- remote migration failures stop startup;
- a fake `chezmoi` observes the independently selected render environment;
- URL/ref values containing TOML metacharacters remain quoted data;
- `make up` forwards all four optional URL/ref overrides;
- `zsh -n` accepts the modified entrypoint.

Actual `chezmoi apply` errors remain fatal and are not converted into transport
fallbacks.

## §7 Review response

- **A-F1 / D-F2:** RESOLVED — §3 I10 and §4 add `make up` override
  forwarding.
- **A-F2 / B-F1:** RESOLVED — §3 I6 and §5 require an outer wall-clock
  timeout and forced-kill grace around the complete probe.
- **A-F3:** RESOLVED — §6 adds a render-boundary integration test.
- **A-F4:** RESOLVED — §3 I5 and §5 define overrides as non-empty.
- **B-F2:** RESOLVED — §3 I9 and §4 require final-sink TOML quoting.
- **B-F3:** RESOLVED — §3 I7 preserves host-key checks and explicitly defines
  fixed-HTTPS fallback for every probe failure.
- **B-F4:** RESOLVED — §3 I5/I11 reject credential-bearing HTTP(S) overrides
  and prohibit logging arbitrary override values.
- **D-F1:** RESOLVED — the maintainer selected transport enforcement for
  existing checkouts; §3 I8 and §5 define remote migration.
- **D-F3:** RESOLVED — §4 includes spec 21 synchronization.
- **D-F4:** INCOMPLETE — lifecycle drift in the prior pi/nvim designs predates
  this change and does not alter its transport behavior. Follow-up targets are
  the existing design documents
  [`pi-config direct clone`](2026-07-14-pi-config-direct-clone-design.md) and
  [`nvim external config`](2026-07-09-nvim-external-config-design.md).
- **A-F5 / B-F5 / D-F5:** RESOLVED — §3 I6a, §5, and §6 require
  parent-shell result assignment and a signal-forwarding regression test.

## §8 Open questions

- **Q1:** None. The maintainer approved independent SSH-first selection for
  both repositories and selected-transport enforcement for existing
  checkouts on 2026-07-16.
