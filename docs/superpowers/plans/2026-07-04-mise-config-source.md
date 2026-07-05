# Mise Config Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `dot_config/mise/config.toml` the only source of truth for mise-managed language installs in the container build.

**Architecture:** The Containerfile already renders the chezmoi source into `/tmp/build-home` during the build-prepass stage. Layer 3 should install mise tools by copying `/tmp/build-home/.config/mise/config.toml` into the build user's XDG config directory and running `mise install`, while the dependency generator stops treating `mise` as a package-list manager.

**Tech Stack:** Podman Containerfile, chezmoi-rendered dotfiles, mise, Python dependency generator, pytest, generated Markdown specifications.

## Global Constraints

- Do not manage mise language defaults in `dependencies/packages.toml`.
- Do not generate or copy `dependencies/layer_3/mise.txt`.
- Keep `deno = "latest"`, `go = "latest"`, and `python = "latest"` in `dot_config/mise/config.toml`.
- Rust stays outside mise because `dot_config/mise/config.toml` documents the rustup/XDG incompatibility.
- Source `/tmp/build-home/.zshenv` in each Layer 3 `RUN` that needs `MISE_DATA_DIR`, matching the existing Containerfile pattern.
- Run project commands from the repository root with `cd /data/dotfiles3 && ...`.

---

## File Structure

- `dot_config/mise/config.toml`: the sole hand-edited mise tool inventory for global defaults.
- `container/Containerfile`: consumes the rendered mise config in Layer 3 and runs `mise install`.
- `dependencies/packages.toml`: remains the hand-edited inventory for generated package-list and doc-only managers, excluding mise language defaults.
- `programs/generate_deps/main.py`: validates package-list managers and writes generated dependency lists, with no mise-specific behavior.
- `programs/generate_deps/tests/test_mise_manager.py`: becomes regression coverage proving `mise` is not accepted by the generator.
- `programs/generate_deps/tests/test_custom_manager.py`: updates stale prose that says mise is a list manager.
- `dependencies/layer_3/mise.txt`: removed from version control.
- `docs/specifications/02-installed-programs.md`: updates the source-of-truth contract and regenerated tool inventory.
- `docs/specifications/21-container-build-flow.md`: updates Layer 3 inputs and behavior from generated mise list to rendered mise config.

---

### Task 1: Make the Dependency Generator Reject Mise Entries

**Files:**
- Modify: `programs/generate_deps/main.py`
- Modify: `programs/generate_deps/tests/test_mise_manager.py`
- Modify: `programs/generate_deps/tests/test_custom_manager.py`

**Interfaces:**
- Consumes: `main.validate(t: dict) -> None`, `main.render_packages_txt(layer: int, manager: str, tools: list[dict]) -> str`, `main.write_txt_files(by_layer: dict[int, list[dict]]) -> int`
- Produces: `main.LIST_MANAGERS` without `mise`, `main.ALL_MANAGERS` without `mise`, and validation that exits on `manager = "mise"`

- [ ] **Step 1: Replace the mise generator tests with failing regression tests**

Replace the entire contents of `programs/generate_deps/tests/test_mise_manager.py` with:

```python
"""Tests that mise tools are configured outside generate_deps.

Mise language defaults live in dot_config/mise/config.toml. The dependency
generator must not accept manager = "mise" entries or emit layer_3/mise.txt.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import main  # noqa: E402


def test_mise_not_in_any_generator_manager_set() -> None:
    assert "mise" not in main.LIST_MANAGERS
    assert "mise" not in main.DOC_ONLY_MANAGERS
    assert "mise" not in main.ALL_MANAGERS


def test_expected_empty_files_excludes_layer_3_mise() -> None:
    assert (3, "mise") not in main.EXPECTED_EMPTY_FILES


def test_validate_rejects_mise_entries() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main.validate(
            {
                "name": "go",
                "manager": "mise",
                "layer": 3,
                "has_configs": False,
            }
        )

    assert excinfo.value.code == 1


def test_render_packages_txt_has_no_mise_latest_special_case() -> None:
    tools = [
        {
            "name": "cargo-edit",
            "manager": "cargo",
            "layer": 3,
            "has_configs": False,
            "description": "cargo subcommands",
        }
    ]

    out = main.render_packages_txt(3, "cargo", tools)

    assert "manager: cargo" in out
    assert "cargo-edit  # cargo subcommands" in out
    assert "@latest" not in out


def test_write_txt_files_does_not_emit_empty_mise_txt(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(main, "DEPS_DIR", tmp_path)
    monkeypatch.setattr(main, "EXPECTED_EMPTY_FILES", ((3, "cargo"),))
    by_layer = {
        1: [
            {
                "name": "git",
                "manager": "pacman",
                "layer": 1,
                "has_configs": False,
            }
        ]
    }

    main.write_txt_files(by_layer)

    assert not (tmp_path / "layer_3" / "mise.txt").exists()
```

