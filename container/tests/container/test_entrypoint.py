import os
import signal
import subprocess
import textwrap
import time
import tomllib
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ENTRYPOINT = ROOT / "container" / "bind" / "layer_5_files" / "entrypoint.sh"
SSH_KEY_IMPORT = ROOT / ".chezmoiscripts" / "run_after_install-ssh-keys.sh.tmpl"
MAKEFILE = ROOT / "Makefile"
MISE_CONFIG = ROOT / "dot_config" / "mise" / "config.toml"
GIT_CONFIG = ROOT / "dot_config" / "git" / "config.tmpl"
GIT_DATA = ROOT / ".chezmoidata" / "git_config.yaml"
ZSHENV = ROOT / "dot_zshenv.tmpl"
CHEZMOI_CONFIG = ROOT / ".chezmoi.toml.tmpl"
CHEZMOI_EXTERNAL = ROOT / ".chezmoiexternal.toml.tmpl"
PI_COMMIT_HOOK = ROOT / "programs" / "chezmoi_pi_commit.sh"
PACKAGES = ROOT / "dependencies" / "packages.toml"
CONTAINERFILE = ROOT / "container" / "Containerfile"
MAKEPKG_CONF = ROOT / "container" / "bind" / "layer_1_files" / "makepkg.conf"


def shell_function(text: str, name: str) -> str:
    start = text.index(f"{name}() {{")
    end = text.index("\n}\n", start) + len("\n}\n")
    return text[start:end]


def write_executable(path: Path, body: str) -> None:
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(0o755)


def _entrypoint_env_with_fake_git(tmp_path: Path, fake_git_body: str) -> dict:
    git = tmp_path / "git"
    write_executable(git, fake_git_body)
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}{os.pathsep}{env['PATH']}"
    return env


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


