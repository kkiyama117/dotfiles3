# Kakehashi Container Install Implementation Plan

**Status:** executed
**Spec:** [../specifications/implementations/2026-07-16-kakehashi-container-install-design.md](../specifications/implementations/2026-07-16-kakehashi-container-install-design.md)
**Parent issue:** [../issues/2026-07-16-kakehashi-container-install.md](../issues/2026-07-16-kakehashi-container-install.md)
**Review trail:** [../reviews/2026-07-16-kakehashi-container-install-review-pass1.md](../reviews/2026-07-16-kakehashi-container-install-review-pass1.md)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install the latest stable x86_64 GNU/Linux `kakehashi` release at
`~/.local/bin/kakehashi` during the container build, with fail-closed release,
archive, ownership, and runtime checks.

**Architecture:** Declare `kakehashi` as a doc-only custom Layer 3 tool, then
install it in a new Containerfile Layer 3-8 before the `aur` stage. Resolve the
stable tag from GitHub's latest-release redirect, download from a hardcoded
repository URL, validate the one-member regular-file archive in private
staging, and verify the installed absolute path. Keep the entrypoint, Makefile,
PATH, secrets, and named volumes unchanged.

**Tech Stack:** Podman/Containerfile, zsh, curl, GNU tar, Python pytest,
`tomllib`, and the existing dependency generator.

## Global Constraints

- Support only `x86_64-unknown-linux-gnu`; do not add aarch64 selection.
- Resolve latest only when Layer 3-8 executes; preserve ordinary layer caching.
- Do not pin a version or SHA-256 under the approved policy.
- Use HTTPS-only origin and redirect protocols with TLS 1.2 minimum.
- Hardcode `https://github.com/atusy/kakehashi/releases/download/`; interpolate
  only a validated three-component stable tag such as `v0.8.0`.
- Run as `${USERNAME}` and install mode `0755` to
  `$HOME/.local/bin/kakehashi`.
- Reject extra archive members, alternate paths, symlinks, and non-regular
  members before installation.
- Use private temporary staging and remove it on success or failure.
- Do not modify `Makefile`, `dot_zshenv.tmpl`, mise config, entrypoint, volumes,
  secret-management files, or chezmoi templates.
- Commit steps below require explicit user authorization before execution.

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `programs/generate_deps/tests/test_kakehashi_container_install.py` | create | Enforce custom Layer 3 inventory and synchronized spec contracts |
| `dependencies/packages.toml` | modify | Declare the user-facing custom Layer 3 tool |
| `docs/specifications/02-installed-programs.md` | regenerate | Render the inventory declaration |
| `container/tests/container/test_entrypoint.py` | modify | Enforce the Layer 3-8 and entrypoint boundary |
| `container/Containerfile` | modify | Resolve, validate, and install `kakehashi` |
| `docs/specifications/20-container-rules.md` | modify | Add I-KAKEHASHI1 through I-KAKEHASHI6 |
| `docs/specifications/21-container-build-flow.md` | modify | Add Layer 3-8 and acceptance #26 |
| `docs/issues/2026-07-16-phase-kakehashi-container-install.md` | create | Record final acceptance evidence |
| `docs/issues/2026-07-16-kakehashi-container-install.md` | modify | Close the parent issue after verification |

---

### Task 1: Add the dependency inventory contract

**Files:**
- Create: `programs/generate_deps/tests/test_kakehashi_container_install.py`
- Modify: `dependencies/packages.toml`
- Regenerate: `docs/specifications/02-installed-programs.md`

**Interfaces:**
- Consumes: existing `custom` doc-only manager behavior.
- Produces: one `kakehashi` Layer 3 inventory row and no generated install list.

- [ ] **Step 1: Write the failing inventory tests**

Create `programs/generate_deps/tests/test_kakehashi_container_install.py`:

