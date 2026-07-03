"""Tests for the layer-6 runtime-manual reference list in generate_deps.

`layer = 6` is a runtime-manual layer: entries are declared in
`packages.toml` for SoT but NOT build-installed (the Containerfile only
reads `layer_3`). The generator emits `layer_6/<manager>.txt` as a
reference list (no functional emission change — the `write_txt_files`
loop already handles any `layer >= 1`), and the spec-02 AUTO-GEN doc
block renders a distinct heading for layer 6.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import main  # noqa: E402


def test_render_doc_block_layer6_heading() -> None:
    tools = [{"name": "maturin", "manager": "cargo", "layer": 6,
              "has_configs": False, "description": "runtime-manual"}]
    block = main.render_doc_block(tools)
    assert "#### Layer 6 — runtime-manual (not build-installed)" in block
    assert "maturin" in block


def test_render_doc_block_layer0_heading_unchanged() -> None:
    tools = [{"name": "pacman", "manager": "pacman", "layer": 0,
              "has_configs": True}]
    block = main.render_doc_block(tools)
    assert "#### Layer 0 — already in the base image" in block


def test_write_txt_files_emits_layer_6_cargo_txt(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(main, "DEPS_DIR", tmp_path)
    monkeypatch.setattr(main, "EXPECTED_EMPTY_FILES", ())
    by_layer = {
        6: [{"name": "maturin", "manager": "cargo", "layer": 6,
             "has_configs": False}],
    }
    n = main.write_txt_files(by_layer)
    out = tmp_path / "layer_6" / "cargo.txt"
    assert n == 1
    assert out.is_file()
    assert "maturin" in out.read_text()


def test_layer6_entries_do_not_leak_into_layer3(tmp_path, monkeypatch) -> None:
    """A layer=6 cargo entry must NOT appear in layer_3/cargo.txt."""
    monkeypatch.setattr(main, "DEPS_DIR", tmp_path)
    monkeypatch.setattr(main, "EXPECTED_EMPTY_FILES", ((3, "cargo"),))
    by_layer = {
        3: [{"name": "topgrade", "manager": "cargo", "layer": 3,
             "has_configs": False}],
        6: [{"name": "maturin", "manager": "cargo", "layer": 6,
             "has_configs": False}],
    }
    main.write_txt_files(by_layer)
    l3 = (tmp_path / "layer_3" / "cargo.txt").read_text()
    l6 = (tmp_path / "layer_6" / "cargo.txt").read_text()
    assert "topgrade" in l3 and "maturin" not in l3
    assert "maturin" in l6 and "topgrade" not in l6
