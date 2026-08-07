"""kakehashi global config ↔ install-inventory sync tests.

The global kakehashi config (dot_config/kakehashi/kakehashi.toml) declares
`languageServers` whose binaries must resolve on PATH. The authoritative
server → provider mapping:

- mise-managed: the provider tool key exists in dot_config/mise/config.toml
  [tools] (the server's cmd[0] is the binary the tool installs).
- system-managed: the provider package exists in dependencies/packages.toml
  (paru/pacman) — rust_analyzer (rust-analyzer) and clangd (clang).

This is a coverage contract, NOT set equality: denols is provided by the
`deno` runtime entry, stylua is a formatter (not a languageServer), and the
nvim `bridged_servers` list is deliberately a subset (no clangd).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
KAKEHASHI_CONFIG = REPO_ROOT / "dot_config" / "kakehashi" / "kakehashi.toml"
MISE_CONFIG = REPO_ROOT / "dot_config" / "mise" / "config.toml"
PACKAGES = REPO_ROOT / "dependencies" / "packages.toml"

# server key -> (provider, provider name in the install inventory)
# `mise` providers are tool keys under [tools]; `system` providers are
# package names in packages.toml.
SERVER_PROVIDERS: dict[str, tuple[str, str]] = {
    "denols": ("mise", "deno"),
    "emmylua_ls": ("mise", "cargo:emmylua_ls"),
    "gopls": ("mise", "go:golang.org/x/tools/gopls"),
    "pyright": ("mise", "npm:pyright"),
    "rust_analyzer": ("system", "rust-analyzer"),
    "tombi": ("mise", "aqua:tombi-toml/tombi"),
    "vtsls": ("mise", "npm:@vtsls/language-server"),
    "clangd": ("system", "clang"),
}


def _kakehashi_servers() -> set[str]:
    data = tomllib.loads(KAKEHASHI_CONFIG.read_text())
    return set(data["languageServers"])


def _mise_tools() -> set[str]:
    data = tomllib.loads(MISE_CONFIG.read_text())
    return set(data["tools"])


def _package_names() -> set[str]:
    data = tomllib.loads(PACKAGES.read_text())
    return {tool["name"] for tool in data["tool"]}


def test_kakehashi_language_servers_match_inventory() -> None:
    servers = _kakehashi_servers()
    assert servers == set(SERVER_PROVIDERS)

    mise_tools = _mise_tools()
    packages = _package_names()

    for server, (provider, provider_name) in SERVER_PROVIDERS.items():
        if provider == "mise":
            assert provider_name in mise_tools, (
                f"server {server}: mise tool {provider_name!r} missing from "
                "dot_config/mise/config.toml"
            )
        else:
            assert provider_name in packages, (
                f"server {server}: package {provider_name!r} missing from "
                "dependencies/packages.toml"
            )


def test_kakehashi_servers_use_bare_commands() -> None:
    data = tomllib.loads(KAKEHASHI_CONFIG.read_text())
    for name, server in data["languageServers"].items():
        cmd = server["cmd"]
        assert isinstance(cmd, list) and cmd, f"server {name}: empty cmd"
        cmd0 = cmd[0]
        assert isinstance(cmd0, str) and "/" not in cmd0, (
            f"server {name}: cmd[0] must be a bare PATH name, got {cmd0!r}"
        )


def test_mise_config_comment_names_all_sync_targets() -> None:
    text = MISE_CONFIG.read_text()
    assert "dot_config/kakehashi/kakehashi.toml" in text
    assert "vimrc.kakehashi_config" in text
