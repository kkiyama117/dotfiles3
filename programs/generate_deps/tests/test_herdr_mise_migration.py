from __future__ import annotations

from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]


def test_herdr_not_in_packages_toml() -> None:
    """After migration herdr is managed by mise, not packages.toml."""
    repo_root = SCRIPT_DIR.parents[1]
    packages_path = repo_root / "dependencies" / "packages.toml"
    raw = packages_path.read_text()
    assert 'name = "herdr"' not in raw, "herdr must not be declared in dependencies/packages.toml"


def test_herdr_in_mise_config() -> None:
    """herdr is declared with the explicit aqua backend because disable_default_registry=true."""
    repo_root = SCRIPT_DIR.parents[1]
    mise_config_path = repo_root / "dot_config" / "mise" / "config.toml"
    raw = mise_config_path.read_text()
    assert '"aqua:ogulcancelik/herdr" = "latest"' in raw


def test_containerfile_has_no_bespoke_herdr_install() -> None:
    """herdr is installed via mise (Layer 3-4), not a bespoke Containerfile block."""
    repo_root = SCRIPT_DIR.parents[1]
    containerfile = repo_root / "container" / "Containerfile"
    raw = containerfile.read_text()
    forbidden = (
        "HERDR_VERSION",
        "HERDR_SHA256",
        "herdr-linux-x86_64",
        "# Layer 3-8: Install herdr",
    )
    for marker in forbidden:
        assert marker not in raw, (
            f"Containerfile must not contain bespoke herdr install marker: {marker!r}"
        )


def test_herdr_update_checks_disabled() -> None:
    """Both herdr config variants set stable channel and disabled checks."""
    repo_root = SCRIPT_DIR.parents[1]
    for name in ("config.toml", "config.yml"):
        cfg_path = repo_root / "dot_config" / "herdr" / name
        raw = cfg_path.read_text()
        assert 'channel = "stable"' in raw
        assert 'version_check = false' in raw
        assert 'manifest_check = false' in raw
