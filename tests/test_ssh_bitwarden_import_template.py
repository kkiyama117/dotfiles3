from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / ".chezmoiscripts" / "run_after_install-ssh-keys.sh.tmpl"
DATA = ROOT / ".chezmoidata" / "ssh_keys.yaml"


def test_ssh_import_template_exists_and_is_guarded():
    text = TEMPLATE.read_text()

    assert '{{- if and (not .build_mode) (eq .runtime "container") (env "BW_SESSION") }}' in text
    assert "bitwardenAttachment" in text
    assert "BW_SESSION" in text
    assert "build_mode" in text
    assert 'eq .runtime "container"' in text


def test_ssh_import_template_is_idempotent_and_secret_safe():
    text = TEMPLATE.read_text()

    assert "ssh_import_enabled" in text
    assert "Skipping existing SSH key" in text
    assert "mktemp" in text
    assert "trap cleanup EXIT" in text
    assert "chmod 700" in text
    assert 'write_key_file "$private_path" 600' in text
    assert 'write_key_file "$public_path" 644' in text
    assert "chmod 644" in text
    assert "BEGIN OPENSSH PRIVATE KEY" not in text


def test_ssh_key_metadata_is_non_secret_and_disabled_by_default():
    text = DATA.read_text()

    assert "ssh_import_enabled: false" in text
    assert "private_attachment:" in text
    assert "public_attachment:" in text
    assert "BEGIN OPENSSH PRIVATE KEY" not in text
    assert "PRIVATE KEY" not in text
