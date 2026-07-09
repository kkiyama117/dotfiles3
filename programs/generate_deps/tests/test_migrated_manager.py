"""Tests for the `migrated` (doc-only) manager in generate_deps.

`migrated` is for tools whose chezmoi config was carried over from an
older dotfiles setup but are NOT installed in the container. Declared in
`packages.toml` (so they appear in the spec 02 AUTO-GEN doc block) with
`layer = -1`; no `layer_<N>/<manager>.txt` is emitted and the
Containerfile is not updated.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import main  # noqa: E402


def test_migrated_in_all_managers() -> None:
    assert "migrated" in main.ALL_MANAGERS


def test_migrated_is_doc_only_not_list() -> None:
    assert "migrated" in main.DOC_ONLY_MANAGERS
    assert "migrated" not in main.LIST_MANAGERS


def test_validate_accepts_migrated() -> None:
    main.validate(
        {
            "name": "kitty",
            "manager": "migrated",
            "layer": -1,
            "has_configs": True,
            "description": "terminal emulator; host-only, config retained",
        }
    )


def test_validate_rejects_migrated_with_wrong_layer() -> None:
    with pytest.raises(SystemExit):
        main.validate(
            {
                "name": "kitty",
                "manager": "migrated",
                "layer": 7,
                "has_configs": True,
            }
        )


def test_validate_rejects_non_migrated_with_layer_minus_one() -> None:
    with pytest.raises(SystemExit):
        main.validate(
            {
                "name": "kitty",
                "manager": "pacman",
                "layer": -1,
                "has_configs": True,
            }
        )


def test_migrated_entry_produces_no_txt(tmp_path, monkeypatch) -> None:
    """A `migrated` entry must NOT produce a `layer_<N>/<manager>.txt`
    install list."""
    monkeypatch.setattr(main, "DEPS_DIR", tmp_path)
    monkeypatch.setattr(main, "EXPECTED_EMPTY_FILES", ())
    by_layer = {
        -1: [
            {
                "name": "kitty",
                "manager": "migrated",
                "layer": -1,
                "has_configs": True,
            }
        ],
    }
    n = main.write_txt_files(by_layer)
    assert n == 0
    assert not (tmp_path / "layer_-1").exists()


def test_migrated_entry_rendered_in_doc_block() -> None:
    tools = [
        {
            "name": "kitty",
            "manager": "migrated",
            "layer": -1,
            "has_configs": True,
            "description": "terminal emulator; host-only, config retained",
        },
    ]
    out = main.render_doc_block(tools)
    assert "Layer -1 — migrated" in out
    assert "`kitty`" in out
    assert "migrated" in out
