from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / ".chezmoiscripts" / "run_after_install-ssh-keys.sh.tmpl"
DATA = ROOT / ".chezmoidata" / "ssh_keys.yaml"


def test_ssh_import_template_exists_and_is_guarded():
    text = TEMPLATE.read_text()

    assert '{{- if and (not .build_mode) (eq .runtime "container") }}' in text
    assert "build_mode" in text
    assert 'eq .runtime "container"' in text


def test_ssh_import_template_fetches_attachments_with_bw_session():
    text = TEMPLATE.read_text()

    assert '[ -z "${BW_SESSION:-}" ]' in text
    assert "bw get attachment" in text
    assert '--session "$BW_SESSION"' in text
    assert "--itemid" in text
    assert "bitwardenAttachment" not in text


def test_ssh_import_template_is_idempotent_and_secret_safe():
    text = TEMPLATE.read_text()

    assert "ssh_import_enabled" in text
    assert "Skipping existing SSH key" in text
    assert "Repairing missing public key" in text
    assert "mktemp" in text
    assert "trap cleanup EXIT" in text
    assert "chmod 700" in text
    assert 'fetch_attachment_file {{ .item | quote }} {{ .private_attachment | quote }} "$private_path" 600' in text
    assert 'fetch_attachment_file {{ .item | quote }} {{ .public_attachment | quote }} "$public_path" 644' in text
    assert "chmod 644" in text
    assert "BEGIN OPENSSH PRIVATE KEY" not in text


def test_ssh_import_template_normalizes_crlf_attachments():
    text = TEMPLATE.read_text()

    assert "normalize_key_file" in text
    assert "perl -0pi -e 's/\\r\\n/\\n/g; s/\\r/\\n/g'" in text
    assert 'normalize_key_file "$private_path"' in text
    assert 'normalize_key_file "$public_path"' in text


def test_ssh_key_metadata_is_non_secret():
    text = DATA.read_text()

    assert "ssh_import_enabled:" in text
    assert "item:" in text
    assert "private_attachment:" in text
    assert "public_attachment:" in text
    assert "BEGIN OPENSSH PRIVATE KEY" not in text
    assert "PRIVATE KEY" not in text