- [ ] **Step 2: Run the mise generator tests and verify they fail**

Run:

```bash
cd /data/dotfiles3 && pytest programs/generate_deps/tests/test_mise_manager.py -v
```

Expected: FAIL. The first failures should show that `"mise"` is still present in `main.LIST_MANAGERS` and `(3, "mise")` is still present in `main.EXPECTED_EMPTY_FILES`.

- [ ] **Step 3: Remove mise-specific generation behavior**

In `programs/generate_deps/main.py`, make these exact edits:

```python
"""Regenerate per-layer install lists and the 02-installed-programs AUTO-GEN block.

Source of truth: ``dependencies/packages.toml`` (schema=1).

Outputs (all derived, do not hand-edit):
  - ``dependencies/layer_<N>/<manager>.txt``  — one install list per layer (N>=1)
    and per list-based manager (pacman / paru / nix / uv / cargo). Layer 0
    (already in the base image) and ``custom`` (bespoke install path) produce no
    txt.
  - The AUTO-GEN block in ``docs/specifications/02-installed-programs.md``
    (between the ``installed-programs`` markers), rendered as per-layer tables.

Invoke via ``make gen-deps`` from the repo root.
"""
```

```python
# Managers that install from a flat package list -> emit a .txt file.
LIST_MANAGERS = ("pacman", "paru", "nix", "uv", "cargo")
```

```python
# (layer, manager) pairs that always have a generated install list file,
# even when no entries exist. Required because the Containerfile COPYs
# `dependencies/layer_3/cargo.txt` and `dependencies/layer_4/paru.txt`
# unconditionally; a missing file breaks the build. Keeping these files
# generator-owned satisfies spec 02 §9 criterion #10 (never hand-edited).
EXPECTED_EMPTY_FILES: tuple[tuple[int, str], ...] = (
    (3, "cargo"),
    (4, "paru"),
)
```

```python
def render_packages_txt(layer: int, manager: str, tools: list[dict]) -> str:
    """One package name per line, sorted, with inline `# description` when set."""
    lines = [
        TXT_HEADER,
        f"# manager: {manager} | layer: {layer} | packages: {len(tools)}",
        "",
    ]
    for t in sorted(tools, key=lambda x: x["name"]):
        line = t["name"]
        desc = t.get("description")
        if desc:
            line = f"{line}  # {desc}"
        lines.append(line)
    lines.append("")
    return "\n".join(lines)
```

- [ ] **Step 4: Update the custom manager test prose**

In `programs/generate_deps/tests/test_custom_manager.py`, replace the module docstring with:

```python
"""Tests for the `custom` (doc-only) manager in generate_deps.

`custom` is for packages that are declared in `packages.toml` (so they
appear in the spec 02 AUTO-GEN doc block and satisfy invariant I5) but
are NOT installed from a generated `layer_<N>/<manager>.txt` list — they
have a bespoke install path in the Containerfile (e.g. `paru`, which is
bootstrapped via `makepkg` and therefore cannot also be a `paru -S`
target). `custom` is doc-only, no .txt emitted. Mise language defaults
live in dot_config/mise/config.toml, outside packages.toml.
"""
```

- [ ] **Step 5: Run focused generator tests and verify they pass**

Run:

```bash
cd /data/dotfiles3 && pytest programs/generate_deps/tests/test_mise_manager.py programs/generate_deps/tests/test_custom_manager.py -v
```

Expected: PASS for all tests in both files.

- [ ] **Step 6: Commit the generator change**

```bash
cd /data/dotfiles3 && git add programs/generate_deps/main.py programs/generate_deps/tests/test_mise_manager.py programs/generate_deps/tests/test_custom_manager.py && git commit -m "$(cat <<'EOF'
Stop generating mise package lists