```python
from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGES = REPO_ROOT / "dependencies" / "packages.toml"
MISE_CONFIG = REPO_ROOT / "dot_config" / "mise" / "config.toml"


def test_kakehashi_is_custom_layer_3_inventory() -> None:
    tools = tomllib.loads(PACKAGES.read_text())["tool"]
    matches = [tool for tool in tools if tool["name"] == "kakehashi"]

    assert matches == [{
        "name": "kakehashi",
        "manager": "custom",
        "layer": 3,
        "has_configs": False,
        "description": (
            "language-server bridge; latest x86_64 GNU/Linux release binary "
            "installed to ~/.local/bin during the container build"
        ),
    }]


def test_kakehashi_is_not_mise_managed() -> None:
    assert "kakehashi" not in MISE_CONFIG.read_text()
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
python3 -m pytest -q \
  programs/generate_deps/tests/test_kakehashi_container_install.py
```

Expected: `test_kakehashi_is_custom_layer_3_inventory` fails because no
`kakehashi` inventory entry exists.

- [ ] **Step 3: Add the custom Layer 3 declaration**

Insert this block with the other custom Layer 3 tools in
`dependencies/packages.toml`:

```toml
[[tool]]
name = "kakehashi"
manager = "custom"
layer = 3
has_configs = false
description = "language-server bridge; latest x86_64 GNU/Linux release binary installed to ~/.local/bin during the container build"
```

- [ ] **Step 4: Regenerate and verify**

Run:

```bash
make gen-deps
make gen-deps
python3 -m pytest -q \
  programs/generate_deps/tests/test_kakehashi_container_install.py
make test-deps
git diff --check
```

Expected: both generator runs are idempotent; `kakehashi` appears in spec 02's
Layer 3 custom inventory; no `layer_3/custom.txt` is created; all dependency
tests and whitespace checks pass.

- [ ] **Step 5: Commit if explicitly authorized**

```bash
git add \
  programs/generate_deps/tests/test_kakehashi_container_install.py \
  dependencies/packages.toml \
  docs/specifications/02-installed-programs.md
git commit -m "feat(deps): declare kakehashi as a custom layer 3 tool"
```

---

### Task 2: Implement and statically enforce Layer 3-8

**Files:**
- Modify: `container/tests/container/test_entrypoint.py`
- Modify: `container/Containerfile`

**Interfaces:**
- Consumes: curl and GNU tar from Layer 1, inherited non-root `${USERNAME}`,
  `$HOME=/home/${USERNAME}`, and the upstream release naming convention.
- Produces: executable `$HOME/.local/bin/kakehashi` inherited by final runtime.

- [ ] **Step 1: Write the failing Containerfile contract test**

Append to `container/tests/container/test_entrypoint.py`:

```python
def test_kakehashi_inventory_and_container_install() -> None:
    packages = PACKAGES.read_text()
    containerfile = CONTAINERFILE.read_text()
    entrypoint = ENTRYPOINT.read_text()

    assert 'name = "kakehashi"' in packages
    assert 'manager = "custom"' in packages
    assert 'layer = 3' in packages

    start = containerfile.index("# Layer 3-8: Install kakehashi")
    end = containerfile.index("# Stage 4: aur", start)
    block = containerfile[start:end]

    assert containerfile.index("# Layer 3-7:") < start < end
    assert "releases/latest" in block
    assert '%{url_effective}' in block
    assert "v<->.<->.<->" in block
    assert "--proto-redir \"=https\"" in block
    assert "https://github.com/atusy/kakehashi/releases/download/" in block
    assert "x86_64-unknown-linux-gnu.tar.gz" in block
    assert "mktemp -d" in block
    assert "trap " in block
    assert "tar -tzf" in block
    assert "tar -tvzf" in block
    assert "--no-same-owner --no-same-permissions" in block
    assert '! -L "$staging/kakehashi"' in block
    assert 'install -D -m 0755' in block
    assert '"$HOME/.local/bin/kakehashi" --version' in block
    assert "kakehashi" not in entrypoint
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
python3 -m pytest -q \
  container/tests/container/test_entrypoint.py \
  -k kakehashi_inventory_and_container_install
```

Expected: failure because `# Layer 3-8: Install kakehashi` is absent.

- [ ] **Step 3: Add Layer 3-8**

Insert this block after Layer 3-7 and before the Stage 4 comment in
`container/Containerfile`:

