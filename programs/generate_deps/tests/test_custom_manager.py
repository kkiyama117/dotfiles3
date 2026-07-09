"""Tests for the `custom` (doc-only) manager in generate_deps.

`custom` is for packages that are declared in `packages.toml` (so they
appear in the spec 02 AUTO-GEN doc block and satisfy invariant I5) but
are NOT installed from a generated `layer_<N>/<manager>.txt` list — they
have a bespoke install path in the Containerfile (e.g. `paru`, which is
bootstrapped via `makepkg` and therefore cannot also be a `paru -S`
target). `custom` is doc-only, no .txt emitted. Mise-managed tool versions
live in dot_config/mise/config.toml, outside packages.toml.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import main  # noqa: E402


def test_custom_in_all_managers() -> None:
    assert "custom" in main.ALL_MANAGERS


def test_custom_is_doc_only_not_list() -> None:
    assert "custom" in main.DOC_ONLY_MANAGERS
    assert "custom" not in main.LIST_MANAGERS


def test_validate_accepts_custom() -> None:
    main.validate(
        {
            "name": "paru",
            "manager": "custom",
            "layer": 4,
            "has_configs": False,
        }
    )


def test_custom_entry_produces_no_txt(tmp_path, monkeypatch) -> None:
    """A `custom` entry must NOT produce a `layer_<N>/<manager>.txt`
    install list. Isolate EXPECTED_EMPTY_FILES so the count is
    deterministic and prove no file is written for the custom entry."""
    monkeypatch.setattr(main, "DEPS_DIR", tmp_path)
    monkeypatch.setattr(main, "EXPECTED_EMPTY_FILES", ())
    by_layer = {
        4: [{"name": "paru", "manager": "custom", "layer": 4,
             "has_configs": False}],
    }
    n = main.write_txt_files(by_layer)
    assert n == 0
    # No layer_4 directory is materialised for a custom-only layer.
    assert not (tmp_path / "layer_4").exists()


def test_custom_entry_rendered_in_doc_block() -> None:
    """`custom` entries MUST appear in the AUTO-GEN doc block (the whole
    point of declaring them in packages.toml)."""
    tools = [
        {"name": "paru", "manager": "custom", "layer": 4,
         "has_configs": False, "description": "AUR helper; bootstrapped via makepkg"},
        {"name": "neovim-git", "manager": "paru", "layer": 4,
         "has_configs": False, "description": "neovim -git build"},
    ]
    out = main.render_doc_block(tools)
    assert "Layer 4" in out
    assert "`paru`" in out
    assert "custom" in out
    assert "`neovim-git`" in out
    assert "paru" in out  # manager column for neovim-git