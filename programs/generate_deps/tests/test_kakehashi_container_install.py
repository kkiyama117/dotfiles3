from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGES = REPO_ROOT / "dependencies" / "packages.toml"
MISE_CONFIG = REPO_ROOT / "dot_config" / "mise" / "config.toml"
SPEC20 = REPO_ROOT / "docs" / "specifications" / "20-container-rules.md"
SPEC21 = REPO_ROOT / "docs" / "specifications" / "21-container-build-flow.md"


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


def test_kakehashi_container_specs_are_synchronized() -> None:
    rules = SPEC20.read_text()
    flow = SPEC21.read_text()

    for invariant in range(1, 7):
        assert f"I-KAKEHASHI{invariant}" in rules
    assert "| `toolchain` (`FROM build-prepass`) | 3-8 |" in flow
    assert "26. After `make up`" in flow
    assert "$HOME/.local/bin/kakehashi" in flow