```dockerfile
# Layer 3-8: Install kakehashi (latest x86_64 GNU/Linux release binary).
#
# kakehashi is a user-facing custom Layer 3 tool declared in packages.toml.
# Resolve the stable tag only when this layer executes; normal layer caching
# intentionally retains the previously resolved release. The GitHub asset base
# is hardcoded, and private staging is removed on every shell exit.
RUN zsh -c 'set -eo pipefail; \
      staging=$(mktemp -d); \
      trap "rm -rf -- ${(q)staging}" EXIT INT TERM; \
      latest_url=$(curl -L --proto "=https" --proto-redir "=https" --tlsv1.2 -sSf \
        -o /dev/null -w "%{url_effective}" \
        https://github.com/atusy/kakehashi/releases/latest); \
      tag=${latest_url##*/}; \
      [[ "$tag" == v<->.<->.<-> ]] || { \
        print -u2 "kakehashi: unexpected latest release tag: $tag"; \
        exit 1; \
      }; \
      asset="kakehashi-${tag}-x86_64-unknown-linux-gnu.tar.gz"; \
      archive="$staging/$asset"; \
      curl -L --proto "=https" --proto-redir "=https" --tlsv1.2 -sSf \
        -o "$archive" \
        "https://github.com/atusy/kakehashi/releases/download/${tag}/${asset}"; \
      members=("${(@f)$(tar -tzf "$archive")}"); \
      (( ${#members} == 1 )) && [[ "${members[1]}" == "kakehashi" ]] || { \
        print -u2 "kakehashi: unexpected archive members"; \
        exit 1; \
      }; \
      listing=$(tar -tvzf "$archive"); \
      [[ "${listing[1]}" == "-" ]] || { \
        print -u2 "kakehashi: archive member is not a regular file"; \
        exit 1; \
      }; \
      tar --no-same-owner --no-same-permissions -xzf "$archive" -C "$staging"; \
      [[ -f "$staging/kakehashi" && ! -L "$staging/kakehashi" ]] || { \
        print -u2 "kakehashi: extracted member is not a regular file"; \
        exit 1; \
      }; \
      install -D -m 0755 "$staging/kakehashi" "$HOME/.local/bin/kakehashi"; \
      "$HOME/.local/bin/kakehashi" --version; \
    '
```

- [ ] **Step 4: Run static verification**

Run:

```bash
python3 -m pytest -q \
  container/tests/container/test_entrypoint.py \
  -k kakehashi_inventory_and_container_install
make test-container
git diff --check
```

Expected: focused test and full container static suite pass.

- [ ] **Step 5: Commit if explicitly authorized**

```bash
git add container/tests/container/test_entrypoint.py container/Containerfile
git commit -m "feat(container): install latest kakehashi in layer 3-8"
```

---

### Task 3: Synchronize container specifications

**Files:**
- Modify: `programs/generate_deps/tests/test_kakehashi_container_install.py`
- Modify: `docs/specifications/20-container-rules.md`
- Modify: `docs/specifications/21-container-build-flow.md`

**Interfaces:**
- Consumes: the Layer 3-8 contract from Task 2.
- Produces: normative lifecycle, security, refresh, and acceptance text.

- [ ] **Step 1: Add failing specification assertions**

Add these constants and test to
`programs/generate_deps/tests/test_kakehashi_container_install.py`:

```python
SPEC20 = REPO_ROOT / "docs" / "specifications" / "20-container-rules.md"
SPEC21 = REPO_ROOT / "docs" / "specifications" / "21-container-build-flow.md"


def test_kakehashi_container_specs_are_synchronized() -> None:
    rules = SPEC20.read_text()
    flow = SPEC21.read_text()

    for invariant in range(1, 7):
        assert f"I-KAKEHASHI{invariant}" in rules
    assert "| `toolchain` (`FROM build-prepass`) | 3-8 |" in flow
    assert "26. After `make up`" in flow
    assert "$HOME/.local/bin/kakehashi" in flow
```

- [ ] **Step 2: Run the focused test and verify it fails**

```bash
python3 -m pytest -q \
  programs/generate_deps/tests/test_kakehashi_container_install.py \
  -k container_specs_are_synchronized
```

Expected: failure because I-KAKEHASHI1 through I-KAKEHASHI6 and Layer 3-8 are
not yet in the normative specs.

