# SSH-first external repository fallback — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Status:** pending
**Spec:** [SSH-first external repository fallback design](../specifications/implementations/2026-07-16-ssh-first-external-fallback-design.md)
**Parent issue:** [Use SSH first for managed external repositories](../issues/2026-07-16-ssh-first-external-fallback.md)
**Review trail:** [Aggregate pass 1](../reviews/2026-07-16-ssh-first-external-fallback-review-pass1.md)

**Goal:** Use each managed repository's SSH URL whenever an independent,
bounded SSH probe succeeds, with HTTPS only as that repository's fallback.

**Architecture:** The entrypoint selects each URL in the parent shell, renders
the selected values into chezmoi config, and updates existing managed
checkouts to the selected transport before apply. `Makefile` forwards optional
non-secret overrides, and the external template quotes values at the final
TOML sink.

**Tech stack:** zsh, Git/OpenSSH, GNU coreutils `timeout`, chezmoi Go
templates, Podman Make targets, pytest.

## Global constraints

- Probe each repository independently.
- Use a five-second SSH connection timeout.
- Use a ten-second outer timeout with a two-second forced-kill grace.
- Keep OpenSSH host-key checking enabled.
- Use only fixed public HTTPS fallback constants.
- Treat only non-empty environment values as explicit overrides.
- Reject credential-bearing HTTP(S) userinfo without logging the URL.
- Do not use command substitution to capture selector output.
- Migrate an existing managed checkout's `origin`; migration failure is fatal.
- Preserve existing readiness, Bitwarden, and signal behavior.

---

## Phases

### Phase 1 — Tests first: transport selection and integration

**Files:**
- Modify: `container/tests/container/test_entrypoint.py`

**Interfaces:**
- Consumes: `entrypoint.sh` text and fake executables on `PATH`.
- Produces: regression coverage for selector behavior, timeout/TERM handling,
  remote migration, Makefile forwarding, and external-template quoting.

- [ ] **Step 1: Replace the unconditional-HTTPS assertion with failing
  selector behavior tests**

Add a reusable extractor and runner:

```python
def shell_function(text: str, name: str) -> str:
    start = text.index(f"{name}() {{")
    end = text.index("\n}\n", start) + len("\n}\n")
    return text[start:end]


def write_executable(path: Path, body: str) -> None:
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(0o755)
```

Run `select_external_url` with fake `git` implementations that succeed,
fail, or discriminate by repository name. Assert:

```python
assert selected_pi == "git@github.com:kkiyama117/pi-config.git"
assert selected_nvim == "https://github.com/kkiyama117/nvim_config.git"
```

Also assert a non-empty `file:///data/nvim_config` override bypasses the fake
probe, while an empty override probes normally.

- [ ] **Step 2: Add failing validation, timeout, and signal tests**

Use a fake `git` that traps or ignores `TERM`. Assert the selector command
contains and behavior enforces:

```python
assert "BatchMode=yes" in function
assert "ConnectTimeout=5" in function
assert "GIT_TERMINAL_PROMPT=0" in function
assert "--kill-after=2s" in function
assert "10s" in function
assert "$(" not in selection_call_block
```

For the runtime checks, start a zsh snippet with
`subprocess.Popen(..., start_new_session=True)`, wait for the fake probe PID
file, send `SIGTERM` to the zsh process, and assert status 143 plus child
termination. For a child that ignores `TERM`, assert selection returns the
fixed HTTPS fallback within 13 seconds.

Assert `https://token@github.com/owner/repo.git` is rejected, the captured
stderr does not contain `token`, and no fake Git call occurs.

- [ ] **Step 3: Add failing remote migration and render-boundary tests**

Extract `set_external_remote_url`, initialize temporary Git repositories with
an `origin`, run the function, and assert:

```python
assert subprocess.check_output(
    ["git", "-C", str(checkout), "remote", "get-url", "origin"],
    text=True,
).strip() == selected_url
```

Assert a Git checkout without `origin` returns non-zero. Use fake `git` and
fake `chezmoi` executables to record the `PI_CONFIG_URL` and
`NVIM_CONFIG_URL` seen at the render boundary for a mixed SSH/HTTPS result.

- [ ] **Step 4: Add failing Makefile and final-sink quoting tests**

Assert the `up` recipe forwards:

