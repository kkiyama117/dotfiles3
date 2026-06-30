"""Tests for the layer-4 paru install list in generate_deps."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import main  # noqa: E402


def test_paru_listed_in_list_managers() -> None:
    assert "paru" in main.LIST_MANAGERS


def test_expected_empty_files_includes_layer_4_paru() -> None:
    assert (4, "paru") in main.EXPECTED_EMPTY_FILES


def test_validate_accepts_paru_layer_4() -> None:
    main.validate(
        {
            "name": "paru",
            "manager": "paru",
            "layer": 4,
            "has_configs": False,
        }
    )


def test_write_txt_files_creates_layer_4_paru_txt(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(main, "DEPS_DIR", tmp_path)
    monkeypatch.setattr(main, "EXPECTED_EMPTY_FILES", ((4, "paru"),))
    by_layer = {
        4: [{"name": "paru", "manager": "paru", "layer": 4,
             "has_configs": False,
             "description": "AUR helper; bootstrapped via makepkg"}],
    }
    n = main.write_txt_files(by_layer)
    out = tmp_path / "layer_4" / "paru.txt"
    assert n == 1
    assert out.is_file()
    body = out.read_text()
    assert "manager: paru" in body
    assert "paru" in body


def test_write_txt_files_emits_empty_paru_txt_when_no_entries(
    tmp_path, monkeypatch
) -> None:
    """layer_4/paru.txt must exist even with zero paru entries so the
    Containerfile `COPY --from=deps layer_4/paru.txt` does not fail.
    Spec 02 §9 criterion #10: never hand-edited."""
    monkeypatch.setattr(main, "DEPS_DIR", tmp_path)
    by_layer = {1: [{"name": "git", "manager": "pacman", "layer": 1,
                     "has_configs": False}]}
    main.write_txt_files(by_layer)
    out = tmp_path / "layer_4" / "paru.txt"
    assert out.is_file()
    body = out.read_text()
    assert "manager: paru" in body
    assert "packages: 0" in body