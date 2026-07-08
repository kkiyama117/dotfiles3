"""Tests that mise tools are configured outside generate_deps.

Mise-managed tool versions live in dot_config/mise/config.toml. The dependency
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