```python
for variable in (
    "PI_CONFIG_URL",
    "PI_CONFIG_REF",
    "NVIM_CONFIG_URL",
    "NVIM_CONFIG_REF",
):
    assert f"--env {variable}" in up_target
```

Assert `.chezmoiexternal.toml.tmpl` uses:

```python
assert "url = {{ .pi_config_url | quote }}" in external
assert '{{ .pi_config_ref | quote }}' in external
assert "url = {{ .nvim_config_url | quote }}" in external
assert '{{ .nvim_config_ref | quote }}' in external
```

Render the template with:

```python
rendered = subprocess.run(
    [
        "chezmoi",
        "execute-template",
        "--init",
        "--config",
        str(config_path),
    ],
    input=external,
    text=True,
    capture_output=True,
    check=True,
).stdout
parsed = tomllib.loads(rendered)
assert parsed[".pi"]["url"] == 'https://github.com/example/pi-"quoted".git'
assert parsed[".config/nvim"]["clone"]["args"][1] == 'branch-"quoted"'
```

The temporary chezmoi config supplies the quoted URL/ref test values under
`[data]`, with `build_mode = false` and `runtime = "container"`.

- [ ] **Step 5: Run focused tests and verify RED**

Run:

```bash
python3 -m pytest container/tests/container/test_entrypoint.py \
  -k 'external or ssh_probe or remote or override' -q
```

Expected: FAIL because selector/migration functions, timeout options,
Makefile forwarding, and final-sink quote filters are not implemented.

**Acceptance:** Every new test fails for the missing behavior, not a fixture
or syntax error.

**Rollback:** Revert only the new test changes; production files are untouched.

### Phase 2 — Implement SSH-first selection and existing-remote enforcement

**Files:**
- Modify: `container/bind/layer_5_files/entrypoint.sh`
- Modify: `Makefile`
- Modify: `.chezmoiexternal.toml.tmpl`

**Interfaces:**
- Consumes: optional `PI_CONFIG_URL`, `PI_CONFIG_REF`, `NVIM_CONFIG_URL`,
  `NVIM_CONFIG_REF`.
- Produces: `select_external_url OVERRIDE SSH_URL HTTPS_URL`,
  `SELECTED_EXTERNAL_URL`, and
  `set_external_remote_url CHECKOUT SELECTED_URL`.

- [ ] **Step 1: Add constants and URL validation**

Replace unconditional bootstrap constants with paired transport constants:

```zsh
PI_CONFIG_SSH_URL="git@github.com:kkiyama117/pi-config.git"
PI_CONFIG_HTTPS_URL="https://github.com/kkiyama117/pi-config.git"
NVIM_CONFIG_SSH_URL="git@github.com:kkiyama117/nvim_config.git"
NVIM_CONFIG_HTTPS_URL="https://github.com/kkiyama117/nvim_config.git"
SELECTED_EXTERNAL_URL=""
```

Add non-secret override validation:

```zsh
validate_external_url() {
  local url="$1"
  case "$url" in
    http://*@*|https://*@*)
      echo "entrypoint: URL overrides must not contain HTTP(S) userinfo." >&2
      return 1
      ;;
  esac
}
```

- [ ] **Step 2: Add parent-shell URL selection**

Add:

```zsh
select_external_url() {
  local override="$1"
  local ssh_url="$2"
  local https_url="$3"

  if [[ -n "$override" ]]; then
    validate_external_url "$override"
    SELECTED_EXTERNAL_URL="$override"
    return 0
  fi

  if run_interruptible timeout --signal=TERM --kill-after=2s 10s \
      env GIT_TERMINAL_PROMPT=0 \
      GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=5 -o ConnectionAttempts=1" \
      git ls-remote "$ssh_url" HEAD >/dev/null 2>&1; then
    SELECTED_EXTERNAL_URL="$ssh_url"
  else
    echo "entrypoint: warning: SSH unavailable for a managed external; using HTTPS fallback." >&2
    SELECTED_EXTERNAL_URL="$https_url"
  fi
}
```

Call the function directly and copy the global result after each call:

```zsh
select_external_url "${PI_CONFIG_URL:-}" "$PI_CONFIG_SSH_URL" "$PI_CONFIG_HTTPS_URL"
selected_pi_config_url="$SELECTED_EXTERNAL_URL"
select_external_url "${NVIM_CONFIG_URL:-}" "$NVIM_CONFIG_SSH_URL" "$NVIM_CONFIG_HTTPS_URL"
selected_nvim_config_url="$SELECTED_EXTERNAL_URL"
```

