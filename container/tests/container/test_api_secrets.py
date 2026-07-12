from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
API_SECRETS_DATA = ROOT / ".chezmoidata" / "api_secrets.yaml"
SECRETS_TMPL = ROOT / "dot_config" / "zsh" / "rc" / "secrets.zsh.tmpl"
SHELDON = ROOT / "dot_config" / "sheldon" / "plugins.toml"
BW_SESSION = ROOT / "dot_config" / "zsh" / "rc" / "functions" / "bw_session.zsh"


def test_api_secrets_data_lists_v1_providers() -> None:
    text = API_SECRETS_DATA.read_text()
    for env in (
        "GH_TOKEN",
        "OPENROUTER_API_KEY",
        "MOONSHOT_API_KEY",
        "OLLAMA_API_KEY",
    ):
        assert f"env: {env}" in text
    assert "field: api_key" in text
    assert "enabled:" not in text
    assert "OLLAMA_HOST" not in text


def test_secrets_template_build_mode_guard() -> None:
    text = SECRETS_TMPL.read_text()
    assert "# chezmoi:mode=600" in text
    assert "{{- if not .build_mode -}}" in text
    guard_start = text.index("{{- if not .build_mode")
    guard_end = text.index("{{- end -}}")
    body = text[guard_start:guard_end]
    assert "bitwardenFields" in body
    tail = text[guard_end + len("{{- end -}}") :]
    assert "bitwarden" not in tail


def test_secrets_template_exports_all_data_entries() -> None:
    text = SECRETS_TMPL.read_text()
    assert "{{- range .api_secrets }}" in text
    assert 'export {{ .env }}=' in text
    assert '(index $fields .field).value' in text


def test_sheldon_my_secrets_plugin_is_synchronous() -> None:
    text = SHELDON.read_text()
    block_start = text.index("[plugins.my_secrets]")
    block_end = text.index("[plugins.my_functions]", block_start)
    block = text[block_start:block_end]
    assert 'use = ["secrets.zsh"]' in block
    assert 'apply = ["source"]' in block
    assert "defer" not in block


def test_sheldon_plugin_order_secrets_before_functions() -> None:
    text = SHELDON.read_text()
    defer_idx = text.index("[plugins.my_conf_defered]")
    secrets_idx = text.index("[plugins.my_secrets]")
    funcs_idx = text.index("[plugins.my_functions]")
    assert defer_idx < secrets_idx < funcs_idx


def test_bw_session_helper_exists() -> None:
    text = BW_SESSION.read_text()
    assert "bw_session()" in text
    assert "/run/secrets/bw_password" in text
    assert "bw unlock --raw" in text
