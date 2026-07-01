"""Tests for the mise list manager in generate_deps.

`mise` is a list manager (like pacman/paru/cargo): entries declared in
`packages.toml` with `manager = "mise"` are rendered into
`dependencies/layer_<N>/mise.txt` as one `<name>@latest` line per tool.
Bare `mise install <tool>` reads a `mise.toml` (not latest), so the
generator appends `@latest`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import main  # noqa: E402


def test_mise_listed_in_list_managers() -> None:
    assert "mise" in main.LIST_MANAGERS


def test_mise_not_in_doc_only_managers() -> None:
    assert "mise" not in main.DOC_ONLY_MANAGERS


def test_expected_empty_files_includes_layer_3_mise() -> None:
    assert (3, "mise") in main.EXPECTED_EMPTY_FILES


def test_validate_accepts_mise_layer_3() -> None:
    main.validate(
        {
            "name": "go",
            "manager": "mise",
            "layer": 3,
            "has_configs": False,
        }
    )


def test_render_packages_txt_emits_at_latest_for_mise() -> None:
    tools = [
        {"name": "go", "manager": "mise", "layer": 3, "has_configs": False},
        {"name": "deno", "manager": "mise", "layer": 3, "has_configs": False,
         "description": "Deno runtime"},
    ]
    out = main.render_packages_txt(3, "mise", tools)
    assert "manager: mise" in out
    assert "go@latest" in out
    assert "deno@latest  # Deno runtime" in out


def test_render_packages_txt_bare_for_non_mise_managers() -> None:
    """pacman/paru/cargo keep bare names (no @latest suffix)."""
    tools = [{"name": "ripgrep", "manager": "cargo", "layer": 3,
              "has_configs": False}]
    out = main.render_packages_txt(3, "cargo", tools)
    assert "ripgrep" in out
    assert "ripgrep@latest" not in out


def test_write_txt_files_creates_layer_3_mise_txt(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(main, "DEPS_DIR", tmp_path)
    monkeypatch.setattr(main, "EXPECTED_EMPTY_FILES", ((3, "mise"),))
    by_layer = {
        3: [{"name": "go", "manager": "mise", "layer": 3,
             "has_configs": False, "description": "Go"}],
    }
    n = main.write_txt_files(by_layer)
    out = tmp_path / "layer_3" / "mise.txt"
    assert n == 1
    assert out.is_file()
    body = out.read_text()
    assert "manager: mise" in body
    assert "go@latest" in body


def test_write_txt_files_emits_empty_mise_txt_when_no_entries(
    tmp_path, monkeypatch
) -> None:
    """layer_3/mise.txt must exist even with zero mise entries so the
    Containerfile `COPY --from=deps layer_3/mise.txt` does not fail.
    Spec 02 §9 criterion #10: never hand-edited."""
    monkeypatch.setattr(main, "DEPS_DIR", tmp_path)
    monkeypatch.setattr(main, "EXPECTED_EMPTY_FILES", ((3, "mise"),))
    by_layer = {1: [{"name": "git", "manager": "pacman", "layer": 1,
                     "has_configs": False}]}
    main.write_txt_files(by_layer)
    out = tmp_path / "layer_3" / "mise.txt"
    assert out.is_file()
    body = out.read_text()
    assert "manager: mise" in body
    assert "packages: 0" in body


def test_mise_entry_rendered_in_doc_block() -> None:
    """mise entries appear in the spec 02 AUTO-GEN doc block under their
    layer, showing `name` (NOT `name@latest` — the version suffix is an
    install-detail, not an inventory fact)."""
    tools = [
        {"name": "go", "manager": "mise", "layer": 3,
         "has_configs": False, "description": "Go programming language"},
        {"name": "ripgrep", "manager": "cargo", "layer": 3,
         "has_configs": False},
    ]
    out = main.render_doc_block(tools)
    assert "Layer 3" in out
    assert "`go`" in out
    assert "go@latest" not in out
    assert "`ripgrep`" in out
    assert "mise" in out
    assert "cargo" in out