- [ ] **Step 3: Render selected URLs and enforce existing remotes**

Render with:

```zsh
PI_CONFIG_URL="$selected_pi_config_url" \
NVIM_CONFIG_URL="$selected_nvim_config_url" \
chezmoi execute-template --init \
  < "$CONFIG_TEMPLATE" \
  > "$RUNTIME_CONFIG"
```

Add and invoke:

```zsh
set_external_remote_url() {
  local checkout="$1"
  local selected_url="$2"
  [[ -e "$checkout/.git" ]] || return 0

  if ! git -C "$checkout" remote get-url origin >/dev/null 2>&1; then
    echo "entrypoint: existing managed external has no origin remote." >&2
    return 1
  fi
  git -C "$checkout" remote set-url origin "$selected_url"
}

set_external_remote_url "$HOME/.pi" "$selected_pi_config_url"
set_external_remote_url "$HOME/.config/nvim" "$selected_nvim_config_url"
```

- [ ] **Step 4: Forward optional values through `make up`**

Add these Podman arguments before the volume arguments:

```make
		--env PI_CONFIG_URL \
		--env PI_CONFIG_REF \
		--env NVIM_CONFIG_URL \
		--env NVIM_CONFIG_REF \
```

- [ ] **Step 5: Quote values at the external TOML sink**

Use:

```toml
url = {{ .pi_config_url | quote }}
clone.args = ["--branch", {{ .pi_config_ref | quote }}, "--depth", "1", "--no-single-branch"]
```

For `nvim_config`, use:

```toml
url = {{ .nvim_config_url | quote }}
clone.args = ["--branch", {{ .nvim_config_ref | quote }}, "--depth", "1", "--no-single-branch"]
```

- [ ] **Step 6: Run focused tests and verify GREEN**

Run:

```bash
python3 -m pytest container/tests/container/test_entrypoint.py -q
zsh -n container/bind/layer_5_files/entrypoint.sh
```

Expected: all tests pass and zsh exits 0 with no output.

**Acceptance:** SSH success, per-repository fallback, override preservation,
timeouts, signal forwarding, remote migration, Makefile forwarding, and TOML
quoting all pass without network access.

**Rollback:** Restore the three production files. Before testing migration,
record each old remote with `git -C "$HOME/.pi" remote get-url origin` and
`git -C "$HOME/.config/nvim" remote get-url origin`; restore those recorded
values with `git -C "$HOME/.pi" remote set-url origin "$old_pi_url"` and
`git -C "$HOME/.config/nvim" remote set-url origin "$old_nvim_url"`.

### Phase 3 — Synchronize specifications and close with evidence

**Files:**
- Modify: `docs/specifications/11-pre-required-env-values.md`
- Modify: `docs/specifications/21-container-build-flow.md`
- Modify: `docs/issues/2026-07-16-ssh-first-external-fallback.md`
- Create: `docs/issues/2026-07-16-phase-ssh-first-external-fallback.md`
- Modify: this plan

**Interfaces:**
- Consumes: verified implementation and test output.
- Produces: normative SSH-first behavior and a result log.

- [ ] **Step 1: Update spec 11**

Replace unconditional bootstrap HTTPS text with the exact SSH-first,
independent fallback, override-forwarding, non-secret override, bounded probe,
and existing-remote migration behavior.

- [ ] **Step 2: Update spec 21**

Update Stage 5-4, lines 63–72, and acceptance criterion 19 to describe direct
`~/.pi` cloning, direct `~/.config/nvim` cloning, SSH defaults, independent
HTTPS fallback, and existing-remote enforcement.

- [ ] **Step 3: Run full relevant verification**

Run:

```bash
python3 -m pytest container/tests/container/ -q
zsh -n container/bind/layer_5_files/entrypoint.sh
git diff --check
```

Expected: all tests pass, zsh exits 0, and `git diff --check` emits no errors.

- [ ] **Step 4: Record result evidence and lifecycle status**

Create the result log with the commands, exit codes, and test count. Mark this
plan `executed`, the parent issue `closed`, and retain links to the design,
reviews, plan, and result log.

**Acceptance:** The implementation passes the complete container regression
module, shell syntax validation, and whitespace checks; the result log records
the observed output.

**Rollback:** Revert the implementation commit and mark the issue open again.