EOF
)"
```

---

### Task 2: Move Mise Inventory Out of Packages TOML

**Files:**
- Modify: `dependencies/packages.toml`
- Modify: `dot_config/mise/config.toml`
- Delete: `dependencies/layer_3/mise.txt`

**Interfaces:**
- Consumes: `dot_config/mise/config.toml` `[tools]` entries
- Produces: package metadata with no `manager = "mise"` entries and no generated mise list file

- [ ] **Step 1: Write a failing validation check for packages.toml**

Run:

```bash
cd /data/dotfiles3 && python - <<'PY'
from pathlib import Path

text = Path("dependencies/packages.toml").read_text()
assert 'manager = "mise"' not in text
assert "dependencies/layer_3/mise.txt" not in text
PY
```

Expected: FAIL with `AssertionError` because `dependencies/packages.toml` still contains `manager = "mise"` and references `dependencies/layer_3/mise.txt`.

- [ ] **Step 2: Update packages.toml comments and remove mise tool entries**

In `dependencies/packages.toml`, replace the allowed manager comment near the top with:

```toml
## Allowed `manager` values: pacman, paru, nix, uv, cargo, custom.
## `cargo` entries land in layer 3 (Containerfile `toolchain` stage).
## Mise language defaults live in dot_config/mise/config.toml, not here.
```

Remove this entire block from `dependencies/packages.toml`:

```toml
# Layer 3: mise-managed languages (Containerfile `toolchain` stage, Layer 3-4).
# Add `[[tool]]` entries with `manager = "mise"` and `layer = 3`. The
# generator renders each line as `<name>@latest` (bare `mise install
# <tool>` reads a mise.toml, not latest). Run `make gen-deps` to
# regenerate `dependencies/layer_3/mise.txt`.
[[tool]]
name = "go"
manager = "mise"
layer = 3
has_configs = false
description = "Go programming language (mise-managed, latest)"

[[tool]]
name = "python"
manager = "mise"
layer = 3
has_configs = false
description = "CPython (mise-managed, latest)"

[[tool]]
name = "deno"
manager = "mise"
layer = 3
has_configs = false
description = "Deno runtime (mise-managed, latest)"
```

- [ ] **Step 3: Tighten the mise config comment**

In `dot_config/mise/config.toml`, replace the comment above `[tools]` entries with:

```toml
# Latest stable releases of deno, go, and python are global defaults so
# scratch shells have something usable without per-project setup.
```

Keep the tool values exactly:

```toml
deno = "latest"
go = "latest"
python = "latest"
```

- [ ] **Step 4: Delete the obsolete generated mise list**

Run:

```bash
cd /data/dotfiles3 && rm dependencies/layer_3/mise.txt
```

Expected: `dependencies/layer_3/mise.txt` no longer exists.

- [ ] **Step 5: Re-run the validation check and verify it passes**

Run:

```bash
cd /data/dotfiles3 && python - <<'PY'
from pathlib import Path

text = Path("dependencies/packages.toml").read_text()
assert 'manager = "mise"' not in text
assert "dependencies/layer_3/mise.txt" not in text
assert not Path("dependencies/layer_3/mise.txt").exists()
config = Path("dot_config/mise/config.toml").read_text()
for expected in ('deno = "latest"', 'go = "latest"', 'python = "latest"'):
    assert expected in config
PY
```

Expected: PASS with no output.

- [ ] **Step 6: Commit the source-of-truth move**

```bash
cd /data/dotfiles3 && git add dependencies/packages.toml dot_config/mise/config.toml dependencies/layer_3/mise.txt && git commit -m "$(cat <<'EOF'
Move mise language defaults to config.toml