- [ ] **Step 3: Add spec 20 invariants**

After I-HERDR3 in `docs/specifications/20-container-rules.md`, add:

```markdown
- I-KAKEHASHI1: **`kakehashi` is installed only at image build time.**
  It is a user-facing `manager = "custom"`, `layer = 3` tool whose sole
  install authority is Containerfile Layer 3-8. The entrypoint and runtime
  `chezmoi apply` never install or update it.
- I-KAKEHASHI2: **The binary path is `$HOME/.local/bin/kakehashi`.**
  Layer 3-8 runs as `${USERNAME}`, installs mode `0755`, and creates the
  parent directory with `install -D`. `dot_zshenv.tmpl` already adds this
  directory to PATH; no named volume overlays it.
- I-KAKEHASHI3: **Latest means latest when Layer 3-8 executes.** Normal
  container caching may retain an older release. Immediate refresh requires
  the documented full `podman build --no-cache` command; there is no
  entrypoint update and no automatic cache-bust argument.
- I-KAKEHASHI4: **The release contract is x86_64 GNU/Linux and one regular
  file.** The archive must contain exactly one member named `kakehashi`; its
  tar type and extracted form must both be regular and non-symlink before
  installation.
- I-KAKEHASHI5: **The moving release trusts GitHub/upstream control.** Both
  requests require HTTPS and HTTPS-only redirects with TLS 1.2 minimum. The
  asset repository prefix is hardcoded and only a validated stable tag is
  interpolated. No repository-pinned digest exists, so shape and version
  checks are not a cryptographic identity guarantee.
- I-KAKEHASHI6: **No runtime state or secret is baked.** The build invokes
  only the installed binary's `--version`; it starts no bridge service,
  creates no configuration, and reads no secret.
```

- [ ] **Step 4: Add the spec 21 Layer 3-8 row**

Insert after the Layer 3-7 row:

```markdown
| `toolchain` (`FROM build-prepass`) | 3-8 | Resolve GitHub's stable latest tag; download the hardcoded `atusy/kakehashi` x86_64 GNU/Linux asset over HTTPS; validate one regular `kakehashi` member; install to `$HOME/.local/bin/kakehashi`; run `--version` | Install the custom Layer 3 `kakehashi` binary at build time. Normal layer caching is intentional; no runtime update path or named volume is added (I-KAKEHASHI1–I-KAKEHASHI6). | GitHub releases, `dependencies/packages.toml` |
```

- [ ] **Step 5: Add spec 21 acceptance criterion #26**

Append after criterion #25:

```markdown
26. After `make up`, `podman exec dotfiles-manjaro zsh -ic 'command -v
    kakehashi; kakehashi --version'` exits 0 and resolves
    `/home/${USERNAME}/.local/bin/kakehashi`; `podman exec
    dotfiles-manjaro stat -c '%a %U:%G' /home/${USERNAME}/.local/bin/kakehashi`
    reports `755 ${USERNAME}:${USERNAME}` (or the configured primary group).
    The entrypoint contains no `kakehashi` install/update path. **Refresh:**
    ordinary `make build` may reuse Layer 3-8; use the design's full
    `podman build --no-cache` command to re-resolve latest.
```

- [ ] **Step 6: Run synchronized verification**

```bash
python3 -m pytest -q \
  programs/generate_deps/tests/test_kakehashi_container_install.py
make test-deps
make test-container
git diff --check
```

Expected: all focused and full static suites pass.

- [ ] **Step 7: Commit if explicitly authorized**

```bash
git add \
  programs/generate_deps/tests/test_kakehashi_container_install.py \
  docs/specifications/20-container-rules.md \
  docs/specifications/21-container-build-flow.md
