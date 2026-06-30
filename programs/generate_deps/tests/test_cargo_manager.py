"""Tests for the cargo-manager extension in generate_deps."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import main  # noqa: E402


def test_cargo_listed_in_list_managers() -> None:
    assert "cargo" in main.LIST_MANAGERS


def test_validate_accepts_cargo_manager() -> None:
    main.validate(
        {
            "name": "ripgrep",
            "manager": "cargo",
            "layer": 3,
            "has_configs": False,
        }
    )


def test_render_packages_txt_emits_cargo_entries() -> None:
    tools = [
        {"name": "ripgrep", "manager": "cargo", "layer": 3, "has_configs": False},
        {"name": "eza", "manager": "cargo", "layer": 3, "has_configs": False,
         "description": "modern ls"},
    ]
    out = main.render_packages_txt(3, "cargo", tools)
    assert "manager: cargo" in out
    assert "ripgrep" in out
    assert "eza  # modern ls" in out


def test_write_txt_files_creates_layer_3_cargo_txt(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(main, "DEPS_DIR", tmp_path)
    by_layer = {
        3: [{"name": "ripgrep", "manager": "cargo", "layer": 3,
             "has_configs": False}],
    }
    n = main.write_txt_files(by_layer)
    out = tmp_path / "layer_3" / "cargo.txt"
    assert n == 1
    assert out.is_file()
    assert "ripgrep" in out.read_text()


def test_write_txt_files_emits_empty_cargo_txt_when_no_entries(tmp_path, monkeypatch) -> None:
    """layer_3/cargo.txt must exist even with zero entries so the
    Containerfile `COPY --from=deps layer_3/cargo.txt` does not fail.
    Spec §9 criterion #10: never hand-edited."""
    monkeypatch.setattr(main, "DEPS_DIR", tmp_path)
    by_layer = {1: [{"name": "git", "manager": "pacman", "layer": 1,
                     "has_configs": False}]}
    n = main.write_txt_files(by_layer)
    out = tmp_path / "layer_3" / "cargo.txt"
    assert out.is_file()
    body = out.read_text()
    assert "manager: cargo" in body
    assert "packages: 0" in body