EOF
)"
```

---

### Task 3: Install Mise Tools From Rendered Config in the Containerfile

**Files:**
- Modify: `container/Containerfile`

**Interfaces:**
- Consumes: `/tmp/build-home/.zshenv`, `/tmp/build-home/.config/mise/config.toml`, `$XDG_CONFIG_HOME`, `$MISE_DATA_DIR`
- Produces: Layer 3 mise install that reads `[tools]` from `${XDG_CONFIG_HOME}/mise/config.toml`

- [ ] **Step 1: Write a failing static check for the old install path**

Run:

```bash
cd /data/dotfiles3 && python - <<'PY'
from pathlib import Path

text = Path("container/Containerfile").read_text()
assert "layer_3/mise.txt" not in text
assert "/tmp/mise_tools.txt" not in text
assert "mise install --yes" in text
assert "/tmp/build-home/.config/mise/config.toml" in text
PY
```

Expected: FAIL with `AssertionError` because the Containerfile still copies `layer_3/mise.txt`.

- [ ] **Step 2: Replace the Layer 3 mise install block**

In `container/Containerfile`, replace the whole current block:

```dockerfile
# Layer 3-3: Install mise-managed languages
COPY --from=deps layer_3/mise.txt /tmp/mise_tools.txt
RUN --mount=type=cache,target=/home/${USERNAME}/.cache/mise,uid=${HOST_UID},gid=${HOST_GID} \
    zsh -c 'set -eo pipefail; \
      source /tmp/build-home/.zshenv; \
      pkgs=$(sed "s/#.*//" /tmp/mise_tools.txt | xargs); \
      if [ -n "$pkgs" ]; then \
        mise install ${=pkgs}; \
        mise use -g ${=pkgs}; \
      else \
        echo "toolchain: mise install list is empty -- skipping"; \
      fi; \
    '
```

with:

```dockerfile
# Layer 3-3: Install mise-managed languages from rendered chezmoi config
RUN --mount=type=cache,target=/home/${USERNAME}/.cache/mise,uid=${HOST_UID},gid=${HOST_GID} \
    zsh -c 'set -eo pipefail; \
      source /tmp/build-home/.zshenv; \
      mise_config=/tmp/build-home/.config/mise/config.toml; \
      if [ ! -s "$mise_config" ]; then \
        echo "toolchain: missing rendered mise config: $mise_config" >&2; \
        exit 1; \
      fi; \
      install -d "$XDG_CONFIG_HOME/mise"; \
      cp "$mise_config" "$XDG_CONFIG_HOME/mise/config.toml"; \
      mise install --yes; \
    '
```

- [ ] **Step 3: Update nearby Layer 3 comments**

In `container/Containerfile`, update the Stage 3 comment so the cache paragraph reads:

```dockerfile
# MISE_DATA_DIR. BuildKit cache mounts (uid/gid require Podman >= 4.0) keep
# the rustup download cache (3-2) and the mise download cache (3-3) across
# rebuilds without bloating image layers. cargo-binstall (3-4) has no
# persistent cache (per-run tempdir in $CARGO_HOME), and the cargo tools
# (3-5) resolve via the crates.io HTTP API, so neither carries a cache mount;
```

Update the cargo-binstall heading immediately after the mise block to:

```dockerfile
# Layer 3-4: Install cargo-binstall (prebuilt bootstrap — INFRA, not in packages.toml).
```

If subsequent comments already use this numbering, leave them unchanged. If they refer to mise as `3-4`, change those references to `3-3`.

- [ ] **Step 4: Re-run the static check and verify it passes**

Run:

```bash
cd /data/dotfiles3 && python - <<'PY'
from pathlib import Path

text = Path("container/Containerfile").read_text()
assert "layer_3/mise.txt" not in text
assert "/tmp/mise_tools.txt" not in text
assert "mise install --yes" in text
assert "/tmp/build-home/.config/mise/config.toml" in text
PY
```

Expected: PASS with no output.

- [ ] **Step 5: Commit the Containerfile install change**

```bash
cd /data/dotfiles3 && git add container/Containerfile && git commit -m "$(cat <<'EOF'
Install mise tools from rendered config

