import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ENTRYPOINT = ROOT / "container" / "bind" / "layer_5_files" / "entrypoint.sh"
SSH_KEY_IMPORT = ROOT / ".chezmoiscripts" / "run_after_install-ssh-keys.sh.tmpl"
MAKEFILE = ROOT / "Makefile"
MISE_CONFIG = ROOT / "dot_config" / "mise" / "config.toml"
ZSHENV = ROOT / "dot_zshenv.tmpl"
CHEZMOI_CONFIG = ROOT / ".chezmoi.toml.tmpl"
CHEZMOI_EXTERNAL = ROOT / ".chezmoiexternal.toml.tmpl"
PI_COMMIT_HOOK = ROOT / "programs" / "chezmoi_pi_commit.sh"
PACKAGES = ROOT / "dependencies" / "packages.toml"
CONTAINERFILE = ROOT / "container" / "Containerfile"
MAKEPKG_CONF = ROOT / "container" / "bind" / "layer_1_files" / "makepkg.conf"


def test_entrypoint_forwards_stop_signal_during_startup_work() -> None:
    text = ENTRYPOINT.read_text()

    assert "trap terminate TERM INT" in text
    assert "chezmoi execute-template --init" in text
    assert "run_interruptible chezmoi apply --no-tty --force" in text


def test_entrypoint_propagates_failed_child_status() -> None:
    """A failed chezmoi child must stop the entrypoint before readiness."""
    text = ENTRYPOINT.read_text()
    start = text.index("run_interruptible() {")
    end = text.index("\n}\n", start) + len("\n}\n")
    function = text[start:end]

    result = subprocess.run(
        ["zsh", "-fc", f"set -e\n{function}\nrun_interruptible false\n"],
        check=False,
    )

    assert result.returncode != 0


def test_entrypoint_bootstraps_externals_without_changing_git_remotes() -> None:
    """Startup may bootstrap over HTTPS but must not rewrite Git remotes."""
    text = ENTRYPOINT.read_text()

    assert 'PI_CONFIG_BOOTSTRAP_URL="https://github.com/kkiyama117/pi-config.git"' in text
    assert 'NVIM_CONFIG_BOOTSTRAP_URL="https://github.com/kkiyama117/nvim_config.git"' in text
    assert "remote set-url" not in text
    assert "switch_external_remote_to_ssh" not in text

    apply_idx = text.index("run_interruptible chezmoi apply --no-tty --force")
    ready_idx = text.index('touch "$READINESS_SENTINEL"')
    assert apply_idx < ready_idx


def test_ssh_key_normalization_does_not_require_perl(tmp_path: Path) -> None:
    """The runtime image has zsh but not Perl."""
    text = SSH_KEY_IMPORT.read_text()
    start = text.index("normalize_key_file() {")
    end = text.index("\n}\n", start) + len("\n}\n")
    function = text[start:end]
    key_file = tmp_path / "key"
    key_file.write_bytes(b"line1\r\nline2\rline3")

    result = subprocess.run(
        ["zsh", "-fc", f'{function}\nnormalize_key_file "$1"', "zsh", str(key_file)],
        check=False,
    )

    assert result.returncode == 0
    assert key_file.read_bytes() == b"line1\nline2\nline3\n"
    assert "perl" not in function


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


def test_chezmoi_config_enables_bitwarden_unlock_auto() -> None:
    text = CHEZMOI_CONFIG.read_text()
    assert "[bitwarden]" in text
    assert 'unlock = "auto"' in text


def test_pi_config_external_is_build_mode_gated_and_pinned() -> None:
    config = CHEZMOI_CONFIG.read_text()
    external = CHEZMOI_EXTERNAL.read_text()

    assert "pi_config_url" in config
    assert "PI_CONFIG_URL" in config
    assert "git@github.com:kkiyama117/pi-config.git" in config
    assert "pi_config_ref" in config
    assert "PI_CONFIG_REF" in config
    assert 'pi_config_ref = {{ env "PI_CONFIG_REF" | default "main" | quote }}' in config

    assert "{{- if and (not .build_mode) (eq .runtime \"container\") }}" in external
    assert 'eq .runtime "container"' in external
    assert '[".pi"]' in external
    assert 'type = "git-repo"' in external
    assert 'url = "{{ .pi_config_url }}"' in external
    assert 'refreshPeriod = "0"' in external
    assert 'clone.args = ["--branch", "{{ .pi_config_ref }}", "--depth", "1", "--no-single-branch"]' in external


def test_nvim_config_external_is_build_mode_gated_and_pinned() -> None:
    config = CHEZMOI_CONFIG.read_text()
    external = CHEZMOI_EXTERNAL.read_text()

    assert "nvim_config_url" in config
    assert "NVIM_CONFIG_URL" in config
    assert "git@github.com:kkiyama117/nvim_config.git" in config
    assert "nvim_config_ref" in config
    assert "NVIM_CONFIG_REF" in config
    assert 'nvim_config_ref = {{ env "NVIM_CONFIG_REF" | default "main" | quote }}' in config

    assert '[".config/nvim"]' in external
    assert 'url = "{{ .nvim_config_url }}"' in external
    assert 'clone.args = ["--branch", "{{ .nvim_config_ref }}", "--depth", "1", "--no-single-branch"]' in external
    assert "file:///data/nvim_config" not in external


def test_containerfile_arg_comments_are_not_inline() -> None:
    """Podman parses words after ARG as more argument names, even after #."""
    arg_lines = [
        line for line in CONTAINERFILE.read_text().splitlines() if line.startswith("ARG ")
    ]

    assert all(" #" not in line for line in arg_lines)


def test_pi_commit_hook_uses_external_prompt_precedence() -> None:
    text = PI_COMMIT_HOOK.read_text()

    assert "PI_COMMIT_PROMPT_FILE" in text
    assert "$HOME/.pi/agent/prompts/commit.md" in text
    assert "$HOME/.local/share/pi-config/agent/prompts/commit.md" not in text
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


def test_makepkg_conf_baked_into_layer_1_2() -> None:
    containerfile = CONTAINERFILE.read_text()
    makepkg = MAKEPKG_CONF.read_text()

    assert "COPY bind/layer_1_files/makepkg.conf /etc/makepkg.conf" in containerfile
    assert "PKGEXT='.pkg.tar.xz'" in makepkg
    assert "COMPRESSZST=(zstd -c -z -q -)" in makepkg
    copy_idx = containerfile.index("COPY bind/layer_1_files/makepkg.conf /etc/makepkg.conf")
    mirror_idx = containerfile.index("COPY bind/layer_1_files/pacman_mirrorlist")
    syu_idx = containerfile.index("pacman -Syu --noconfirm")
    assert copy_idx < mirror_idx < syu_idx