git commit -m "docs(container): specify kakehashi layer 3-8 contract"
```

---

### Task 4: Build, runtime verification, and result log

**Files:**
- Create: `docs/issues/2026-07-16-phase-kakehashi-container-install.md`
- Modify: `docs/issues/2026-07-16-kakehashi-container-install.md`

**Interfaces:**
- Consumes: Tasks 1–3 and configured `.env`.
- Produces: acceptance evidence and a closed parent issue.

- [ ] **Step 1: Run all offline checks**

```bash
make gen-deps
make test-deps
make test-container
make test-zsh
git diff --check
```

Expected: every command exits 0 and a second `make gen-deps` creates no diff.

- [ ] **Step 2: Build and start the container**

```bash
make build
make up
```

Expected: Layer 3-8 prints a line such as `kakehashi 0.8.0`; all image stages
complete; `make up` reaches the chezmoi readiness sentinel.

- [ ] **Step 3: Verify runtime path, version, ownership, and entrypoint boundary**

```bash
podman exec dotfiles-manjaro zsh -ic \
  'command -v kakehashi; kakehashi --version'
podman exec dotfiles-manjaro zsh -ic \
  'stat -c "%a %U:%G" "$HOME/.local/bin/kakehashi"'
! rg -n 'kakehashi' container/bind/layer_5_files/entrypoint.sh
```

Expected: command path is `$HOME/.local/bin/kakehashi` for the configured
container user; version exits 0; stat reports mode `755` and that user/group;
rg finds no entrypoint match.

- [ ] **Step 4: Write the result log**

Create `docs/issues/2026-07-16-phase-kakehashi-container-install.md`:

```markdown
# Kakehashi container install result

**Date:** 2026-07-16
**Status:** executed
**Plan:** [../plans/2026-07-16-kakehashi-container-install-impl.md](../plans/2026-07-16-kakehashi-container-install-impl.md)

## Acceptance evidence

| Criterion | Status | Evidence |
|---|---|---|
| Custom Layer 3 inventory | PASS | `make gen-deps` and focused inventory test |
| Static contracts | PASS | `make test-deps`, `make test-container`, `make test-zsh` |
| Image build | PASS | Exact successful `make build` summary and Layer 3-8 version line captured in Steps 2–3 |
| Runtime path/version | PASS | Exact `command -v kakehashi` and `kakehashi --version` output captured in Step 3 |
| Mode and ownership | PASS | Exact `stat -c '%a %U:%G'` output captured in Step 3 |
| Entrypoint boundary | PASS | no `kakehashi` match in entrypoint |
| Specs synchronized | PASS | I-KAKEHASHI1–6, Layer 3-8, acceptance #26 |

## Command outputs

Use the exact version, path, stat, test-summary, and build-result lines captured
by Steps 1–3 as the Evidence cells; do not write `PASS` for a command that did
not exit zero.
```

Write the file only after Steps 1–3 succeed so every `PASS` row has concrete
command output.

- [ ] **Step 5: Close the issue and mark the plan executed**

In `docs/issues/2026-07-16-kakehashi-container-install.md`, change status to:

```markdown
**Status:** closed (see [result-log](2026-07-16-phase-kakehashi-container-install.md))
```

In this plan, change `**Status:** pending` to `**Status:** executed`.

- [ ] **Step 6: Commit if explicitly authorized**

```bash
git add \
  docs/issues/2026-07-16-phase-kakehashi-container-install.md \
  docs/issues/2026-07-16-kakehashi-container-install.md \
  docs/plans/2026-07-16-kakehashi-container-install-impl.md
git commit -m "docs: close kakehashi container install with evidence"
```

---

## Self-Review

- Spec coverage: Tasks 1–4 cover S1–S7, I-KAKEHASHI1–6, Layer 3-8,
  acceptance #26, rollback-relevant files, and result evidence.
- Placeholder scan: every code block, command, path, and interface is concrete.
- Name consistency: `kakehashi`, `x86_64-unknown-linux-gnu`, Layer 3-8,
  I-KAKEHASHI1–6, and `$HOME/.local/bin/kakehashi` are consistent.
- Scope: no Makefile, PATH, mise, entrypoint, volume, secret, or chezmoi
  behavior change is planned.
- Security: hardcoded download base, zsh-safe tag validation, regular-file tar
  checks, private staging, and failure cleanup are all explicit.

## Execution Handoff

Plan complete at
`docs/plans/2026-07-16-kakehashi-container-install-impl.md`.

1. **Subagent-Driven (recommended):** dispatch a fresh worker for each task
   with review between tasks.
2. **Inline Execution:** execute tasks in this session in batches with
   checkpoints.