EOF
)"
```

---

### Task 4: Regenerate Dependency Artifacts and Update Specs

**Files:**
- Modify: `docs/specifications/02-installed-programs.md`
- Modify: `docs/specifications/21-container-build-flow.md`
- Modify: generated files under `dependencies/layer_*/*.txt` as produced by `make gen-deps`

**Interfaces:**
- Consumes: generator behavior from Task 1, package inventory from Task 2, Containerfile behavior from Task 3
- Produces: documentation that names `dot_config/mise/config.toml` as the mise source and no longer names `dependencies/layer_3/mise.txt`

- [ ] **Step 1: Write failing documentation checks**

Run:

```bash
cd /data/dotfiles3 && python - <<'PY'
from pathlib import Path

spec02 = Path("docs/specifications/02-installed-programs.md").read_text()
flow21 = Path("docs/specifications/21-container-build-flow.md").read_text()
assert "dot_config/mise/config.toml" in spec02
assert "dependencies/layer_3/mise.txt" not in spec02
assert "dot_config/mise/config.toml" in flow21
assert "dependencies/layer_3/mise.txt" not in flow21
PY
```

Expected: FAIL with `AssertionError` because both docs still refer to the generated mise list.

- [ ] **Step 2: Update the source-of-truth section in spec 02**

In `docs/specifications/02-installed-programs.md`, replace the generated artifacts bullet list in the "Source of truth" section with:

```markdown
- Hand-edited SoT for package-list and doc-only tool definitions: [`../../dependencies/packages.toml`](../../dependencies/packages.toml)
- Hand-edited SoT for mise language defaults: [`../../dot_config/mise/config.toml`](../../dot_config/mise/config.toml)
- Generated artifacts derived from `packages.toml`:
  - `../../dependencies/layer_<N>/<manager>.txt` — per-layer install lists for the Containerfile (layers >= 1; list managers `pacman`/`paru`/`nix`/`uv`/`cargo`)
  - The AUTO-GEN block at the end of this document
```

Replace the paragraph after that list with:

```markdown
`packages.toml` schema is documented at the top of that file. New package-list
entries belong there only — never edit the AUTO-GEN block by hand. New global
mise language defaults belong in `dot_config/mise/config.toml`, not in
`packages.toml`.
```

- [ ] **Step 3: Regenerate dependency artifacts**

Run:

```bash
cd /data/dotfiles3 && make gen-deps
```

Expected: command exits 0 and prints a `generate_deps:` summary. The generated AUTO-GEN block in `docs/specifications/02-installed-programs.md` no longer contains `go`, `python`, or `deno` rows with manager `mise`.

- [ ] **Step 4: Update spec 21 Layer 3 build flow**

In `docs/specifications/21-container-build-flow.md`, update the Layer 3 row that describes mise-managed languages so it names `dot_config/mise/config.toml` rendered into `/tmp/build-home/.config/mise/config.toml` as the input.

Use this wording for the row's purpose/input cells if the table is still in the current shape:

```markdown
Install mise-managed language defaults from the rendered mise config. | `/tmp/build-home/.zshenv`, `/tmp/build-home/.config/mise/config.toml`
```

In the acceptance criteria or notes, replace references to `dependencies/layer_3/mise.txt` with:

```markdown
Layer 3 installs mise-managed languages by copying `/tmp/build-home/.config/mise/config.toml` into the build user's `${XDG_CONFIG_HOME}/mise/config.toml` and running `mise install --yes`.
```

- [ ] **Step 5: Re-run documentation checks and verify they pass**

Run:

```bash
cd /data/dotfiles3 && python - <<'PY'
from pathlib import Path

spec02 = Path("docs/specifications/02-installed-programs.md").read_text()
flow21 = Path("docs/specifications/21-container-build-flow.md").read_text()
assert "dot_config/mise/config.toml" in spec02
assert "dependencies/layer_3/mise.txt" not in spec02
assert "dot_config/mise/config.toml" in flow21
assert "dependencies/layer_3/mise.txt" not in flow21
PY
```

Expected: PASS with no output.

- [ ] **Step 6: Commit generated docs and dependency artifacts**

```bash
cd /data/dotfiles3 && git add docs/specifications/02-installed-programs.md docs/specifications/21-container-build-flow.md dependencies && git commit -m "$(cat <<'EOF'
Document mise config as language source

EOF
)"
```

---

### Task 5: Final Verification

**Files:**
- Verify: `container/Containerfile`
- Verify: `dependencies/packages.toml`
- Verify: `dot_config/mise/config.toml`
- Verify: `programs/generate_deps/main.py`
- Verify: `programs/generate_deps/tests/test_mise_manager.py`
- Verify: `docs/specifications/02-installed-programs.md`
- Verify: `docs/specifications/21-container-build-flow.md`

**Interfaces:**
- Consumes: all prior tasks
- Produces: evidence that generator behavior, docs, and static Containerfile invariants are aligned

- [ ] **Step 1: Run the full generator test suite**

Run:

```bash
cd /data/dotfiles3 && pytest programs/generate_deps/tests -v
```

Expected: PASS for all tests under `programs/generate_deps/tests`.

- [ ] **Step 2: Run generator idempotence**

Run:

```bash
cd /data/dotfiles3 && make gen-deps && git diff --exit-code -- dependencies docs/specifications/02-installed-programs.md
```

Expected: PASS with exit code 0. If `make gen-deps` changes tracked files, inspect the diff, keep valid generated changes, and re-run this step until the second command exits 0.

- [ ] **Step 3: Run repository diff whitespace validation**

Run:

```bash
cd /data/dotfiles3 && git diff --check
```

Expected: PASS with no whitespace errors.

- [ ] **Step 4: Run final static invariant check**

Run:

```bash
cd /data/dotfiles3 && python - <<'PY'
from pathlib import Path

packages = Path("dependencies/packages.toml").read_text()
containerfile = Path("container/Containerfile").read_text()
spec02 = Path("docs/specifications/02-installed-programs.md").read_text()
flow21 = Path("docs/specifications/21-container-build-flow.md").read_text()
config = Path("dot_config/mise/config.toml").read_text()

assert 'manager = "mise"' not in packages
assert not Path("dependencies/layer_3/mise.txt").exists()
assert "layer_3/mise.txt" not in containerfile
assert "/tmp/mise_tools.txt" not in containerfile
assert "/tmp/build-home/.config/mise/config.toml" in containerfile
assert "mise install --yes" in containerfile
assert "dot_config/mise/config.toml" in spec02
assert "dependencies/layer_3/mise.txt" not in spec02
assert "dot_config/mise/config.toml" in flow21
assert "dependencies/layer_3/mise.txt" not in flow21
for expected in ('deno = "latest"', 'go = "latest"', 'python = "latest"'):
    assert expected in config
PY
```

Expected: PASS with no output.

- [ ] **Step 5: Run the container build verification**

Run:

```bash
cd /data/dotfiles3 && make build
```

Expected: PASS. Layer 3 should reach the mise install step without trying to copy `dependencies/layer_3/mise.txt`.

- [ ] **Step 6: Commit verification-only fixes if any were required**

If Task 5 required edits, commit only files from this plan:

```bash
cd /data/dotfiles3 && git add container/Containerfile dependencies/packages.toml dot_config/mise/config.toml programs/generate_deps/main.py programs/generate_deps/tests/test_mise_manager.py programs/generate_deps/tests/test_custom_manager.py docs/specifications/02-installed-programs.md docs/specifications/21-container-build-flow.md dependencies && git commit -m "$(cat <<'EOF'
Fix mise config source verification

EOF
)"
```

If Task 5 required no edits, do not create an empty commit.

---

## Self-Review

- Spec coverage: The plan covers the chosen config-only source, Containerfile Layer 3 install behavior, generator removal, package inventory cleanup, documentation updates, and verification.
- Placeholder scan: The plan contains concrete files, snippets, commands, and expected outcomes for each implementation task.
- Type and name consistency: The plan consistently uses `dot_config/mise/config.toml`, `/tmp/build-home/.config/mise/config.toml`, `${XDG_CONFIG_HOME}/mise/config.toml`, `LIST_MANAGERS`, `DOC_ONLY_MANAGERS`, `ALL_MANAGERS`, and `EXPECTED_EMPTY_FILES`.