def test_select_external_url_ssh_first_per_repository(tmp_path: Path) -> None:
    """SSH probe success selects SSH; failure falls back to HTTPS per repo."""
    text = ENTRYPOINT.read_text()
    select_fn = shell_function(text, "select_external_url")
    validate_fn = shell_function(text, "validate_external_url")
    run_fn = shell_function(text, "run_interruptible")

    fake_git = textwrap.dedent(
        """
        if [ "$1" = "ls-remote" ]; then
            shift
            url="$1"
            case "$url" in
                *pi-config*) exit 0 ;;
                *) exit 1 ;;
            esac
        fi
        exit 1
        """
    )
    env = _entrypoint_env_with_fake_git(tmp_path, fake_git)

    script = f"""
        set -euo pipefail
        SELECTED_EXTERNAL_URL=""
        {validate_fn}
        {run_fn}
        {select_fn}
        select_external_url "" "git@github.com:kkiyama117/pi-config.git" "https://github.com/kkiyama117/pi-config.git"
        selected_pi="$SELECTED_EXTERNAL_URL"
        select_external_url "" "git@github.com:kkiyama117/nvim_config.git" "https://github.com/kkiyama117/nvim_config.git"
        selected_nvim="$SELECTED_EXTERNAL_URL"
        printf '%s\\n' "$selected_pi" "$selected_nvim"
    """
    result = subprocess.run(
        ["zsh", "-fc", script],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    selected_pi, selected_nvim = result.stdout.strip().splitlines()
    assert selected_pi == "git@github.com:kkiyama117/pi-config.git"
    assert selected_nvim == "https://github.com/kkiyama117/nvim_config.git"


def test_select_external_url_non_empty_override_bypasses_probe(tmp_path: Path) -> None:
    """A non-empty override URL must skip the SSH probe entirely."""
    text = ENTRYPOINT.read_text()
    select_fn = shell_function(text, "select_external_url")
    validate_fn = shell_function(text, "validate_external_url")
    run_fn = shell_function(text, "run_interruptible")

    # This fake git would fail every probe; it must never be called.
    env = _entrypoint_env_with_fake_git(tmp_path, "exit 1")

    script = f"""
        set -euo pipefail
        SELECTED_EXTERNAL_URL=""
        {validate_fn}
        {run_fn}
        {select_fn}
        select_external_url "file:///data/nvim_config" "git@github.com:kkiyama117/nvim_config.git" "https://github.com/kkiyama117/nvim_config.git"
        printf '%s\\n' "$SELECTED_EXTERNAL_URL"
    """
    result = subprocess.run(
        ["zsh", "-fc", script],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "file:///data/nvim_config"


def test_select_external_url_empty_override_uses_probe(tmp_path: Path) -> None:
    """An empty override must fall through to the SSH/HTTPS probe."""
    text = ENTRYPOINT.read_text()
    select_fn = shell_function(text, "select_external_url")
    validate_fn = shell_function(text, "validate_external_url")
    run_fn = shell_function(text, "run_interruptible")

    env = _entrypoint_env_with_fake_git(tmp_path, "exit 0")

    script = f"""
        set -euo pipefail
        SELECTED_EXTERNAL_URL=""
        {validate_fn}
        {run_fn}
        {select_fn}
        select_external_url "" "git@github.com:kkiyama117/pi-config.git" "https://github.com/kkiyama117/pi-config.git"
        printf '%s\\n' "$SELECTED_EXTERNAL_URL"
    """
    result = subprocess.run(
        ["zsh", "-fc", script],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "git@github.com:kkiyama117/pi-config.git"


def test_select_external_url_rejects_http_userinfo(tmp_path: Path) -> None:
    """URL overrides containing HTTP(S) userinfo must be rejected without leaking them."""
    text = ENTRYPOINT.read_text()
    select_fn = shell_function(text, "select_external_url")
    validate_fn = shell_function(text, "validate_external_url")
    run_fn = shell_function(text, "run_interruptible")

    calls = tmp_path / "git-calls"
    env = _entrypoint_env_with_fake_git(
        tmp_path,
        f'echo called >> "{calls}"\nexit 0',
    )

    script = f"""
        set -euo pipefail
        SELECTED_EXTERNAL_URL=""
        {validate_fn}
        {run_fn}
        {select_fn}
        select_external_url "https://token@github.com/owner/repo.git" "git@github.com:owner/repo.git" "https://github.com/owner/repo.git"
        printf '%s\\n' "$SELECTED_EXTERNAL_URL"
    """
    result = subprocess.run(
        ["zsh", "-fc", script],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0, "credential-bearing URL should be rejected"
    assert "token" not in result.stderr
    assert result.stdout.strip() == ""
    assert not calls.exists() or calls.read_text() == ""


def test_select_external_url_enforces_ssh_timeout_options() -> None:
    """The SSH probe must use hard timeouts and non-interactive SSH options."""
    function = shell_function(ENTRYPOINT.read_text(), "select_external_url")

    assert "BatchMode=yes" in function
    assert "ConnectTimeout=5" in function
    assert "GIT_TERMINAL_PROMPT=0" in function
    assert "--kill-after=2s" in function
    assert "10s" in function
    assert "$(" not in function


def test_select_external_url_signal_forwarding_kills_probe(tmp_path: Path) -> None:
    """SIGTERM to the entrypoint shell must terminate the running probe and exit 143."""
    text = ENTRYPOINT.read_text()
    run_fn = shell_function(text, "run_interruptible")
    term_fn = shell_function(text, "terminate")

    child_script = tmp_path / "child.sh"
    pid_file = tmp_path / f"probe-pid-{uuid.uuid4().hex}"
    write_executable(
        child_script,
        f'printf "%s" "$$" > "{pid_file}"\nwhile :; do sleep 0.1; done',
    )

    zsh_script = f"""
        set -euo pipefail
        child_pid=""
        {term_fn}
        {run_fn}
        trap terminate TERM INT
        run_interruptible "{child_script}"
        echo done
    """
    proc = subprocess.Popen(
        ["zsh", "-fc", zsh_script],
        start_new_session=True,
    )

    deadline = time.time() + 5
    while not pid_file.exists():
        if time.time() > deadline:
            break
        time.sleep(0.05)

    child_pid: int | None = None
    if pid_file.exists():
        child_pid = int(pid_file.read_text().strip())

    os.kill(proc.pid, signal.SIGTERM)
    proc.wait(timeout=10)

    assert proc.returncode == 143
    if child_pid is not None:
        # The child should have been killed, not left running.
        for _ in range(50):
            try:
                os.kill(child_pid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.05)
        raise AssertionError(f"probe child {child_pid} still running after SIGTERM")


def test_select_external_url_ignoring_term_falls_back_to_https(tmp_path: Path) -> None:
    """A probe child that ignores TERM must be killed and trigger HTTPS fallback."""
    text = ENTRYPOINT.read_text()
    select_fn = shell_function(text, "select_external_url")
    validate_fn = shell_function(text, "validate_external_url")
    run_fn = shell_function(text, "run_interruptible")

    # Ignore TERM so timeout has to escalate to SIGKILL after --kill-after=2s.
    env = _entrypoint_env_with_fake_git(
        tmp_path,
        "trap '' TERM\nsleep 60\nexit 0",
    )

    script = f"""
        set -euo pipefail
        SELECTED_EXTERNAL_URL=""
        {validate_fn}
        {run_fn}
        {select_fn}
        select_external_url "" "git@github.com:kkiyama117/pi-config.git" "https://github.com/kkiyama117/pi-config.git"
        printf '%s\\n' "$SELECTED_EXTERNAL_URL"
    """
    start = time.time()
    result = subprocess.run(
        ["zsh", "-fc", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    elapsed = time.time() - start

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "https://github.com/kkiyama117/pi-config.git"
    assert elapsed < 13, f"fallback took {elapsed:.1f}s, expected < 13s"


def test_set_external_remote_url_migrates_origin(tmp_path: Path) -> None:
    """An existing managed external's origin remote is rewritten to the selected URL."""
    set_fn = shell_function(ENTRYPOINT.read_text(), "set_external_remote_url")
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    subprocess.run(["git", "init"], cwd=checkout, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://old.example/repo.git"],
        cwd=checkout,
        check=True,
        capture_output=True,
    )
    selected_url = "git@github.com:kkiyama117/pi-config.git"

    script = f"""
        set -euo pipefail
        {set_fn}
        set_external_remote_url "{checkout}" "{selected_url}"
    """
    result = subprocess.run(
        ["zsh", "-fc", script],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    actual = subprocess.check_output(
        ["git", "-C", str(checkout), "remote", "get-url", "origin"],
        text=True,
    ).strip()
    assert actual == selected_url


def test_set_external_remote_url_fails_without_origin(tmp_path: Path) -> None:
    """A checkout that lacks an origin remote must be rejected."""
    set_fn = shell_function(ENTRYPOINT.read_text(), "set_external_remote_url")
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    subprocess.run(["git", "init"], cwd=checkout, check=True, capture_output=True)

    script = f"""
        set -euo pipefail
        {set_fn}
        set_external_remote_url "{checkout}" "git@github.com:kkiyama117/pi-config.git"
    """
    result = subprocess.run(
        ["zsh", "-fc", script],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0


def test_set_external_remote_url_runs_before_apply() -> None:
    """Existing-checkout origin migration must happen after selection/render but before chezmoi apply."""
    text = ENTRYPOINT.read_text()

    select_pi = text.index('select_external_url "${PI_CONFIG_URL:-}"')
    # The header comment also contains the render command; find the actual render call.
    render_idx = text.index("chezmoi execute-template --init \\")
    apply_idx = text.index("run_interruptible chezmoi apply --no-tty --force")
    pi_remote_idx = text.index('\nset_external_remote_url "$HOME/.pi"')
    nvim_remote_idx = text.index('\nset_external_remote_url "$HOME/.config/nvim"')

    assert select_pi < render_idx < pi_remote_idx < apply_idx
    assert select_pi < render_idx < nvim_remote_idx < apply_idx


def test_render_boundary_exports_mixed_ssh_https_selection(tmp_path: Path) -> None:
    """The selected URLs are forwarded to chezmoi execute-template as env vars."""
    text = ENTRYPOINT.read_text()
    select_fn = shell_function(text, "select_external_url")
    validate_fn = shell_function(text, "validate_external_url")
    run_fn = shell_function(text, "run_interruptible")

    env = _entrypoint_env_with_fake_git(
        tmp_path,
        textwrap.dedent(
            """
            if [ "$1" = "ls-remote" ]; then
                shift
                url="$1"
                case "$url" in
                    *pi-config*) exit 0 ;;
                    *) exit 1 ;;
                esac
            fi
            exit 1
            """
        ),
    )

    record = tmp_path / "render-boundary.env"
    write_executable(
        tmp_path / "chezmoi",
        f'echo "PI_CONFIG_URL=$PI_CONFIG_URL" >> "{record}"\n'
        f'echo "NVIM_CONFIG_URL=$NVIM_CONFIG_URL" >> "{record}"\n'
        'echo rendered',
    )

    script = f"""
        set -euo pipefail
        SELECTED_EXTERNAL_URL=""
        {validate_fn}
        {run_fn}
        {select_fn}
        select_external_url "" "git@github.com:kkiyama117/pi-config.git" "https://github.com/kkiyama117/pi-config.git"
        selected_pi_config_url="$SELECTED_EXTERNAL_URL"
        select_external_url "" "git@github.com:kkiyama117/nvim_config.git" "https://github.com/kkiyama117/nvim_config.git"
        selected_nvim_config_url="$SELECTED_EXTERNAL_URL"
        PI_CONFIG_URL="$selected_pi_config_url" NVIM_CONFIG_URL="$selected_nvim_config_url" chezmoi execute-template --init < /dev/null > /dev/null
    """
    result = subprocess.run(
        ["zsh", "-fc", script],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    lines = record.read_text().strip().splitlines()
    assert "PI_CONFIG_URL=git@github.com:kkiyama117/pi-config.git" in lines
    assert "NVIM_CONFIG_URL=https://github.com/kkiyama117/nvim_config.git" in lines


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


def test_make_up_forwards_external_url_and_ref_variables() -> None:
    text = MAKEFILE.read_text()
    up_target = text.split("up: _require_username", 1)[1].split("\nexec:", 1)[0]

    for variable in (
        "PI_CONFIG_URL",
        "PI_CONFIG_REF",
        "NVIM_CONFIG_URL",
        "NVIM_CONFIG_REF",
    ):
        assert f"--env {variable}" in up_target


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


def test_git_uses_shared_ssh_commit_signing() -> None:
    config = GIT_CONFIG.read_text()
    data = GIT_DATA.read_text()

    assert "gpgsign = true" in config
    assert "format = ssh" in config
    assert "format = openpgp" not in config
    assert "signingkey: ~/.ssh/main" in data
    assert "A1E4E20240EA5BAA" not in data


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
    assert "url = {{ .pi_config_url | quote }}" in external
    assert 'refreshPeriod = "0"' in external
    assert 'clone.args = ["--branch", {{ .pi_config_ref | quote }}, "--depth", "1", "--no-single-branch"]' in external


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
    assert "url = {{ .nvim_config_url | quote }}" in external
    assert 'clone.args = ["--branch", {{ .nvim_config_ref | quote }}, "--depth", "1", "--no-single-branch"]' in external
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


def test_pi_is_mise_managed_via_aqua() -> None:
    mise_config = MISE_CONFIG.read_text()
    packages = PACKAGES.read_text()
    containerfile = CONTAINERFILE.read_text()

    assert '"aqua:earendil-works/pi" = "latest"' in mise_config
    assert "npm:@earendil-works/pi-coding-agent" not in mise_config
    assert 'name = "pi-coding-agent"' not in packages
    assert "@earendil-works/pi-coding-agent" not in containerfile
    assert "# Layer 3-5: Install pi coding agent CLI" not in containerfile


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


def test_kakehashi_inventory_and_container_install() -> None:
    packages = PACKAGES.read_text()
    containerfile = CONTAINERFILE.read_text()
    entrypoint = ENTRYPOINT.read_text()

    assert 'name = "kakehashi"' in packages
    assert 'manager = "custom"' in packages
    assert 'layer = 3' in packages

    start = containerfile.index("# Layer 3-8: Install kakehashi")
    end = containerfile.index("# Stage 4: aur", start)
    block = containerfile[start:end]

    assert containerfile.index("# Layer 3-7:") < start < end
    assert "releases/latest" in block
    assert '%{url_effective}' in block
    assert "v<->.<->.<->" in block
    assert "--proto-redir \"=https\"" in block
    assert "https://github.com/atusy/kakehashi/releases/download/" in block
    assert "x86_64-unknown-linux-gnu.tar.gz" in block
    assert "mktemp -d" in block
    assert "trap " in block
    assert "tar -tzf" in block
    assert "tar -tvzf" in block
    assert "--no-same-owner --no-same-permissions" in block
    assert '! -L "$staging/kakehashi"' in block
    assert 'install -D -m 0755' in block
    assert '"$HOME/.local/bin/kakehashi" --version' in block
    assert "kakehashi" not in entrypoint


def test_external_template_renders_quoted_values(tmp_path: Path) -> None:
    """The final external TOML sink must quote values and survive special characters."""
    external = CHEZMOI_EXTERNAL.read_text()

    assert "url = {{ .pi_config_url | quote }}" in external
    assert '{{ .pi_config_ref | quote }}' in external
    assert "url = {{ .nvim_config_url | quote }}" in external
    assert '{{ .nvim_config_ref | quote }}' in external

    config_path = tmp_path / "chezmoi.toml"
    config_path.write_text(
        textwrap.dedent(
            """
            [data]
            build_mode = false
            runtime = "container"
            pi_config_url = 'https://github.com/example/pi-"quoted".git'
            pi_config_ref = 'branch-"quoted"'
            nvim_config_url = 'https://github.com/example/nvim-"quoted".git'
            nvim_config_ref = 'branch-"quoted"'
            """
        ).strip()
    )
    rendered = subprocess.run(
        [
            "chezmoi",
            "execute-template",
            "--init",
            "--config",
            str(config_path),
        ],
        input=external,
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    parsed = tomllib.loads(rendered)
    assert parsed[".pi"]["url"] == 'https://github.com/example/pi-"quoted".git'
    assert parsed[".config/nvim"]["clone"]["args"][1] == 'branch-"quoted"'
