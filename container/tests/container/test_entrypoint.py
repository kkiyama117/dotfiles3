from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ENTRYPOINT = ROOT / "container" / "bind" / "layer_5_files" / "entrypoint.sh"
MAKEFILE = ROOT / "Makefile"
MISE_CONFIG = ROOT / "dot_config" / "mise" / "config.toml"
ZSHENV = ROOT / "dot_zshenv.tmpl"
CHEZMOI_CONFIG = ROOT / ".chezmoi.toml.tmpl"
CHEZMOI_EXTERNAL = ROOT / ".chezmoiexternal.toml.tmpl"
PI_LINK_SCRIPT = ROOT / ".chezmoiscripts" / "run_after_configure-pi-agent.sh.tmpl"
PI_COMMIT_HOOK = ROOT / "programs" / "chezmoi_pi_commit.sh"
PACKAGES = ROOT / "dependencies" / "packages.toml"
CONTAINERFILE = ROOT / "container" / "Containerfile"


def test_entrypoint_forwards_stop_signal_during_startup_work() -> None:
    text = ENTRYPOINT.read_text()

    assert "trap terminate TERM INT" in text
    assert "chezmoi execute-template --init" in text
    assert "run_interruptible chezmoi apply --no-tty --force" in text


def test_make_up_uses_init_for_steady_state_signal_forwarding() -> None:
    text = MAKEFILE.read_text()

    up_target = text.split("up: _require_username", 1)[1].split("\nexec:", 1)[0]
    assert "--init" in up_target


def test_entrypoint_writes_readiness_sentinel_only_after_apply() -> None:
    """make up waits on /tmp/chezmoi-applied; it must be removed at start
    and touched only after `chezmoi apply` succeeds so a stale flag can
    never satisfy the wait and a failed apply never publishes readiness."""
    text = ENTRYPOINT.read_text()

    assert 'READINESS_SENTINEL="/tmp/chezmoi-applied"' in text
    rm_idx = text.index('rm -f "$READINESS_SENTINEL"')
    apply_idx = text.index("run_interruptible chezmoi apply --no-tty --force")
    touch_idx = text.index('touch "$READINESS_SENTINEL"')
    assert rm_idx < apply_idx < touch_idx


def test_entrypoint_seeds_chezmoi_source_before_readiness() -> None:
    """The first interactive shell after `make up` should have the source
    bind in zoxide without needing the user to visit it manually."""
    text = ENTRYPOINT.read_text()

    apply_idx = text.index("run_interruptible chezmoi apply --no-tty --force")
    seed_idx = text.index("seed_zoxide_paths", apply_idx)
    touch_idx = text.index('touch "$READINESS_SENTINEL"')
    assert apply_idx < seed_idx < touch_idx

    assert 'for path in "$CHEZMOI_SOURCE"; do' in text
    assert '"$zoxide_bin" add -- "$path"' in text


def test_entrypoint_zoxide_seed_uses_absolute_binary_fallback() -> None:
    """The entrypoint's non-interactive PATH can miss /usr/sbin, while the
    container zoxide package installs there."""
    text = ENTRYPOINT.read_text()

    assert "/usr/sbin/zoxide" in text
    assert '"$zoxide_bin" add -- "$path"' in text


def test_make_up_waits_for_readiness_sentinel() -> None:
    """make up must poll for the sentinel and abort (with logs) if the
    container exits early or the timeout elapses."""
    text = MAKEFILE.read_text()

    up_target = text.split("up: _require_username", 1)[1].split("\nexec:", 1)[0]
    assert "UP_WAIT_TIMEOUT" in up_target
    assert "/tmp/chezmoi-applied" in up_target
    assert "podman logs" in up_target
    assert "exit 1" in up_target


def test_make_up_verifies_image_entrypoint_is_fresh() -> None:
    """make up must refuse to run a stale image whose entrypoint differs
    from the source at container/bind/layer_5_files/entrypoint.sh, so the
    readiness-sentinel wait loop cannot time out against an old entrypoint
    that never writes /tmp/chezmoi-applied. See spec 20 I-RUN3."""
    text = MAKEFILE.read_text()

    # `up` must list _verify_image_fresh as a prerequisite.
    up_header = text.split("up:", 1)[1].split("\n", 1)[0]
    assert "_verify_image_fresh" in up_header

    # The verify target must compare source vs image entrypoint hashes and
    # fail with a `make build` hint on mismatch.
    verify_body = text.split("_verify_image_fresh:", 1)[1].split("\n\n", 1)[0]
    assert "sha256sum" in verify_body
    assert "/usr/local/bin/entrypoint.sh" in verify_body
    assert "podman run --rm --entrypoint /usr/bin/sha256sum" in verify_body
    assert "stale entrypoint" in verify_body
    assert "make build" in verify_body
    assert "exit 1" in verify_body


def test_zshenv_owns_pnpm_bootstrap_env() -> None:
    mise_config = MISE_CONFIG.read_text()
    zshenv = ZSHENV.read_text()

    assert "[env]" not in mise_config
    assert "PNPM_HOME" not in mise_config
    assert "export PNPM_HOME=" in zshenv
    assert "path=($PNPM_HOME/bin $path)" in zshenv


def test_pi_config_external_is_build_mode_gated_and_pinned() -> None:
    config = CHEZMOI_CONFIG.read_text()
    external = CHEZMOI_EXTERNAL.read_text()

    assert "pi_config_url" in config
    assert "PI_CONFIG_URL" in config
    assert "https://github.com/kkiyama117/pi-config.git" in config
    assert "pi_config_ref" in config
    assert "PI_CONFIG_REF" in config
    assert "pi-config-v2026-07-08-1" in config

    assert "{{- if not .build_mode }}" in external
    assert '[".local/share/pi-config"]' in external
    assert 'type = "git-repo"' in external
    assert 'url = "{{ .pi_config_url }}"' in external
    assert 'refreshPeriod = "0"' in external
    assert 'clone.args = ["--branch", "{{ .pi_config_ref }}", "--depth", "1"]' in external
    assert "file:///data/pi-config" not in external


def test_pi_link_script_manages_only_stable_resources() -> None:
    text = PI_LINK_SCRIPT.read_text()

    assert "{{- if not .build_mode }}" in text
    assert ".local/share/pi-config/agent" in text
    assert ".pi/agent" in text
    for name in ("settings.json", "prompts", "skills", "extensions", "themes"):
        assert f'link_resource "{name}"' in text

    forbidden = ("auth.json", "trust.json", "sessions", "transcripts", "npm", "git", "logs", "cache")
    for name in forbidden:
        assert f'link_resource "{name}"' not in text


def test_pi_commit_hook_uses_external_prompt_precedence() -> None:
    text = PI_COMMIT_HOOK.read_text()

    assert "PI_COMMIT_PROMPT_FILE" in text
    assert "$HOME/.pi/agent/prompts/commit.md" in text
    assert "$HOME/.local/share/pi-config/agent/prompts/commit.md" in text
    assert '$src_dir/.pi/prompts/commit.md' not in text


def test_pi_coding_agent_inventory_and_container_install() -> None:
    packages = PACKAGES.read_text()
    containerfile = CONTAINERFILE.read_text()

    assert 'name = "pi-coding-agent"' in packages
    assert 'manager = "custom"' in packages
    assert "@earendil-works/pi-coding-agent" in packages
    assert "@earendil-works/pi-coding-agent" in containerfile
    assert "--ignore-scripts" in containerfile
    assert "pi --version" in containerfile
