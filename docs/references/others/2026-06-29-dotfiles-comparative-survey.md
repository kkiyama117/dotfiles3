# Famous Dotfiles — Comparative Survey

**Date:** 2026-06-29
**Author:** investigation dispatched by kiyama, synthesized from 4 parallel research subagents
**Scope of inputs:**
- ~14 famous dotfiles repos surveyed by GitHub fetch (software inventory)
- ~17 chezmoi/stow/yadm/bare-git/Nix/custom-installer repos (management tooling)
- ~25 dotfiles repos + chezmoi upstream (install verification / CI patterns)
- home-manager / nix-darwin / sops-nix / agenix / Guix home / Ansible (declarative end)

**Reading order:** Part 3 (validation) is the section closest to kiyama's podman-based testing concern and contains the actionable "Top 5 Steals". Part 1 is the breadth check; Parts 2 and 4 are context for tool-choice tradeoffs.

---

## TL;DR

- **Software inventory** (Part 1): zsh / Neovim / tmux / starship / fzf-ripgrep-bat-fd-eza stack is the modern dotfiles baseline. **Terminal** drift is fastest: iTerm2 → Alacritty → WezTerm → Ghostty. **chezmoi / mise / rbw / podman** — kiyama's distinctive stack — barely appear in famous public dotfiles; he is well ahead of the public curve there.
- **Management tools** (Part 2): chezmoi is the most expressive (templates + 12+ password managers + ordered lifecycle hooks + per-OS subdirs). Stow has the cleanest layout but zero hook surface. yadm has alternates instead of templates. Nix/home-manager is the only model with *typed compile-time validation* but inverts the whole stack.
- **Validation/CI** (Part 3): The dotfile community's median CI is essentially "run `./install` in a fresh GH runner and check exit code." Kiyama's podman-based BuildKit-secret pipeline is **above the field median** on the build side and **below the chezmoi-CI subset** on the assertion side. Highest-leverage gaps: bats behavior tests, idempotence assertion (run twice + grep `0 changes`), and `chezmoi doctor` / `chezmoi verify` as post-apply gates.
- **Declarative end** (Part 4): home-manager gives whole-closure validation chezmoi cannot; chezmoi gives template debuggability and pacman-friendliness home-manager cannot. Verdict for kiyama: stay on chezmoi + podman; do not migrate. Optional small experiment is a side `flake.nix` for one slice (git+zsh) to get typed validation in CI without committing.

---

# Part 1 — Software Inventory Across Famous Dotfiles

## Methodology

Fetched READMEs and root listings for 14 widely-cited dotfiles repos via WebFetch against GitHub HTML. Star counts are GitHub-reported as of the fetch and rounded; tool lists come from directory names and README descriptions, so deeply nested plugins (Brewfile lines, lazy.nvim plugin specs) are not exhaustively enumerated. Skipped: `Skyzh/dotfiles` (404 — repo deleted/renamed) and `mischavandenburg/dotfiles` (made private, behind paid community).

## Per-Repo Profiles

### mathiasbynens/dotfiles (~31k stars)
- **URL:** https://github.com/mathiasbynens/dotfiles
- **Manager:** Custom `bootstrap.sh` (rsync into `$HOME`) + `brew.sh`
- **Flavor:** The classic macOS bash reference dotfiles — minimal, surgical, no modern CLI add-ons.
- **Inventory:**
  - Shell: bash (`.bashrc`, `.bash_profile`, `.bash_prompt`, `.aliases`, `.functions`, `.inputrc`)
  - Multiplexer: tmux, GNU screen
  - Editor: Vim (`.vimrc`, `.gvimrc`), editorconfig, gdb
  - Git: `.gitconfig`, `.gitattributes`, `.gitignore`
  - Package mgr: Homebrew (`brew.sh`)
  - Misc: `.curlrc`, `.wgetrc`
  - OS tweaks: `.macos` (defaults write script)
- **Notable:** `.macos` defaults script is the canonical reference others copy from; supports `~/.extra` for secret overrides without forking.

### thoughtbot/dotfiles (~8.2k stars)
- **URL:** https://github.com/thoughtbot/dotfiles
- **Manager:** `rcm` (their own dotfile manager)
- **Flavor:** Rails-consultancy starter kit — Ruby/Postgres-heavy, opinionated for paired teams.
- **Inventory:**
  - Shell: zsh (`zshrc`, `zprofile`, `zshenv`, `aliases`)
  - Multiplexer: tmux (prefix Ctrl+s)
  - Editor: Vim + `vim-plug`, ctags
  - Git: gitconfig, gitmessage, git_template hooks
  - Version mgr: asdf (`asdfrc`)
  - Lang tooling: gemrc, railsrc, rspec, psqlrc
  - Search: ag (`agignore`)
- **Notable:** Personal layering via `~/dotfiles-local`; one of the few well-known repos shipping an `asdfrc`.

### holman/dotfiles (~7.7k stars)
- **URL:** https://github.com/holman/dotfiles
- **Manager:** Custom `script/bootstrap` (topical: `*.symlink`, `*.zsh` auto-sourced)
- **Flavor:** The "topical dotfiles" pattern — one folder per tool, the architecture half the community copies.
- **Inventory:**
  - Shell: zsh
  - Editor: vim, `editors/`
  - Git: full git topic dir
  - Package mgr: Homebrew (Brewfile + `homebrew/`)
  - Lang: Ruby
  - Misc: atuin, docker, yarn, xcode, custom `bin/`
- **Notable:** Atuin appears at top level (rare among older repos); the topical layout is itself the influential artifact.

### paulirish/dotfiles (~4.3k stars)
- **URL:** https://github.com/paulirish/dotfiles
- **Manager:** Hand-rolled `setup-a-new-machine.sh` + `brew.sh` / `brew-cask.sh`
- **Flavor:** Chrome DevTools-era web-dev kit — heavy on Node/JS linting and fish shell.
- **Inventory:**
  - Shell: fish (primary), bash retained
  - Editor: vim, Sublime launcher
  - Multiplexer: tmux
  - Git: gitconfig + git-completion.bash
  - Package mgr: Homebrew
  - JS tooling: eslint, oxlint, prettier
  - Misc: iTerm2 fish integration, mpv config, custom `bin/` (incl. `git-open`)
- **Notable:** One of the few high-star fish setups; ships `oxlintrc.json` (Rust-based JS linter).

### josean-dev/dev-environment-files (~4.1k stars)
- **URL:** https://github.com/josean-dev/dev-environment-files
- **Manager:** GNU stow
- **Flavor:** YouTube-tutorial "modern terminal dev env" — WezTerm + Neovim + tmux, copy-pastable.
- **Inventory:**
  - Shell: zsh
  - Terminal: WezTerm (primary), iTerm2, Ghostty (Linux)
  - Multiplexer: tmux
  - Editor: Neovim + lazy.nvim, Mason
  - Git: lazygit (in nvim), gitsigns
  - WM (mac): yabai, aerospace, sketchybar
  - WM (linux): Hyprland, waybar
  - Misc: fzf, fd, bat, delta, eza, ripgrep, tldr, thefuck
- **Notable:** Explicit dual macOS/Linux WM coverage; canonical "starter pack" of modern CLI tools.

### omerxx/dotfiles (~3.4k stars)
- **URL:** https://github.com/omerxx/dotfiles
- **Manager:** GNU stow (`.stowrc` + `setup.sh`), Nix-darwin layer
- **Flavor:** Modern macOS power-user — Aerospace + Ghostty + Zellij, heavy Nushell experimentation.
- **Inventory:**
  - Shell: zsh + nushell (~29% of codebase)
  - Terminal: Ghostty, WezTerm
  - Multiplexer: tmux, Zellij
  - Editor: Neovim, KindaVim (system-wide vim)
  - Prompt: starship
  - History: atuin
  - WM (mac): Aerospace, skhd, SketchyBar, Hammerspoon
  - Misc: gh-dash, Television (fzf alternative), Karabiner
  - Package/system: Nix + nix-darwin
- **Notable:** Hybrid stow + Nix; Television and Nushell are unusual choices; popular YouTube source.

### nicknisi/dotfiles (~3k stars)
- **URL:** https://github.com/nicknisi/dotfiles
- **Manager:** Custom `dot` CLI (symlink-based subcommands)
- **Flavor:** Long-running macOS zsh setup, conservative but kept current; "dot" command pattern is the calling card.
- **Inventory:**
  - Shell: zsh, custom `zfetch` plugin manager
  - Terminal: WezTerm
  - Editor: Neovim + lazy.nvim
  - Multiplexer: tmux (prefix Ctrl-A)
  - Git: dotted config + `dot git setup`
  - Package mgr: Homebrew (Brewfile)
  - WM (mac): Aerospace, Raycast
  - Plugins: zsh-syntax-highlighting, zsh-autosuggestions, fzf-tab
- **Notable:** Bespoke `dot` subcommand router (link, unlink, brew, macos, shell); ships terminfo for italic Neovim.

### LazyVim/starter (~1.9k stars)
- **URL:** https://github.com/LazyVim/starter
- **Manager:** Cloned into `~/.config/nvim` directly
- **Flavor:** Reference Neovim distribution starter — editor-only, no shell/terminal opinions.
- **Inventory:**
  - Editor: Neovim (LazyVim + lazy.nvim, `init.lua`, `.neoconf.json`, `stylua.toml`)
- **Notable:** Pure-editor scaffold; included here because countless dotfiles repos vendor it as their `nvim/` directory.

### cowboy/dotfiles (~1.6k stars)
- **URL:** https://github.com/cowboy/dotfiles
- **Manager:** Custom `bin/dotfiles` (copy/link/init phases)
- **Flavor:** Pre-modern bash classic with one of the most-copied prompt scripts.
- **Inventory:**
  - Shell: bash + custom prompt (git/svn, exit code, timestamps)
  - Editor: vim
  - Git: gitconfig, git-extras
  - Version mgr: rbenv, nave (node)
  - Package mgr: Homebrew + apt (Ubuntu branch)
- **Notable:** Three-phase install (copy/link/init) inspired many forks; vendor/ dir for third-party libs; cross-OS aware.

### typecraft-dev/dotfiles (~1.4k stars)
- **URL:** https://github.com/typecraft-dev/dotfiles
- **Manager:** stow-style `.config` layout (no explicit manager declared)
- **Flavor:** YouTube "ricing" Linux desktop — multiple WMs/bars/launchers side-by-side for tutorials.
- **Inventory:**
  - Shell: zsh
  - Terminal: Alacritty, Ghostty, Kitty
  - Editor: Neovim
  - Multiplexer: tmux
  - Prompt: starship
  - WM: Hyprland (+ hyprlock, hyprpaper), i3, picom
  - Bars: Waybar, Polybar
  - Launchers: Wofi, Rofi
- **Notable:** Side-by-side X11 and Wayland stacks in one repo (rare); educational rather than personal-use.

### yutkat/dotfiles (~971 stars, Japanese dev)
- **URL:** https://github.com/yutkat/dotfiles
- **Manager:** Nix + home-manager (with apt/pacman fallbacks)
- **Flavor:** Heavy Linux power-user, NixOS-first, ~5k commits — closest in spirit to kiyama's setup.
- **Inventory:**
  - Shell: zsh + zinit, powerlevel10k prompt
  - Terminal: WezTerm
  - Editor: Neovim (~50% of codebase is Lua)
  - WM: Hyprland (primary), i3, sway
  - Launcher: walker; Notifier: dunst
  - Package/system: Nix + home-manager, pacman, apt
  - OS support: NixOS, Arch, Ubuntu, Fedora, CentOS
- **Notable:** True multi-distro support with explicit install paths per OS; one of few Japanese dotfiles at this scale.

### b4b4r07/dotfiles (~778 stars, Japanese dev)
- **URL:** https://github.com/babarot/dotfiles (renamed from b4b4r07)
- **Manager:** Makefile-driven, with own zsh plugin manager `afx`
- **Flavor:** Long-tenured Japanese dev's setup (~2k commits); minimalist macOS zsh.
- **Inventory:**
  - Shell: zsh (`.zshrc`, `.zprofile`, `.zshenv`)
  - Terminal: Ghostty
  - Editor: Neovim
  - Multiplexer: tmux + tpm
  - Git: gitconfig, gitmessage
  - Plugin mgr: `afx` (his own)
  - Package mgr: Homebrew (Brewfile)
  - Fonts: DejaVuSansMono Nerd Font
- **Notable:** Ships `afx` (declarative package/plugin manager he authored); Obsidian-Vim integration; `.fdignore`, `.dir_colors` present.

### caarlos0/dotfiles (~215 stars)
- **URL:** https://github.com/caarlos0/dotfiles
- **Manager:** Plain `./setup` shell script (after migrating away from Ansible and Nix)
- **Flavor:** Fish-shell power-user (GoReleaser author) — went from Nix back to shell deliberately.
- **Inventory:**
  - Shell: fish
  - Terminal: Ghostty, Rio
  - Editor: Neovim (Lua-heavy)
  - Multiplexer: tmux
  - Git: gitconfig, gh, gh-dash
  - Misc: direnv, fd, custom scripts, Hammerspoon
  - Package mgr: Homebrew (Brewfile)
- **Notable:** Explicit "I tried Nix and Ansible, came back to bash"; gh-dash and fish are signature picks.

### ChristianChiarulli/machfiles (~720 stars, formerly "ChristianChiarulli/dotfiles")
- **URL:** https://github.com/ChristianChiarulli/machfiles
- **Manager:** GNU stow
- **Flavor:** LunarVim author's personal rice — all four major terminals + all three OS WMs.
- **Inventory:**
  - Shell: zsh
  - Terminal: Alacritty, WezTerm, Kitty, Ghostty
  - Editor: Neovim, VSCodium
  - WM: Hyprland, sway, yabai+skhd (mac)
  - File mgr: ranger
  - Misc: waybar, rofi, picom, dunst, cava (audio viz), amfora (Gemini browser), stylua
  - Package mgr: Homebrew
- **Notable:** Cava and Amfora are genuinely unusual; ships every modern terminal so viewers can pick.

## Cross-Repo Observations

**Most common tools across the sample (14 repos):**
1. zsh (10/14) — bash holdouts: mathiasbynens, paulirish, cowboy
2. Neovim (10/14) — pure vim still on mathiasbynens, paulirish, thoughtbot, cowboy
3. tmux (12/14) — universal except LazyVim starter
4. Git config (14/14)
5. Homebrew (11/14) — even on Linux-leaning repos as macOS fallback
6. fzf / ripgrep / bat / fd / eza (~7/14, almost always together)
7. Ghostty (6/14) — fastest-rising terminal in the sample
8. WezTerm (5/14) — current "modern terminal" default
9. starship (4/14, climbing)
10. Hyprland (5/14) — dominant Wayland WM among Linux configs

**Trending shifts visible across the sample:**
- **Prompt:** powerlevel10k → starship (only yutkat still ships p10k)
- **Multiplexer:** tmux still dominant, but Zellij appears in newer repos (omerxx)
- **Editor:** vim → Neovim is essentially complete; lazy.nvim is the standard plugin manager
- **Version manager:** asdf → mise migration in progress (thoughtbot still on asdf, kiyama on mise; few public examples either way)
- **Terminal:** iTerm2 → Alacritty → WezTerm → Ghostty migration path
- **Window manager (mac):** yabai → Aerospace (no SIP-disable requirement)
- **Dotfile manager:** bare-git/stow still dominate; Nix appears in 2 (omerxx partial, yutkat full); chezmoi is conspicuously absent
- **History:** atuin appears in 3 (holman, omerxx, implied elsewhere) and growing

**Gaps vs. kiyama's stack (`/data/dotfiles2`: chezmoi + zsh + sheldon + mise + direnv + git + podman + rbw):**
- **chezmoi**: zero hits in the sample. The "dot_" prefix pattern is invisible to the broader community; stow/rcm/custom-script dominate.
- **mise**: zero explicit hits. asdf still the only version-manager that appears in READMEs (thoughtbot). kiyama is ahead of the curve.
- **sheldon**: zero hits. Public repos use zinit (yutkat), zfetch (nicknisi), afx (b4b4r07), oh-my-zsh, or none.
- **rbw / Bitwarden CLI**: zero hits. Secrets handling is universally hand-waved (`~/.extra`, gitignored env files); no public repo manages secret retrieval in-config.
- **podman**: zero hits. Docker appears only in holman/dotfiles; container-as-dev-env is essentially unrepresented.
- **paru/pacman**: only yutkat addresses Arch/Manjaro explicitly; the sample is overwhelmingly macOS-first.
- **direnv**: appears in caarlos0; commonly assumed but not configured. kiyama is mainstream here.
- **Present in sample, absent from kiyama**: tmux (multiplexer), Neovim config, a terminal emulator config, a prompt config (starship/p10k), modern CLI bundle (fzf/ripgrep/bat/eza/zoxide/atuin) — i.e. kiyama's repo is currently infrastructure-only (shell + secrets + version mgr + containers) and skips the UX surface most public dotfiles center on.

---

# Part 2 — Dotfiles Management Tooling Survey

Surveyed six management approaches by reading the public GitHub source of ~2-3 representative repos per tool plus upstream tool docs where the in-repo evidence was thin.

## chezmoi

### How it works
chezmoi keeps the *source state* in a normal git repo (typically `~/.local/share/chezmoi`) where file *names* encode the desired target — `dot_zshrc` → `~/.zshrc`, `private_dot_ssh/` enforces `0700`, `executable_` sets `+x`, `empty_` allows zero-length, `symlink_` becomes a symlink, `.tmpl` is rendered with Go text/template. `chezmoi apply` reads source state plus runtime template data (`.chezmoi.{toml,yaml}.tmpl` evaluated at `chezmoi init`, plus `.chezmoidata.*` static data) and writes the target tree. Lifecycle scripts (`.chezmoiscripts/run_{once,onchange,always}_{before,after}_*.sh.tmpl`) are ordered shell hooks; `.chezmoihooks/` defines `read-source-state` pre/post commands. `.chezmoiexternal.toml` pulls in third-party files (e.g. zsh plugins) without vendoring.

### Real-world repos
- [twpayne/dotfiles](https://github.com/twpayne/dotfiles) — chezmoi author's own dotfiles; canonical reference for `.chezmoiscripts/{linux,darwin,windows}/` per-OS subtrees and 1Password integration
- [felipecrs/dotfiles](https://github.com/felipecrs/dotfiles) — Ubuntu-focused bootstrap; heavy `run_after_NN-*` numbered ordering, `.chezmoihooks/ensure-pre-requisites.sh`, prompt validation with regex retries
- [renemarc/dotfiles](https://github.com/renemarc/dotfiles) — simpler/older layout (`dot_` at repo root, no `home/` subtree, no `.chezmoiscripts/`); showcases cross-shell + Windows `.bat.tmpl` rendering and `symlink_` prefix

### Lifecycle hooks (run_after_install patterns observed)
- **Per-OS subdirectories** (twpayne) — `.chezmoiscripts/linux/run_onchange_before_install-packages.sh.tmpl`, `.chezmoiscripts/linux/run_onchange_after_chsh.sh.tmpl`, `.chezmoiscripts/linux/run_onchange_before_install-op.sh.tmpl` (installs 1Password CLI). Top-level `run_onchange_after_configure-vscode.sh.tmpl` runs everywhere and `code --force --install-extension …` per line.
- **Numeric ordering prefix** (felipecrs) — `run_before_10-migrate`, `run_after_10-initialize-zsh`, `run_after_20-run-rootmoi` (re-invokes chezmoi as root for system files), `run_after_30-install-homebrew-packages`, `run_after_31-install-volta-packages`, `run_after_40-sync-wsl-ssh-keys`, `run_after_80-remove-files`, `run_after_81-install-gnome-extensions`, `run_after_82-configure-gnome`, `run_after_85-install-winget-packages-on-windows`, `run_after_90-install-vscode-extensions`, `run_after_98-prune-chezmoi-binary`, `run_onchange_after_99-final-message`.
- **`run_onchange_` for idempotent re-runs** — script body is hashed; chezmoi re-runs only when the rendered script changes. Frequent pattern: package install lists embedded in the script so adding/removing a package re-triggers install.
- **`.chezmoihooks/` pre-state hook** (felipecrs) — `ensure-pre-requisites.sh` runs *before* chezmoi reads its source state. Used to install missing CLI deps (`op`, `pkgx`) that templates then call out to.
- **`modify_` files** (felipecrs `modify_dot_gitconfig`) — script that takes the existing target file on stdin and prints the new content; preserves user-edited values that chezmoi shouldn't clobber.

### Secret handling
chezmoi natively integrates with **1Password** (`onepassword`, `onepasswordRead`, `onepasswordDocument`), **Bitwarden** (`bitwarden`, `bitwardenFields`, `bitwardenSecrets`, plus `rbw`/`rbwFields` for the rust client), **pass**/`gopass`, **KeePassXC**, **HashiCorp Vault**, plus generic `secret`/`secretJSON` shelling out to any command. Per docs: also AWS Secrets Manager, Azure Key Vault, Doppler, LastPass, Proton Pass, Keeper, ejson, Dashlane.
- twpayne wires 1Password from his README ("Login to 1Password with `eval $(op signin)`") and ships a Linux installer for `op` so first-`apply` can resolve secret templates.
- felipecrs does not pull secrets via chezmoi; SSH keys are copied from the Windows host into WSL by `run_after_40-sync-wsl-ssh-keys.sh.tmpl` rather than templated from a vault.
- renemarc punts entirely — keeps secrets out of the repo with no integration.

### Observations
The author's own repo (twpayne) doubles as the de-facto style guide: per-OS script subdirs, boolean "feature tag" data (`ephemeral`/`work`/`headless`/`personal`) set from hostname switches in `.chezmoi.toml.tmpl`. felipecrs is the more *complete* example of post-install automation — explicit two-digit ordering, root re-invocation pattern ("rootmoi"), and a pre-source-state hook to bootstrap chezmoi's own dependencies. Honest weakness: the Go template syntax with `{{-` whitespace trimming and `promptBoolOnce` is genuinely hard to read at scale; large `.chezmoi.toml.tmpl` files (twpayne's hostname/OS switchboard) become a single point of failure for "which feature flags am I on?".

## GNU stow

### How it works
Stow is a 1990s Perl utility that treats each top-level directory under the dotfiles repo as a "package" whose internal tree mirrors `$HOME`. `stow zsh -t ~` walks `zsh/` and creates symlinks in `~/` pointing back into the package — `zsh/.config/zsh/.zshrc` becomes `~/.config/zsh/.zshrc → …/dotfiles/zsh/.config/zsh/.zshrc`. No templating, no hooks, no secrets — purely a smarter `ln -s`. Adding/removing packages is `stow`/`stow -D`.

### Real-world repos
- [xero/dotfiles](https://github.com/xero/dotfiles) — clean per-package layout (`bash/`, `zsh/`, `neovim/`, `tmux/`, `git/`, `ssh/`, `bin/`); README shows manual `stow zsh -t ~`
- [jaagr/dots](https://github.com/jaagr/dots) — author of polybar; stow-style layout, demonstrates the convention applied across i3/polybar/compton configs
- (counter-example) [alrra/dotfiles](https://github.com/alrra/dotfiles) is frequently cited as a "stow" repo but actually rolls its own `src/os/setup.sh` with custom symlink logic — illustrates how often real users *opt out* of stow even when their repo looks stow-shaped

### Lifecycle hooks (run_after_install patterns observed)
Stow itself has zero hook surface. Real users either: (a) document manual follow-up steps in the README ("now run tmux plugin install"), (b) wrap stow in a `Makefile` / `install.sh` that runs `stow` then any post-steps, or (c) commit a sibling `bootstrap` script outside the package directories. xero's repo takes route (a) — manual steps documented in README for tmux/nvim plugins.

### Secret handling
None. Stow has no notion of secrets; users keep secrets out of the repo (gitignore + `*.local` overrides) or pair stow with `git-crypt` / `transcrypt` at the git layer.

### Observations
Strength: the *layout convention is the entire spec* — opening a stow repo, you immediately know where every file goes. Weakness: no per-host conditionals (you can't say "this `.gitconfig` only on macOS") without splitting into `git-mac/` and `git-linux/` packages, no templating means hardcoded paths and emails, and post-install automation is bolt-on. Best fit: single-OS workstations where the user wants a one-page mental model and is willing to do package-by-package activation.

## yadm

### How it works
yadm (Yet Another Dotfiles Manager) is a ~3k-line bash wrapper around `git` whose work tree is `$HOME` and git dir is `$HOME/.local/share/yadm/repo.git`. Files live at their final paths (`.bashrc`, not `dot_bashrc`). Per-host/OS specialization uses **alternates**: name a file `file##os.Linux,class.work` and `yadm alt` (auto-run during normal operations) creates a symlink from `file` to the highest-scoring matching variant. Conditions include `os`, `hostname`, `class` (set with `yadm config local.class work`), `arch`, `distro`, `user`. A **bootstrap** script at `$HOME/.config/yadm/bootstrap` runs once after `yadm clone`. Encryption: list patterns in `$HOME/.config/yadm/encrypt`, run `yadm encrypt` to produce a GPG (default) or OpenSSL archive at `$HOME/.local/share/yadm/archive` that ships with the repo.

### Real-world repos
- [yadm-dev/yadm](https://github.com/yadm-dev/yadm) — the tool itself (docs and tests are themselves a reference)
- [harperreed/dotfiles](https://github.com/harperreed/dotfiles) — actively maintained yadm-managed personal dotfiles; classic flat HOME-relative layout, sibling `.gitconfig.linux` / `.gitconfig.mac` files (alternate-adjacent pattern)

### Lifecycle hooks (run_after_install patterns observed)
yadm has a single first-class hook: the **bootstrap** script. Per yadm.io/docs/bootstrap it runs once after `yadm clone` (with `--bootstrap`/`--no-bootstrap` prompt suppression) and can be re-invoked anytime with `yadm bootstrap`. Conventional contents: install Homebrew, init submodules, set vim plugins, configure macOS defaults. yadm also supports arbitrary git hooks (`yadm/hooks/pre-commit`, etc.) and a generic `command.<cmd>.{pre,post}` config for wrapping any `yadm <cmd>` invocation — used in practice for things like auto-decrypt after pull.

### Secret handling
Native encryption via GPG (symmetric by default, asymmetric if `yadm.gpg-recipient` is set) or OpenSSL (`yadm.cipher = openssl`, AES-256-CBC default). The encrypted archive is git-committed; `yadm decrypt` re-extracts on a new machine. Also supported: transparent encryption via third-party `transcrypt` / `git-crypt`.

### Observations
Strength: the alternates scoring system (more matching conditions ⇒ higher score) cleanly expresses host/OS variation without templating syntax — and `class` is user-defined so "work vs personal" is just a config setting. Weakness: bootstrap is a single script with no built-in dependency ordering (vs chezmoi's `run_after_NN-` convention), so non-trivial setups become a hand-managed bash file. Encryption-in-git is real but a password-rotation burden — once a secret leaks into history it's still recoverable. Real-world adoption is materially smaller than chezmoi (search "yadm dotfiles" surfaces ~5 noteworthy public repos vs 100+ for chezmoi).

## bare git repo

### How it works
Per the canonical Atlassian/Streaver writeup: `git init --bare $HOME/.cfg`, then alias `config='git --git-dir=$HOME/.cfg/ --work-tree=$HOME'`, then `config config --local status.showUntrackedFiles no` so `config status` doesn't list every file in `$HOME`. Add files in place (`config add ~/.bashrc; config commit; config push`). New machine: `git clone --bare <url> $HOME/.cfg`, set the alias, `config checkout` — files materialize at their final paths. No second tool, no symlinks, no templates.

### Real-world repos
- The technique itself is repo-shape-agnostic — public repos using it look like *any* dotfiles repo (just files at their HOME-relative paths). [Ackama writeup](https://www.ackama.com/what-we-think/the-best-way-to-store-your-dotfiles-a-bare-git-repository-explained/) and the Atlassian dev tutorial are the cited references.
- In practice indistinguishable on GitHub from a yadm repo without a `.config/yadm/` directory. Hard to cite a *famous* example because the technique is invisible from the repo itself.

### Lifecycle hooks (run_after_install patterns observed)
None native. Users add a hand-rolled `~/.config/dotfiles-bootstrap` shell script and document "run this after `config checkout`" in the README. Standard git hooks (`.cfg/hooks/post-checkout`) are technically available but rarely used.

### Secret handling
None native. Same options as raw git: `.gitignore`, `git-crypt`, `git-secret`, BlackBox. The biggest *operational* footgun is that, because files live in place, an accidental `config add .ssh/id_ed25519` will commit a private key with no friction — chezmoi's `private_` prefix and yadm's encrypt list at least force the user to think.

### Observations
Strength: zero dependencies beyond `git`. Onboarding a fresh machine is two commands plus a checkout. The mental model fits anyone who already knows git. Weakness: no per-host variation, no templating, no installed-package management, and the checkout-conflict workflow on a system with pre-existing config files is hostile. Best fit: minimal single-host personal setups or as a *complement* to a real config manager.

## Nix / home-manager / nix-darwin

### How it works
A `flake.nix` declaratively specifies system configurations (NixOS, nix-darwin, home-manager) as pure functions of inputs (`nixpkgs`, `home-manager`, secret backends like `sops-nix` or `agenix`). `nixos-rebuild switch --flake .#<host>` (or `darwin-rebuild` / `home-manager switch`) builds the *entire* system closure — packages, dotfiles, services — into the nix store and atomically swaps `/run/current-system`. Rollback is `nixos-rebuild --rollback` to a previous generation. Dotfiles are written from Nix expressions: `programs.git = { enable = true; userName = "…"; }` generates the actual `~/.config/git/config`. There are no symlinks-from-a-repo and no templating in the chezmoi sense — *the language is the template*.

### Real-world repos
- [Misterio77/nix-config](https://github.com/Misterio77/nix-config) — flakes-based multi-host (`hosts/`, `home/`, `modules/`, `overlays/`, `pkgs/`); ships `.sops.yaml`, a `flake.nix`, `deploy.sh`, `hydra.nix` (Hydra CI binary cache)
- [mitchellh/nixos-config](https://github.com/mitchellh/nixos-config) — Mitchell Hashimoto's; `machines/`, `modules/specialization/`, `users/mitchellh/`, Makefile-driven (`make vm/bootstrap0` → `make vm/bootstrap` → `make switch` lifecycle), cross-build path for WSL
- [budimanjojo/nix-config](https://github.com/budimanjojo/nix-config) — interesting hybrid: Nix flakes *plus* chezmoi for the dotfiles chezmoi handles better than Nix's text-generation

### Lifecycle hooks (run_after_install patterns observed)
"After install" largely doesn't exist — the model is *fully declarative*, and what would be a post-install script elsewhere is expressed as `system.activationScripts.foo = "…"` (NixOS) or `home.activation.foo = lib.hm.dag.entryAfter ["writeBoundary"] "…"` (home-manager) and runs on every `switch`. Real entry points are usually thin Makefile targets: mitchellh's `make vm/bootstrap0` → `make vm/bootstrap` → `make switch`/`make test`; Misterio77's `deploy.sh` wraps `nixos-rebuild` with sops key handling.

### Secret handling
- **sops-nix** (Misterio77, mainstream choice) — YAML/JSON encrypted with `age` or PGP, keys derived from each host's SSH host key + the operator's YubiKey-backed PGP. Decryption happens at activation time into `/run/secrets/`.
- **agenix** — minimal pure-age alternative; same idea, smaller surface.
- **pass** — Misterio77 explicitly uses `pass` for personal interactive secrets (not the Nix-managed kind), keeping the GPG identity on the same YubiKey.

### Observations
Strength: reproducibility is real — `nix flake lock` pins every input by hash, so `rebuild` two years later produces a bit-identical system. Multi-host scaling is genuinely good. Weakness: the learning cliff is the steepest of any tool here (mitchellh's README explicitly says "not a turnkey solution"), and *dotfile mutability* fights the model — config files you'd casually edit need to be either (a) Nix expressions you re-rebuild on every tweak, or (b) excluded from Nix and managed by something else. The budimanjojo hybrid (Nix + chezmoi) is an honest acknowledgment of this tension.

## Custom scripts / Makefile / dotbot

### How it works
A grab-bag of DIY approaches. Two dominant patterns: (1) **convention-based script** — walk the repo for files with a magic suffix (`*.symlink`, `*.zsh`) and act on each; (2) **declarative manifest** — a YAML/JSON file lists symlinks, shell commands, and dependencies, executed by a small runner (dotbot, rcm, makesymlinks). Both pair with a `bootstrap`/`install.sh` entrypoint and OS-specific subdirectories.

### Real-world repos
- [holman/dotfiles](https://github.com/holman/dotfiles) — the classic "topic-centric" Zach Holman repo; per-topic dirs (`ruby/`, `git/`, `vim/`) each containing `*.symlink`, `*.zsh`, optional `install.sh`. `script/bootstrap` does the symlinking; `script/install` runs all `install.sh` files.
- [thoughtbot/dotfiles](https://github.com/thoughtbot/dotfiles) — uses **rcm** (thoughtbot's own tool, `brew install rcm`); bootstrap is `env RCRC=$HOME/dotfiles/rcrc rcup`, updates are `rcup`. Ships git templates with `post-checkout`/`post-commit`/`post-merge` hooks to auto-rebuild ctags.
- [anishathalye/dotbot](https://github.com/anishathalye/dotbot) — the YAML-runner; `install.conf.yaml` with `link:`, `create:`, `shell:`, `clean:` directives, ~3k+ user repos. Idempotent by design — re-running is safe.
- [LukeSmithxyz/voidrice](https://github.com/LukeSmithxyz/voidrice) — files in place; install is the external [LARBS](https://larbs.xyz) script (`curl -LO larbs.xyz/larbs.sh`) which clones + installs packages from a CSV. No in-repo tool.

### Lifecycle hooks (run_after_install patterns observed)
- **holman** — `script/bootstrap`'s `link_files` walks `find -maxdepth 2 -name '*.symlink' -not -path '*.git*'`, prompts overwrite/backup/skip per collision, then a separate `setup_gitconfig` reads `git/gitconfig.local.symlink.example`, prompts for name/email/credential-helper, sed-substitutes into `gitconfig.local.symlink`. `script/install` then runs every `*/install.sh` in the topic dirs.
- **rcm** — `rcup` re-runs are the hook ("after-install" is just "run rcup again"); per-host overrides via `host-<hostname>/` dirs and tag selection.
- **dotbot** — post-install is an arbitrary `shell:` directive: `[git submodule update --init --recursive, Installing submodules]`, `chsh -s $(which zsh)`. Idempotency is the user's responsibility.
- **LARBS / voidrice** — install is a single non-resumable shell script that reads a `programs.csv` (name, source, description) and either `pacman -S` or `yay -S` or `git clone && make install` per row. No per-machine state tracked.

### Secret handling
Almost universally manual:
- holman: `gitconfig.local.symlink` is gitignored, sed-templated at bootstrap from prompts. SSH keys/tokens documented as "you supply".
- thoughtbot/rcm: same pattern — `*.local` files override and stay out of the repo.
- dotbot: no native support; users wire `git-crypt` or vault CLIs into `shell:` directives.
- LARBS/voidrice: out of scope; user copies their own keys.

### Observations
Strength: total control, zero abstraction tax, and the "find by suffix" patterns (holman's `*.symlink`) are *very* readable for someone landing in the repo cold. dotbot's YAML is the right level of declarative for users who want one file as the install spec. Weakness: every project reinvents collision handling, per-host conditionals, idempotency, and dependency ordering — exactly the surface chezmoi/Nix nailed down. Custom scripts age poorly: holman's repo is functionally archived, and many "famous" custom-installer dotfiles haven't been touched in 5+ years.

## Cross-Manager Comparison

| Aspect | chezmoi | stow | yadm | bare git | nix/home-manager | custom (dotbot/holman) |
|---|---|---|---|---|---|---|
| Templating | Go text/template (first-class) | none | none | none | Nix language *is* the template | usually `sed` substitution |
| Secrets | 12+ password managers (1Password, Bitwarden/rbw, pass, KeePassXC, Vault, …) via template funcs | none (use git-crypt) | native GPG/OpenSSL encrypt list | none (use git-crypt) | sops-nix / agenix (encrypted in repo, decrypted at activation) | usually `*.local` + manual `git-crypt` |
| Multi-host | hostname-driven template data + per-OS script subdirs | one package per OS variant (manual split) | alternates suffix `##os.X,class.Y,hostname.Z` (auto-scored) | none (single tree) | one flake output per host (`nixosConfigurations.<host>`) | per-tag subdirs (rcm) or per-host `case "$HOSTNAME"` |
| Hook scripts | `.chezmoiscripts/run_{once,onchange,always}_{before,after}_*.sh.tmpl` + ordering prefix + `.chezmoihooks/` | none (wrap in Makefile) | single `bootstrap` script + `command.<cmd>.{pre,post}` git hooks | none (DIY shell) | declarative `system.activationScripts` / `home.activation` | bootstrap entrypoint + per-topic `install.sh` (holman) or `shell:` directives (dotbot) |
| Reproducible install verification | re-run `apply` is idempotent; `chezmoi diff` shows pending changes; `verify` exits non-zero on drift | re-`stow` is a no-op if links exist; no drift detection | `yadm status` shows drift; bootstrap re-runnable if idempotent | `config status` shows drift on tracked files only; checkout is destructive | flake.lock pins inputs by hash → bit-identical rebuilds; `nixos-rebuild build` for dry-run | per-tool: dotbot is idempotent by design; holman/LARBS aren't — they're install-only |

---

# Part 3 — Install Verification: How Others Do It (PRIMARY SECTION)

This is the section closest to kiyama's podman-based testing concern. Surveyed ~25 public dotfiles repositories plus chezmoi upstream itself, weighted toward repos that look similar to kiyama's setup (chezmoi-managed, Linux-targeted, opinionated install scripts). All quotes are from real files fetched live; negative findings ("repo X has *no* CI") are called out. Bias: the sample skews toward maintainers who already care about validation — i.e. the upper end of the field, not the median dotfiles repo.

## Pattern 1: Containerized install sandbox

### Variant 1a: Single Dockerfile per OS, build-and-run in CI

The dominant pattern: ship a `Dockerfile` per target distro, build it inside a GitHub-hosted runner, and let the build/run exit-code be the test.

- **Example:** [twpayne/chezmoi](https://github.com/twpayne/chezmoi/blob/master/assets/docker/test.sh) — `assets/docker/test.sh` + `assets/docker/{alpine,archlinux,fedora,...}.Dockerfile`.
  - **Mechanism:** `./assets/docker/test.sh alpine` is invoked from `.github/workflows/main.yml` jobs `test-alpine` / `test-archlinux`. The script does `docker build . -f assets/docker/${distribution}.Dockerfile -q` then `docker run --rm --volume "${PWD}:/chezmoi" <image>`. Inside, `assets/docker/entrypoint.sh` runs `go tool chezmoi doctor || true && go test ./... && sh assets/scripts/install.sh && bin/chezmoi --version`.
  - **Catches:** install-script regressions on Alpine (musl/BusyBox), Arch (rolling), Fedora; missing build deps; chezmoi self-test failures.
  - **Misses:** does not actually `chezmoi apply` a real dotfiles tree — chezmoi here is testing *itself*, not a user dotfiles set. No bats-style behavior assertions.
  - **Steal-for-kiyama:** YES — the `test.sh distribution1 distribution2 ...` dispatcher is a clean parallel to kiyama's single `Containerfile`. A second `Containerfile.archlinux` (host-target equivalent) would unlock a real distro matrix.

- **Example:** [shunk031/dotfiles](https://github.com/shunk031/dotfiles) — `Dockerfile` (root) + `.github/workflows/{ubuntu.yaml,macos.yaml,test.yaml,remote.yaml}` + `tests/files/{common,ubuntu,macos}.bats`.
  - **Mechanism:** `Dockerfile` = `FROM ubuntu:22.04` + `RUN apt-get install ... bats sudo ...` + `RUN sudo sh -c "$(curl -fsLS get.chezmoi.io)" -- -b /usr/local/bin`. The CI matrix `system: [server, client]` runs `printf "${EMAIL_ADDRESS}\n${SYSTEM}\n" | bash -c "$(wget -qO - $URL)"` (i.e. pipes user-config answers into setup.sh non-interactively), then `bats tests/files/common.bats` + `bats --filter-tags common,ubuntu:${SYSTEM} tests/files/ubuntu.bats`.
  - **Catches:** broken `setup.sh` on Ubuntu, missing chezmoi templates per system profile, missing tools after install (asserted by bats).
  - **Misses:** Arch / Manjaro path is not exercised (kiyama's primary target).
  - **Steal-for-kiyama:** YES, with adaptation. This is the closest public mirror of kiyama's architecture. The `system: [server, client]` matrix idea maps directly to a kiyama `profile: [workstation, ci]` matrix once chezmoi data has that axis. See Top-5 steal #1.

- **Example:** [utouto97/dotfiles](https://github.com/utouto97/dotfiles/blob/main/.github/workflows/check.yml) — `.github/workflows/check.yml` runs three jobs (`ubuntu`, `lint`, `bench`).
  - **Mechanism:** `ubuntu` job uses `container: ubuntu:latest` directly (no Dockerfile), then `./install.sh`, then `nvim --headless "+Lazy! update" +qa`, then `zsh -i -c exit`. The nvim/zsh probes are the entire "post-install smoke test."
  - **Catches:** nvim plugin-spec breakage, zsh interactive-startup failure (catches `zshrc` syntax errors, missing sourced files).
  - **Misses:** no broader package presence check, no GPG/SSH/git config assertions.
  - **Steal-for-kiyama:** YES — `zsh -i -c exit` and a `nvim --headless +qa` are cheap, language-agnostic smoke probes that kiyama's `make verify` does not currently include. Costs ~2 lines.

- **Example:** [edjchapman/dotfiles](https://github.com/edjchapman/dotfiles/blob/main/.github/workflows/audit.yml) — uses `chezmoi execute-template --init` to render `Brewfile.tmpl` against synthetic data, then `brew info --json` to validate each formula.
  - **Mechanism:** `chezmoi execute-template --init --source="$(pwd)" --override-data "{...}" < Brewfile.tmpl > "/tmp/Brewfile.$mt"` — exercises template rendering without a full apply.
  - **Catches:** template syntax errors, missing package data, formulas that no longer exist upstream.
  - **Misses:** non-template files; runtime behavior of installed packages.
  - **Steal-for-kiyama:** PARTIAL — kiyama has very few templates (`dot_zshenv` etc.), so the audit surface is small, but a `chezmoi execute-template --init` smoke against the rendered config files would catch template breakage independent of vault availability.

- **Example:** [TheTrueZeroTwo/DotFiles](https://github.com/TheTrueZeroTwo/DotFiles/blob/main/.gitea/workflows/distro-checks.yml) — `matrix.include` runs fedora/debian/ubuntu/arch/alpine/opensuse containers (on Gitea, but the pattern is identical to GH Actions).
  - **Mechanism:** `include: [- {name: Arch, image: archlinux:latest}, - {name: Fedora, image: fedora:latest}, ...]` per-job container.
  - **Catches:** distro-specific package-manager breakage in install scripts.
  - **Misses:** rolling-release breakage between scheduled runs (no cron).
  - **Steal-for-kiyama:** PARTIAL — kiyama is Manjaro-first; a future `[manjaro, arch, endeavouros]` matrix would catch divergence across the Arch family.

### Variant 1b: Podman / Containerfile (rare in CI; common as portable env)

Podman-as-CI is rare because GH-hosted runners default to docker. Podman as a *portable runtime container* exists but is usually built via `redhat-actions/buildah-build`.

- **Example:** [sainnhe/dotfiles](https://github.com/sainnhe/dotfiles) — `Containerfile` (alpine:edge) + `.github/workflows/build.yml`.
  - **Mechanism:** `build.yml` triggers on `workflow_dispatch`, `push` of `Containerfile`, and `schedule: cron "12 0 * * 0"` (weekly). Uses `redhat-actions/buildah-build@v2` with `oci: true`, `containerfiles: ./Containerfile`, `platforms: linux/amd64,linux/arm64/v8`, then pushes to ghcr.io and quay.io.
  - **Catches:** drift between Containerfile and upstream alpine; multi-arch breakage; AUR-equivalent in alpine `testing` repo.
  - **Misses:** no in-container test step at all — success = "buildah-build exit 0". No `chezmoi verify`, no smoke run.
  - **Steal-for-kiyama:** NO (and notably weaker than kiyama's current `make verify`). The portable-image idea (push a daily fresh image to a registry so a new machine can `podman run -it ghcr.io/...`) is interesting as a *separate* feature, not as validation.

- **Negative finding:** A focused search for dotfiles repos that use `Containerfile` *and* a podman-specific test step did not turn up an obvious peer. The two closest are sainnhe (above) and kiyama himself. The pattern "podman + Containerfile + smoke test inside" is essentially unique to dotfiles2 in the surveyed sample.

### Variant 1c: devcontainer.json (VS Code dev containers / Codespaces)

- **Example:** [rio/dotfiles](https://github.com/rio/dotfiles) — has `.devcontainer/devcontainer.json` + `Dockerfile` + chezmoi `apply` in the post-create hook. The blog post [alfonsofortunato.com/blog/dotfile/](https://alfonsofortunato.com/blog/dotfile/) documents the same pattern: `.devcontainer/` contains a `Dockerfile` and `devcontainer.json` whose `postCreateCommand` runs `chezmoi init --apply <repo>`. Codespaces-ready repos use `"dotfiles": { "repository": "owner/dotfiles" }` in the Codespaces config so opening any project provisions the dotfiles.
  - **Mechanism:** "Reopen in Container" or "Open in Codespaces" triggers `devcontainer.json` → builds the image → runs `postCreateCommand` → chezmoi applies → developer sees a configured shell. The *test surface* is the developer's first-launch experience, not CI.
  - **Catches:** breakage of the bootstrap path (clone → init → apply) that interactive use takes for granted.
  - **Misses:** no automated assertion — failure is "the dev container won't open." There's no CI matrix here unless the maintainer wires `devcontainers/ci@v0.3` into a workflow (rare in dotfile repos).
  - **Steal-for-kiyama:** LOW — kiyama explicitly rules out a remote/Codespaces flow (FF-only, local-only repo per memory `project_no_prs_ff_only`). Devcontainer would be a niche convenience for a future hosted lab, not validation.

### Variant 1d: Nix hermetic build (`nix flake check`)

- **Example:** [Mic92/dotfiles](https://github.com/Mic92/dotfiles/blob/main/flake.nix) — `flake.nix` includes `./checks/flake-module.nix` and `./checks/effects.nix`, exposing a `checks` output consumed by Hercules CI (`hercules-ci-effects`). `nix flake check` validates the closure builds, evaluates pure, and passes the maintainer's custom checks.
  - **Mechanism:** `nix --accept-flake-config flake check` evaluates all `checks.<system>.<name>` derivations to completion. Combined with `nix build .#homeConfigurations."x".activationPackage`, every dotfile is a derivation that *must* build hermetically.
  - **Catches:** any non-determinism, missing inputs, evaluation errors — the strongest correctness guarantee in this whole document.
  - **Misses:** does not test *applying* into a real `$HOME`; the build derivation can succeed while the activation script fails on a real user account. Also requires committing to Nix as the install mechanism.
  - **Steal-for-kiyama:** NO. Kiyama's stack is pacman/paru/uv/nix-as-just-a-package-manager. Adopting flakes for hermetic validation alone would invert the whole architecture.

- **Example (peer for reference):** [fufexan/dotfiles](https://github.com/fufexan/dotfiles) — NixOS + home-manager dotfiles where the build itself is the test.

### Variant 1e: HOME-redirection sandbox (no container at all)

The cheapest test: redirect `$HOME` to a scratch dir on a clean GH runner and run the installer.

- **Example:** [anishathalye/dotfiles](https://github.com/anishathalye/dotfiles/blob/master/.github/workflows/ci.yml) — full workflow is 15 lines:
  ```yaml
  jobs:
    build:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v2
        - run: mkdir -p ~/dotfiles-install-dir
        - run: HOME=~/dotfiles-install-dir ./install
  ```
  Schedule: `cron '0 8 * * 6'` (weekly).
  - **Mechanism:** rename `$HOME`, run installer, success = `./install` exits 0.
  - **Catches:** broken `./install` (which delegates to dotbot), missing submodule symlinks.
  - **Misses:** anything that depends on the *real* user environment (GPG, SSH, vault); only catches what the installer itself does.
  - **Steal-for-kiyama:** NO directly — kiyama's install touches gpg-agent, rbw, ssh-agent in ways that can't be `HOME`-redirected. But the *cost* of this pattern (one workflow file, zero infrastructure) is the floor everyone should beat.

- **Example:** [EyesofBucket/dotfiles](https://github.com/EyesofBucket/dotfiles/blob/main/.github/workflows/main.yml) — same idea: `apt-get install zsh stow ...` then `./setup.sh`.

## Pattern 2: CI matrix (GitHub Actions)

### Sub-pattern 2a: OS matrix

| Repo | Matrix dimension | Notes |
|---|---|---|
| [twpayne/chezmoi](https://github.com/twpayne/chezmoi/blob/master/.github/workflows/main.yml) | `macos-15`, `ubuntu-22.04`, `windows-2022`, plus dedicated `test-alpine` + `test-archlinux` Docker jobs | Most thorough — splits OS into runner-native vs. container-hosted jobs to cover non-GH-runner distros. |
| [anishathalye/dotbot](https://github.com/anishathalye/dotbot/blob/master/.github/workflows/ci.yml) | `["ubuntu-22.04", "macos-latest", "windows-latest"]` × 9 Python versions | 27-cell matrix for a tool that has to work everywhere. |
| [shunk031/dotfiles](https://github.com/shunk031/dotfiles) | Separate workflows per OS (`ubuntu.yaml`, `macos.yaml`) instead of one matrix | Lets each OS have its own paths-filter, secrets, and post-install benchmark. |
| [upnt/dotfiles](https://github.com/upnt/dotfiles/blob/main/.github/workflows/healthcheck.yml) | linux + `windows-2025` | Notable for testing on Windows via `winget install --id twpayne.chezmoi`. |
| [TheTrueZeroTwo/DotFiles](https://github.com/TheTrueZeroTwo/DotFiles/blob/main/.gitea/workflows/distro-checks.yml) | `matrix.include: [{image: fedora}, {image: arch}, {image: alpine}, {image: opensuse}, {image: ubuntu}, {image: debian}]` | The closest example of a deliberate Linux-distro fan-out. |
| [pragmaticivan/dotfiles](https://github.com/pragmaticivan/dotfiles) | `matrix: system: [server, client]` plus separate macos/ubuntu workflows | The non-OS axis (server vs. client) is a useful idea for kiyama. |

- **Steal-for-kiyama:** Pull the distro fan-out idea (TheTrueZeroTwo) and the orthogonal profile axis (shunk031/pragmaticivan). Cost = one extra Containerfile per distro + a `profile` chezmoi data var.

### Sub-pattern 2b: Shell matrix

Almost nobody runs an explicit shell matrix. The implicit shell matrix is "the runner's default shell" plus "whichever shells your dotfiles configure" (bash + zsh + fish if you have them). Only [nivintw/dotfiles](https://github.com/nivintw/dotfiles/blob/main/.github/workflows/ci.yml) goes further: installs `fish`, `bats`, `ripgrep` and runs behavior tests across both.

- **Steal-for-kiyama:** N/A. Kiyama is zsh-only; a matrix here is wasted cells.

### Sub-pattern 2c: Tool / version matrix

[anishathalye/dotbot] is the only verified case of a non-trivial tool-version matrix (9 Python versions). Dotfile repos generally don't pin multiple versions of e.g. neovim or zsh on purpose. mise users (kiyama is one) implicitly get version pinning from `dot_config/mise/config.toml` — `jdx/mise-action@v4` is the standard way to install pinned tools in CI (used by shunk031 and others).

- **Steal-for-kiyama:** YES — adding `- uses: jdx/mise-action@v4 { install: true, cache: true }` to any future CI workflow is a one-liner that exercises the exact same mise resolution kiyama already trusts in the Containerfile Stage 2.

### Sub-pattern 2d: Idempotence matrix

[geerlingguy/mac-dev-playbook](https://github.com/geerlingguy/mac-dev-playbook/blob/master/.github/workflows/ci.yml) runs the playbook twice and asserts the second run has no changes:
```yaml
- run: ansible-playbook main.yml
- run: ansible-playbook main.yml | tee -a ${idempotence}
  tail ${idempotence} | grep -q 'changed=0.*failed=0'
```

- **Catches:** install scripts that always re-do work, scripts that fail on re-run.
- **Misses:** install scripts that are idempotent but slow; first-run-only bugs.
- **Steal-for-kiyama:** STRONG YES. Run `make up` twice and assert the second `dotfiles-entrypoint` is fast / chezmoi apply reports zero changes. Catches `run_once_` vs `run_onchange_` confusion and rbw-unlock side effects. Cheap and high signal.

## Pattern 3: Lint / static checks

| Check | Tool | Example repo | Purpose / form |
|---|---|---|---|
| Shell lint | `shellcheck` via `ludeeus/action-shellcheck@master` | [kedwards/dotfiles](https://github.com/kedwards/dotfiles/blob/master/.github/workflows/validate.yml), [alrra/dotfiles](https://github.com/alrra/dotfiles/blob/main/.github/workflows/macos.yml), [mswell/dotfiles](https://github.com/mswell/dotfiles/blob/master/.github/workflows/ci.yml), [utouto97](https://github.com/utouto97/dotfiles/blob/main/.github/workflows/check.yml), [Chamal1120](https://github.com/Chamal1120/dotfiles/blob/main/.github/workflows/lint.yml) | One-line action; pre-installed on Ubuntu runners. The most widespread dotfiles CI check. |
| Shell lint with scandir matrix | `shellcheck` + `matrix.scandir` | [ryankanno/dotfiles](https://github.com/ryankanno/dotfiles/blob/main/.github/workflows/shellcheck.yml) | `matrix: scandir: ['./scripts', './dot_claude/scripts', './dot_githooks']` — fan-out per shell-script subtree |
| Shell format | `shfmt -d .` (or `reviewdog/action-shfmt`) | [kedwards](https://github.com/kedwards/dotfiles/blob/master/.github/workflows/validate.yml), [shunk031](https://github.com/shunk031/dotfiles) | `-d` exits non-zero on diff; `reviewdog` posts PR comments. |
| GH Actions workflow lint | `actionlint` | [twpayne/chezmoi](https://github.com/twpayne/chezmoi/blob/master/.github/workflows/main.yml) line 397 | Catches broken `uses:` / `with:` early. |
| Editorconfig | `editorconfig-checker` | twpayne/chezmoi | Cross-platform whitespace + line-ending checks. |
| YAML lint | `yamllint` | [Chamal1120/dotfiles](https://github.com/Chamal1120/dotfiles/blob/main/.github/workflows/lint.yml) | Useful for chezmoi YAML data files. |
| Markdown lint | `markdownlint-cli2-action` / `markdownlint` | twpayne/chezmoi, alrra | Doc hygiene. |
| TOML format | `taplo fmt --check` | [kedwards](https://github.com/kedwards/dotfiles/blob/master/.github/workflows/validate.yml), [Chamal1120](https://github.com/Chamal1120/dotfiles/blob/main/.github/workflows/lint.yml) | Lints `tools.toml` style files. **Directly relevant** — kiyama has `containers/dependencies/tools.toml`. |
| Lua lint | `selene` | kedwards | nvim config |
| Lua format | `stylua --check` | kedwards, utouto97 | nvim config |
| Secrets scan | `gitleaks/gitleaks-action@v2` | [williamzujkowski/machine-rites](https://github.com/williamzujkowski/machine-rites/blob/main/.github/workflows/ci.yml) | Block accidental secret commits. **Directly relevant** for kiyama (templates/rbw_password leak history). |
| Pre-commit aggregator | `pre-commit/action@2c7b3805` | williamzujkowski/machine-rites | Runs the repo's `.pre-commit-config.yaml` in CI to enforce parity with local hooks. |
| chezmoi self-check | `chezmoi doctor` | [upnt/dotfiles](https://github.com/upnt/dotfiles/blob/main/.github/workflows/healthcheck.yml), [oliverdding/dotfiles](https://github.com/oliverdding/dotfiles/blob/main/.github/workflows/check.yml), twpayne/chezmoi entrypoint | "Check for potential problems" (per chezmoi docs); reports status of encryption tools, template engine, git. |
| chezmoi dry-run apply | `chezmoi init --apply --dry-run --source .` | [kedwards/dotfiles](https://github.com/kedwards/dotfiles/blob/master/.github/workflows/validate.yml), [williamzujkowski/machine-rites](https://github.com/williamzujkowski/machine-rites/blob/main/.github/workflows/ci.yml) | Renders all templates + simulates apply without touching anything. **Cheapest meaningful chezmoi gate.** |
| chezmoi template render | `chezmoi execute-template --init --override-data '{...}' < file.tmpl` | [edjchapman/dotfiles](https://github.com/edjchapman/dotfiles/blob/main/.github/workflows/audit.yml) | Targeted template rendering test with synthetic data; runs without vault. |
| chezmoi state verify | `chezmoi verify` | Documented but not seen in surveyed CI | "Exits 0 if all targets match target state, else 1" — meant for post-apply assertion, not CI. |

## Pattern 4: Bats / shell test frameworks

bats-core is the consensus framework for asserting *post-install state* in dotfiles. Three concrete patterns observed:

- **In-CI install of bats-core from source, then run `.bats` files:**
  [pragmaticivan/dotfiles](https://github.com/pragmaticivan/dotfiles) ubuntu.yaml:
  ```yaml
  - name: Install latest bats-core
    run: |
      tmp_dir=$(mktemp -d /tmp/bats-core-XXXXX)
      git clone --depth 1 https://github.com/bats-core/bats-core.git "${tmp_dir}"
      cd "${tmp_dir}" && sudo ./install.sh /usr/local
  - name: Test file existence
    run: |
      cd $(chezmoi source-path)/../
      bats tests/files/common.bats
      bats --filter-tags "ubuntu,!ubuntu:${OTHER_SYSTEM}" \
        --print-output-on-failure tests/files/ubuntu.bats
  ```
  Test files: `tests/files/common.bats`, `tests/files/macos.bats`, `tests/files/ubuntu.bats`. Representative assertions:
  ```bats
  @test "[common] configuration files exist" {
    files_exists=( "${HOME}/.zshrc" "${HOME}/.config/starship.toml"
                   "${HOME}/.config/nvim/init.lua" )
    for file in "${files_exists[@]}"; do [ -f "${file}" ]; done
  }
  @test "[common] verify git configuration" {
    run git config --list ; [ "$status" -eq 0 ]
  }
  ```

- **Bats inside a Docker image** (richer fixture isolation):
  [richhaase/plonk](https://github.com/richhaase/plonk/blob/main/.github/workflows/ci.yml) has an "Integration Tests (BATS)" job that does `docker/build-push-action` then `docker run --rm plonk-test:latest all` — the container entrypoint runs the bats suite.

- **Native bats package install, run from `tests/`** (kiyama-adjacent: shunk031 uses `bats` package from apt + tests/files/*.bats with `--filter-tags`).

- **Setup-via-action:** [bats-core/bats-action](https://github.com/bats-core/bats-action) — single `uses: bats-core/bats-action@4.0.0` installs bats + libs:
  ```yaml
  - uses: bats-core/bats-action@4.0.0
    id: setup-bats
  - env: { BATS_LIB_PATH: ${{ steps.setup-bats.outputs.lib-path }} }
    run: bats test/my-test.bats
  ```

- **Negative finding:** I did not see `shunit2` or `bash_unit` used in the surveyed dotfile repos; bats has won this niche.

Filter-tags is the load-bearing detail for kiyama's profile axis: a single `tests/files/manjaro.bats` can carry `# bats test_tags=manjaro:workstation,manjaro:container` and the workflow does `bats --filter-tags "manjaro,!manjaro:workstation"` in the container job.

## Pattern 5: Dry-run / diff-only verification

- **`chezmoi diff` / `chezmoi init --apply --dry-run`:** kedwards/dotfiles validate.yml uses `chezmoi init --apply --dry-run --source .` as its entire chezmoi gate. machine-rites uses `chezmoi --source ./.chezmoi apply --dry-run`. arumakan1727's `render-macos` job does `chezmoi apply --dry-run --verbose --source="$PWD"`. **All three** treat dry-run as the cheap-CI replacement for a real apply, on the theory that "if the rendered output is structurally fine, the real apply will be fine."
  - **Catches:** template syntax, missing data, missing source files.
  - **Misses:** `run_` script side effects, runtime tool calls inside chezmoi scripts, anything that only fires under `chezmoi apply` for real.

- **`chezmoi verify` (post-apply state check):** documented to "exit 0 if all targets match target state, else 1." Designed for post-apply assertion. Not commonly seen in CI, but trivial to add as the *final* step after a real apply — would catch drift between rendered intent and apply outcome.

- **`chezmoi doctor`:** sub-second pre-flight check. Used by upnt/dotfiles healthcheck.yml on both Linux and Windows; used by twpayne's own entrypoint as the first command (`go tool chezmoi doctor || true`). Tolerates failure deliberately because it's diagnostic, not a gate — but a strict CI can drop the `|| true`.

- **`stow -n` (no-op simulation):** mentioned in stow docs as the dry-run mode. Not seen in surveyed dotfile CI because stow-based dotfiles tend not to have CI in the first place.

- **`nix flake check`:** Mic92's pattern, covered in 1d.

- **`yadm diff`:** referenced in the broader dotfiles ecosystem but no CI examples surfaced in this survey; consider this "needs verification."

- **`ansible-playbook --check --diff`:** geerlingguy's playbook achieves the same effect via the idempotence-grep pattern (Pattern 2d) rather than `--check`.

## Pattern 6: Secret injection in test/CI environments

When CI has no vault, the surveyed maintainers fall into five buckets:

1. **GitHub Actions Secrets + env injection at the install boundary.** [shunk031/dotfiles ubuntu.yaml]:
   ```yaml
   - uses: webfactory/ssh-agent@v0.10.0
     with: { ssh-private-key: ${{ secrets.PRIVATE_DOTFILES_PRIVATE_DEPLOY_KEY }} }
   - env:
       EMAIL_ADDRESS: ${{ secrets.EMAIL_ADDRESS }}
       SYSTEM: ${{ matrix.system }}
       GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
     run: printf "${EMAIL_ADDRESS}\n${SYSTEM}\n" | bash -c "$(wget -qO - $URL)"
   ```
   The `printf` pipes interactive prompts to setup.sh; SSH agent serves a deploy key for the private chezmoi data submodule. Mechanism = "treat CI as a special user with its own keypair."

2. **CHEZMOI_GITHUB_TOKEN-style env passthrough.** twpayne/chezmoi's docker test.sh whitelists exactly four env vars: `CHEZMOI_GITHUB_ACCESS_TOKEN`, `CHEZMOI_GITHUB_TOKEN`, `GITHUB_ACCESS_TOKEN`, `GITHUB_TOKEN`. Tests that need API access find it; tests that don't, don't.

3. **Skip secret-dependent steps via env flag.** Common idiom in chezmoi `.chezmoiscripts/run_once_*`: `{{- if env "CI" }}exit 0{{ end -}}` at the top. Lets the same script behave differently in CI vs. real-host. **No verified example in the surveyed sample**; this is folklore from the chezmoi user-guide rather than a quoted file.

4. **gitleaks pre-commit / CI to *prevent* the inverse problem.** williamzujkowski/machine-rites uses `gitleaks/gitleaks-action@v2`. Not a vault-injection pattern but the natural pairing — "no secrets in CI, also no secrets in repo."

5. **No secret handling at all** — the dominant pattern. anishathalye/dotfiles' `HOME=~/dotfiles-install-dir ./install` exercises only what works without secrets. Anything secret-dependent silently does nothing in CI.

- **BuildKit `--mount=type=secret` in test workflows:** kiyama already does this (the bw-id/bw-secret/bw-pw mounts). The surveyed dotfile-CI sample does **not** show BuildKit secret mounts in test workflows; kiyama's approach is unusual in this group and inherited from server-side build patterns rather than dotfile community practice. The closest peer is the chezmoi project's own CI passing `CHEZMOI_GITHUB_TOKEN` as a `--env`, which is much weaker.

- **Mocking the password-manager CLI:** No verified example. Most maintainers skip secret-touching steps in CI rather than mock rbw / op / bw.

- **Pre-populated GPG/SSH test keys:** webfactory/ssh-agent (above) is the canonical SSH path. For GPG, [shunk031/dotfiles macos.yaml] has `git config --global commit.gpgsign false` as the explicit "disable in CI" pattern — i.e. side-step rather than inject.

## Gap Analysis for kiyama's setup

Honest reading: kiyama's *container build* is more sophisticated than the dotfile-community norm (BuildKit secrets, vault-rotation OCI label, two-stage with sealed apply, named-secret rbw runtime, pinentry shim). The **validation surface around it** is thin compared to the chezmoi-CI subset of the field.

| Pattern | kiyama has it? | Worth adding? | Note |
|---|---|---|---|
| Podman sandbox build | **YES** (Containerfile, multi-stage, BuildKit secrets) | n/a | Best-in-class in surveyed sample. |
| Smoke verify after build | PARTIAL — `make verify` checks id/sudo/tools/mount + `verify-deps` drift gate | YES expand | Current verify checks command *presence* (`command -v git stow zsh nvim ...`) but not behavior. No `zsh -i -c exit`, no `nvim --headless +qa`, no `chezmoi doctor`, no `chezmoi verify` post-apply, no GPG/SSH/rbw probe. |
| `chezmoi doctor` in verify | NO | YES | One line. Strong signal (encryption tools, git, template engine). Already runs cleanly inside the container per the design — surface the result. |
| `chezmoi verify` post-apply | NO | YES | Asserts apply actually converged to target state. Trivial to add to entrypoint or `make verify`. |
| `chezmoi apply --dry-run` from host | NO | YES | A host-side sanity check that doesn't require building the container at all. Catches template breakage in seconds. |
| `chezmoi execute-template --init` smoke | NO | MAYBE | kiyama has few templates; payoff is narrow. Useful if the GPG/git/zshenv templates become more dynamic. |
| GitHub Actions matrix | **NO** (FF-only, local-only repo per hard constraint) | NO at GH; YES as local Makefile target | The `gh push` path is permanently closed. But the *idea* of a distro × profile matrix can run locally via `make verify DISTRO=archlinux PROFILE=ci`. See steal #2. |
| Multi-distro Containerfile fan-out | NO (Manjaro only) | YES (low priority) | Add `Containerfile.arch`, `Containerfile.endeavouros` to catch divergence inside the Arch family. The structural change to `make verify` is small. |
| `act` for local CI | NO | NO | The negative finding above stands — `act` is not a dotfiles-community standard, and it adds tooling weight for no gain over a plain Makefile target. |
| bats smoke tests | NO | **YES — highest leverage** | This is the gap between "image built" (current floor) and "image actually configured the way I think." Pattern 4 is well-trodden; pragmaticivan/shunk031 give a direct template. |
| Idempotence assertion | NO | YES | Cheap (run `make up`-equivalent twice, grep for changes). Would have caught the rbw-runtime-dir bootstrap and run-once/run-onchange confusion noted in docs/issues. |
| shellcheck on `containers/scripts/` | NO | YES | The runtime entrypoint and build installers are pure shell. shellcheck via ludeeus's action is one-liner; runs as a host-side Make target too. |
| shfmt on shell scripts | NO | YES (with -d) | Catches formatting drift; same effort cost as shellcheck. |
| taplo on `tools.toml` | NO | YES | Format gate on the source-of-truth file that `gen-deps` reads. |
| gitleaks pre-commit / make target | NO | **YES** | Direct fix for the `templates/` leak class memorialised in commit `e45d5df`. Cheap insurance. |
| Pre-commit framework | NO | OPTIONAL | Adds another tool to install. Could replace it with a `make lint` Makefile target that runs shellcheck + shfmt + taplo + gitleaks. |
| Drift gate for generated files | **YES** (`verify-deps` regen + git diff) | n/a | Already a strong pattern — most surveyed repos do not have an equivalent. |
| Vault-rotation OCI label + prune | **YES** (`bake.rotate-after`, `prune-expired`) | n/a | Not seen anywhere in the surveyed dotfile field. Domain-specific to kiyama. |
| BuildKit `--secret` for vault | **YES** | n/a | Also not seen in the dotfile field. Inherited from server CI patterns and stronger than the dotfile norm. |
| Multi-arch image push (arm64) | NO | OPTIONAL | sainnhe does it via buildah-build. Useful only if kiyama plans pi.dev as a real target (currently secondary). |

### Honest critique

Three places where kiyama is **behind the better-curated peers (shunk031, kedwards, pragmaticivan)**:

1. **No behavioral assertions.** `make verify`'s `command -v` is the dotfile-CI equivalent of testing that a function imports — it doesn't prove the install converged. The right next step is a bats suite of file-exists / config-set / smoke-run assertions runnable inside the container.

2. **No host-side lint gate.** Every comparable chezmoi-using dotfiles repo with CI runs shellcheck on its install scripts. Kiyama's `containers/scripts/build/` and `containers/scripts/runtime/` are larger and more security-sensitive than most peers — and they're un-linted.

3. **No second-run / idempotence check.** Issues like `docs/issues/2026-06-26-rbw-runtime-dir-bootstrap.md` and `2026-06-26-gpg-agent-config-reload.md` are exactly the kind of "second run breaks" defects that the geerlingguy pattern catches automatically. Right now they're caught by re-running by hand and noticing a behavior change.

Three places where kiyama is **ahead**:

1. Vault rotation is a real, labeled, prunable concept. No surveyed dotfile repo does this.
2. BuildKit secrets for the privileged stage are gated and audited. Surveyed dotfile peers either don't have a vault or pass plaintext env via GH Secrets.
3. The two-stage apply boundary (apply → tools) with the explicit no-cache-mount invariant is more disciplined than any of the surveyed dotfile Dockerfiles, which are single-stage.

## Top 5 actionable steals

Ranked by signal-per-hour-of-work:

1. **Add `tests/*.bats` + a bats step to `make verify`.** Adopt pragmaticivan/shunk031's structure: `tests/files/common.bats` (file existence, git config, zsh -i -c exit, nvim --headless +qa, `chezmoi doctor`, `chezmoi verify`) and `tests/files/manjaro.bats` (paru list, sudoers entry, GNUPGHOME points where chezmoi rendered it). Wire it as `make verify` step running `podman exec dotfiles-manjaro bats /tmp/tests/*.bats`. Cost ~1 evening; converts `make verify` from presence to behavior. Catches the entire class of "apply succeeded but produced the wrong state."

2. **Idempotence check in `make verify`.** Add a `verify-idempotent` target: `make up && podman exec dotfiles-manjaro dotfiles-entrypoint --re-apply 2>&1 | tee log && grep -q '0 changes' log`. Mirrors the geerlingguy `changed=0` grep. Five lines of Makefile. Would have surfaced several issues already in `docs/issues/`.

3. **`make lint` target running shellcheck + shfmt + taplo + gitleaks.** Same hosting as `make verify`/`verify-deps`. Use the actual binaries (already host-installed via pacman), no GitHub action wrappers needed. shellcheck on `containers/scripts/runtime/dotfiles-entrypoint` and `containers/scripts/build/install-*` is the highest-value subset. gitleaks scan of the working tree as an extra `make lint-secrets` target directly addresses the `e45d5df`-class leak.

4. **`chezmoi doctor` + `chezmoi verify` as the final two lines of `dotfiles-entrypoint` (or `make verify`).** Both are sub-second, both have meaningful exit codes. `doctor` reports encryption/git/template-engine health (would catch a pinentry-shim regression); `verify` asserts the rendered $HOME matches chezmoi source state (would catch a partial apply). Drop the `|| true` from `verify` so failures gate.

5. **Host-side `make dry-run` using `chezmoi apply --dry-run --source $PWD`.** Lets kiyama validate template + script syntax in <10 s on the host *without* building the container or unlocking the vault. The kedwards/williamzujkowski pattern. Make it a pre-commit-style local guard; doesn't violate the no-host-apply hard constraint because `--dry-run` doesn't write.

Lower-priority but worth recording:
- A second Containerfile (`Containerfile.arch`) so `make verify DISTRO=arch` exercises pure-Arch behavior. Catches Manjaro-only assumptions before they ship.
- Multi-arch `buildah-build` if pi.dev ever stops being a secondary target.
- `chezmoi execute-template --init` against synthetic data for the few real templates (`dot_zshenv`, anything under `dot_config/git/`), modeled on edjchapman's audit.yml. Lets templates be validated without rbw.

What to *not* steal: GitHub Actions matrices wholesale (blocked by FF-only constraint), `act` (no community traction, no marginal value over make), Nix flakes wholesale (would invert the stack), Codespaces/devcontainer (no host-target use case).

---

# Part 4 — Declarative Dotfiles: Nix / home-manager / Friends

Included for completeness: this is the school that gets *typed compile-time validation* — the one thing chezmoi + podman fundamentally cannot give. Sources: official `home-manager` manual + module source tree, `nix-darwin/nix-darwin` README, `Mic92/sops-nix` and `ryantm/agenix` READMEs, the public configs listed below, Guix manual, and Garnix / magic-nix-cache docs.

## home-manager

### Core idea

`home-manager` is a Nix-based per-user configuration manager. You describe your `$HOME` as a value of type `homeConfiguration` — packages to install, dotfiles to render, services to run under your user — and `home-manager switch` realises that value as a Nix store path, then atomically swaps symlinks from `~/.config/...`, `~/.local/share/...`, etc. into the new generation. Switching is transactional: success makes the new generation current, failure leaves the previous one untouched, and `home-manager generations` plus `home-manager switch --switch-generation N` give rollback. The same configuration can live as a NixOS module (inside `nixosConfigurations.<host>`) or stand-alone on a foreign distro (Arch, Manjaro, Ubuntu, macOS) backed only by a single-user or multi-user Nix install.

### Typical config shape

```nix
{ pkgs, ... }: {
  home.username      = "kiyama";
  home.homeDirectory = "/home/kiyama";
  home.stateVersion  = "24.11";

  home.packages = with pkgs; [ ripgrep fd jq podman-compose ];

  programs.git = {
    enable    = true;
    userName  = "kiyama";
    userEmail = "k.kiyama117@gmail.com";
    delta.enable = true;
    extraConfig = {
      init.defaultBranch = "main";
      pull.rebase        = true;
    };
    includes = [{ path = "~/.config/git/work.inc"; condition = "gitdir:~/work/"; }];
  };

  programs.zsh = {
    enable                = true;
    enableCompletion      = true;
    autosuggestion.enable = true;
    syntaxHighlighting.enable = true;
    shellAliases = { ll = "eza -l"; gs = "git status"; };
    initExtra = ''eval "$(zoxide init zsh)"'';
  };

  programs.starship.enable = true;
  programs.direnv          = { enable = true; nix-direnv.enable = true; };
  programs.atuin           = { enable = true; flags = [ "--disable-up-arrow" ]; };

  services.gpg-agent = {
    enable          = true;
    enableSshSupport = true;
    pinentry.package = pkgs.pinentry-tty;
  };
}
```

Three things distinguish this from a chezmoi template: (a) options are *typed* — `programs.git.userName` is `nullOr str`, so a typo in the attribute name fails evaluation, not at apply time; (b) `pkgs.pinentry-tty` is a build-time reference, so a missing dependency surfaces before any file is written; (c) there is no "render template" step — the dotfile is a derivation that depends on `pkgs.git`, and the activation script either succeeds or doesn't run at all.

### What categories does it manage?

The `modules/programs/` tree currently ships ~500 modules. Representative slice:

- **Shells & prompts**: `programs.bash`, `programs.zsh`, `programs.fish`, `programs.nushell`, `programs.starship`, `programs.oh-my-posh`, `programs.carapace`
- **Editors**: `programs.neovim`, `programs.helix`, `programs.emacs`, `programs.vscode`, `programs.cursor`, `programs.codex`, `programs.claude-code`
- **Terminals & multiplexers**: `programs.alacritty`, `programs.kitty`, `programs.wezterm`, `programs.foot`, `programs.ghostty`, `programs.tmux`, `programs.zellij`
- **VCS & code review**: `programs.git`, `programs.gh`, `programs.jujutsu`, `programs.lazygit`, `programs.darcs`, `programs.delta`, `programs.difftastic`, `programs.diff-so-fancy`
- **Browsers**: `programs.firefox`, `programs.chromium`, `programs.brave`, `programs.qutebrowser`, `programs.chawan`
- **Productivity / nav**: `programs.fzf`, `programs.zoxide`, `programs.atuin`, `programs.broot`, `programs.bat`, `programs.eza`, `programs.bottom`, `programs.btop`, `programs.autojump`
- **Mail / chat**: `programs.aerc`, `programs.alot`, `programs.afew`, `programs.thunderbird`, `programs.neomutt`
- **Secrets & auth**: `programs.gpg`, `programs.ssh`, `programs.password-store`, `programs.browserpass`, `programs.rbw`, `programs._1password`, `programs.bitwarden-cli`
- **Dev envs**: `programs.direnv`, `programs.devenv`, `programs.bun`, `programs.cargo`, `programs.go`, `programs.java`
- **System glue / linux**: `services.gpg-agent`, `services.ssh-agent`, `services.syncthing`, `services.dunst`, `services.kanshi`, `services.swayidle`, `wayland.windowManager.hyprland`, `xdg.mimeApps`

Each module typically exposes (1) `enable`, (2) a handful of high-level options corresponding to the program's important config keys, and (3) one or more escape hatches such as `extraConfig`, `extraInit`, or a fully free-form attrset that is serialised to TOML/INI/YAML.

### Secret handling

`home-manager` itself stores config in the world-readable Nix store, so secrets cannot live in `programs.foo.password = "..."` form. Three encrypted-at-rest options exist:

- **`sops-nix`** (Mic92) — encrypts a single YAML/JSON/INI file with `sops` using **age or GPG** (plus AWS/GCP/Azure/Vault KMS), and on activation decrypts named keys into `/run/secrets/<name>` (NixOS) or a per-user runtime dir (home-manager module). Strength: multi-recipient YAML lets you keep one file per host with many decryptors, and KMS support is real. Cost: sops + key-rotation tooling is its own workflow.
- **`agenix`** (ryantm, based on sops-nix) — age only, one `.age` file per secret. Decryptors are SSH host keys (or user keys), so existing `id_ed25519` infrastructure works without extra GPG ceremony. Smaller surface area, easier to audit, but no KMS and no multi-key-per-file ergonomics.
- **`git-crypt` / `pass` / external secret manager** — used when the secret is consumed by a program that already understands it (e.g. `programs.password-store` + Bitwarden via `programs.rbw`). This is what kiyama is doing today on the host side.

For a single-machine setup, agenix is the lower-friction choice; sops-nix becomes worth it once there are several hosts with overlapping decryptor sets, or when CI needs to inject secrets via cloud KMS.

### Verification commands

| Command | What it catches |
|---|---|
| `nix flake check` | Flake outputs evaluate, every derivation declared in `checks.<system>.*` builds, NixOS/home-manager configs type-check, overlays apply. Does *not* run the built programs. |
| `nix build .#homeConfigurations.<user>.activationPackage --dry-run` | Whole user environment evaluates and the closure resolves without actually building. Fast smoke test on a clean clone. |
| `nix build .#homeConfigurations.<user>.activationPackage` | Same, but actually realises every dotfile and every package in the closure — proves "everything I reference exists in nixpkgs at this revision". |
| `home-manager build --flake .#<user>` | Sugar for the above; leaves a `result/activate` script you can inspect without switching. |
| `nixos-rebuild build --flake .#<host>` | System-level analogue. "Build but don't switch" is the canonical pre-deploy validation. |
| `nix flake show` | Surfaces missing outputs / typos in attribute paths. |
| `statix check` + `deadnix` | Lint for anti-patterns and dead bindings (not built in, but standard). |

What none of these catch: whether `programs.zsh.initExtra` actually does the right thing at runtime, whether your `~/.config/foo/bar.toml` is semantically valid to `foo`, or whether a service crashes on startup. A `nix flake check` passing means "the configuration is a well-typed buildable artifact" — strictly stronger than `chezmoi diff` (which only checks template render), strictly weaker than booting a VM and running smoke tests.

## nix-darwin

### Core idea

`nix-darwin` (now maintained at `github.com/nix-darwin/nix-darwin`, moved from LnL7) is the NixOS-style module system applied to macOS. It manages system-level things that aren't a single user's `$HOME`: Homebrew casks via the `nix-homebrew`/`homebrew.*` bridge, LaunchDaemons / LaunchAgents, `/etc` files, system defaults (`system.defaults.dock.autohide = true`), Touch ID for sudo, fonts, PAM. It does *not* replace home-manager; the standard pattern is `darwinConfigurations.<host>` that imports `home-manager.darwinModules.home-manager` and then defines `home-manager.users.<name> = ./home.nix`. One flake, one `darwin-rebuild switch`, both system and user reconfigure atomically.

### Typical config shape

```nix
{ pkgs, ... }: {
  services.nix-daemon.enable = true;
  programs.zsh.enable = true;  # enables /etc/zshrc shim

  homebrew = {
    enable = true;
    casks  = [ "raycast" "ghostty" "orbstack" ];
  };

  system.defaults = {
    dock.autohide        = true;
    NSGlobalDomain.AppleInterfaceStyle = "Dark";
    finder.AppleShowAllExtensions = true;
  };

  security.pam.services.sudo_local.touchIdAuth = true;
}
```

### Verification

`darwin-rebuild build --flake .#<host>` mirrors `nixos-rebuild build`. Same `nix flake check` story.

## NixOS modules for dotfiles

Less relevant to a Manjaro user — this is the path where dotfiles are owned by `/etc/nixos/configuration.nix` and managed via `environment.etc."<path>".text = "..."` or `environment.etc."<path>".source = ./files/.../foo`. You can also embed home-manager as a NixOS module so that `nixos-rebuild switch` reconfigures both layers in one transaction (this is what most NixOS users actually do).

## Public configs to learn from

| Repo | URL | Notable feature |
|---|---|---|
| Misterio77/nix-starter-configs | https://github.com/Misterio77/nix-starter-configs | Two CC0 starter templates (minimal + standard). The "read this first" config for newcomers. |
| mitchellh/nixos-config | https://github.com/mitchellh/nixos-config | macOS host + NixOS-in-VM hybrid. Explicitly *not* a tutorial — useful as a "what does a senior infra engineer actually ship" reference. |
| srid/nixos-config | https://github.com/srid/nixos-config | Flake-parts based; cross-platform (NixOS / nix-darwin / WSL); uses `agenix`; `just`-driven tasks. Good template for a single config across multiple OSes. |
| NotAShelf/nyx | https://github.com/NotAShelf/nyx | Archived Aug 2024 but still cited. Heavy modularization with profiles/roles, declarative theming, BTRFS impermanence, agenix, custom Xanmod kernel — the "over-engineered showcase" end of the spectrum. |
| LongerHV/nixos-configuration | https://github.com/LongerHV/nixos-configuration | Explicitly supports the foreign-distro path (Ubuntu bootstrap), which is the closest analogue to a Manjaro user adopting home-manager. |
| nix-community/home-manager | https://github.com/nix-community/home-manager | Not a config but the source of truth: `modules/programs/`, `modules/services/`, and `tests/` are the canonical reference for what's available. |
| nix-darwin/nix-darwin | https://github.com/nix-darwin/nix-darwin | Same, for macOS modules. |

For a Manjaro/foreign-distro user, the realistic learning path is **Misterio77 (read) → LongerHV (foreign-distro pattern) → srid (cross-platform + agenix)**.

## Declarative non-Nix alternatives

### Guix home

GNU Guix's equivalent of home-manager, configured in Guile Scheme via a `home-environment` record (`home-environment`, `home-bash-configuration`, `home-files-service-type`, etc.). Like home-manager it builds a transactional generation and supports rollback (`guix home roll-back`); like home-manager it runs on foreign distros. The functional model is identical — pure functional package manager, content-addressed store under `/gnu/store`, derivations. Practical differences from home-manager: smaller ecosystem (~hundreds vs thousands of upstream services), Guile instead of Nix-the-language, FSF-aligned channel defaults (no non-free firmware out of the box), and a much smaller community contributing modules. Useful to know exists; not a serious contender for someone already invested in podman + the wider Nix ecosystem.

### Ansible-managed dotfiles

Jeff Geerling's `geerlingguy/dotfiles` is the canonical example, paired with his much larger `geerlingguy/mac-dev-playbook` which uses Ansible to install Homebrew packages, casks, Mac App Store apps, and then runs the dotfile sync. Ansible's model is **idempotent imperative**: each task declares a desired state (`package: name=git state=present`, `lineinfile: ...`, `file: src=... dest=... state=link`) and the task module checks-then-acts. There is no compile-time validation — a typo in a task name fails at execution, missing dependencies surface only when their playbook runs, and there's no notion of a single "build artifact" you can diff. Strengths: zero buy-in beyond Python+SSH, trivially extends to remote hosts and multi-machine fleets, huge module ecosystem (Galaxy). Weaknesses for personal dotfiles: re-run cost is high, drift between "what the playbook says" and "what the laptop is" accumulates silently, secrets via `ansible-vault` are workable but not store-encrypted.

### chezmoi (as "lite declarative")

chezmoi sits between raw `stow`/symlinks and home-manager. It's declarative about *file contents* (templates render deterministically from a state file + secret backend), idempotent on `chezmoi apply`, and has first-class support for `run_once_`, `run_onchange_`, `run_after_` script hooks plus encrypted source files via age/gpg. What it is *not* declarative about: installed packages (kiyama's `run_after_install_*` is exactly the imperative escape hatch the templates can't express), the state of services, or the system as a single value. The contract chezmoi enforces is "the rendered tree under `~/` matches what `chezmoi diff` says" — a real and useful guarantee, but one layer of validation rather than home-manager's whole-closure one.

## Verification & CI patterns

- **`nix flake check`** — evaluates every flake output, builds everything in `checks.<system>.*`, type-checks NixOS / home-manager configs. Catches: typos in option paths, missing inputs, broken overlays, untyped attribute values, derivation-build failures. Misses: runtime correctness, semantic validity of rendered config files, network-only side effects.
- **`home-manager build` / `nixos-rebuild build` / `darwin-rebuild build`** — "build but don't switch" is the canonical pre-merge gate. Cheaper than a full switch, strictly stronger than `nix flake check` because it forces realisation of the activation derivation.
- **CI: Garnix** (`garnix.io`) — Nix-native CI as a GitHub App. Reads `flake.nix`, builds every `checks.*` and `packages.*` across the systems you declare, reports as GitHub Checks, caches outputs on their substituter for free, and offers preview-deploys for NixOS configs.
- **CI: `DeterminateSystems/magic-nix-cache-action`** — drop-in GitHub Actions step that funnels Nix store I/O through GHA's cache, cutting rebuild cost 30-50% without paying for a Cachix plan.
- **CI: Cachix** — the long-established binary cache service. Pay-per-storage but lets you push artifacts from any runner and consume them from any machine.
- **Reproducibility caveats** — the closure is only as pure as its inputs.
  - **IFD (Import From Derivation)** — evaluating one derivation requires building another first. Breaks parallel evaluation, breaks Hydra, breaks most CI assumptions. `nix flake check --no-allow-import-from-derivation` is the recommended guard.
  - **`builtins.fetchurl` / `builtins.fetchGit` without a hash** — impure: re-evaluating later can return different content.
  - **Impure overlays** — overlays that read env vars or run shell commands at eval time.
  - **`--impure` flag** — convenient escape hatch, regularly abused; once a flake requires it, the lock file's reproducibility promise is over.
  - **`home.activation` scripts** — arbitrary bash run at switch time. Same imperative-tail problem as chezmoi's `run_after_` scripts; they just live inside a more rigorous frame.

So Nix's purity is a default-strong contract with named, lintable holes — not an absolute.

## What chezmoi + podman gets that pure-Nix doesn't (and vice versa)

| Property | chezmoi + podman | home-manager |
|---|---|---|
| Idempotent re-apply | Yes — `chezmoi apply` is the contract | Yes — every `switch` is a fresh generation, rollback built in |
| Pure-function semantics | No — templates render deterministically but `run_after_install_*` is arbitrary bash | Default yes (modulo IFD / `--impure` / `home.activation`) |
| Catches missing dep at "compile time" | No — pacman/rbw failures surface during apply | Yes — `home-manager build` fails if `pkgs.foo` doesn't exist at the pinned revision |
| Typed config validation | No — Go template + YAML, errors at render time | Yes — module options have NixOS types; typos fail evaluation |
| Works without buying into Nix store | Yes — plain pacman + dotfiles | No — requires `/nix` (single- or multi-user install), one-time root for daemon |
| Easy to debug template render | Yes — `chezmoi diff` / `chezmoi cat` | Harder — `nix eval` + `nix log`, learning curve, error messages are notorious |
| Real-OS smoke test | Implicit — apply lives on the actual host | `nixos-rebuild build-vm` for NixOS; for foreign-distro home-manager you still need the host |
| Atomic activation + rollback | Partial — `chezmoi apply` writes file-by-file; no system-wide rollback | Yes — generation symlink swap, `home-manager generations` + `switch-generation N` |
| Secret rotation story | rbw + age, externally orchestrated (your current path) | agenix/sops-nix: rotation = re-encrypt + commit + `switch` |
| Works with podman/OCI containers | Native — that's the whole stack you already built | Possible (`virtualisation.podman` is NixOS-only; on foreign distro you'd still use system podman) |
| Multi-host fleet management | Per-host `chezmoi init` + git pulls | Per-host `flake.nix` outputs, deploy via `nixos-rebuild --target-host` or deploy-rs |
| Learning cost | Low — Go templates + a CLI | High — Nix-the-language, the module system, flakes, store semantics |
| Rolling-distro friendliness | Good — pacman moves under you, you don't care | Mixed — `nixpkgs` pin is independent of pacman; you maintain two package universes |
| Auditability of "what's actually installed" | `pacman -Qet` + your inventory script | `nix-store -qR ~/.local/state/nix/profiles/home-manager` — exact closure, content-addressed |

## Verdict for kiyama

Stay with chezmoi + podman as the primary spine; do **not** migrate. Your current setup already gets you the two things that matter most — content-addressed reproducibility for the *runtime* environments (the podman images, which are the actual security boundary) and a versioned templating layer for the *configuration* surface. home-manager's compile-time-validation win is real but narrow: it would catch typos in `programs.git.userName` that your current `run_after_install_*` would never see, and not much else that you don't already have a story for. The cost — learning the Nix language well enough to debug eval errors, maintaining two package universes on a rolling Arch base, giving up the `pacman -S` muscle memory — is large for a single-user single-host setup.

Where it would be worth a small experiment: add a side `flake.nix` that exposes a `homeConfigurations.kiyama` for *one* well-defined slice (e.g. just the dev-shell + git + zsh modules) and run `nix flake check` in CI; this gives you the typed-validation guarantee for the part of your config most likely to silently rot, without committing to migrate the whole tree. If you ever add a second host or onboard a second user, re-evaluate — that's the inflection point where home-manager's atomic-multi-host story actually pays for its tax.

---

# Appendix — Aggregated Repo Index

Sorted alphabetically by owner; one line each.

| Repo | Manager | Why surveyed |
|---|---|---|
| alrra/dotfiles | custom (looks-like-stow) | shellcheck CI |
| anishathalye/dotbot | dotbot (own tool) | 27-cell OS×Python matrix |
| anishathalye/dotfiles | dotbot | minimal HOME-redirect CI |
| arumakan1727/dotfiles | chezmoi | render-macos dry-run job |
| babarot (b4b4r07)/dotfiles | Makefile + `afx` | Japanese long-tenured zsh dev |
| budimanjojo/nix-config | Nix + chezmoi hybrid | acknowledges Nix's text-gen weakness |
| caarlos0/dotfiles | shell script | "left Nix, came back to bash" |
| Chamal1120/dotfiles | chezmoi | yamllint + taplo lint workflow |
| ChristianChiarulli/machfiles | stow | every-terminal LunarVim rice |
| cowboy/dotfiles | custom (copy/link/init) | classic three-phase pattern |
| edjchapman/dotfiles | chezmoi | `chezmoi execute-template --init` audit |
| EyesofBucket/dotfiles | shell | HOME-redirect CI |
| felipecrs/dotfiles | chezmoi | numbered run_after_NN-* + .chezmoihooks |
| fufexan/dotfiles | NixOS + home-manager | build-is-the-test |
| geerlingguy/mac-dev-playbook | Ansible | `changed=0` idempotence assertion |
| harperreed/dotfiles | yadm | actively maintained yadm reference |
| holman/dotfiles | custom (topical *.symlink) | "topical dotfiles" pattern source |
| jaagr/dots | stow | polybar author |
| josean-dev/dev-environment-files | stow | dual macOS/Linux WM, modern CLI |
| kedwards/dotfiles | chezmoi | shellcheck + shfmt + taplo + chezmoi dry-run |
| LazyVim/starter | git clone | reference Neovim distribution |
| LongerHV/nixos-configuration | NixOS + home-manager | foreign-distro bootstrap path |
| LukeSmithxyz/voidrice | LARBS shell | non-resumable CSV installer |
| mathiasbynens/dotfiles | bootstrap.sh + brew.sh | canonical macOS bash reference |
| Mic92/dotfiles | Nix flake + Hercules CI | hermetic build = test |
| mitchellh/nixos-config | Nix + Makefile lifecycle | senior-infra-engineer reference |
| Misterio77/nix-config | Nix + sops + Hydra | mainstream multi-host Nix template |
| Misterio77/nix-starter-configs | Nix | starter templates |
| mswell/dotfiles | shell | shellcheck CI |
| nicknisi/dotfiles | custom `dot` CLI | bespoke subcommand router |
| nivintw/dotfiles | shell | fish+bash bats matrix |
| nix-community/home-manager | Nix | source of truth |
| nix-darwin/nix-darwin | Nix | macOS modules |
| NotAShelf/nyx | Nix | over-engineered showcase |
| oliverdding/dotfiles | chezmoi | `chezmoi doctor` healthcheck |
| omerxx/dotfiles | stow + nix-darwin | Aerospace/Ghostty/Zellij rice |
| paulirish/dotfiles | shell | fish + JS tooling |
| pragmaticivan/dotfiles | chezmoi | bats + system=[server,client] matrix |
| renemarc/dotfiles | chezmoi | minimal flat layout |
| richhaase/plonk | tool | bats-in-docker job |
| rio/dotfiles | chezmoi + devcontainer | postCreateCommand=chezmoi init --apply |
| ryankanno/dotfiles | chezmoi | shellcheck scandir matrix |
| sainnhe/dotfiles | Containerfile + buildah | multi-arch ghcr push (no test) |
| shunk031/dotfiles | chezmoi | bats + Dockerfile + system=[server,client] |
| srid/nixos-config | Nix flake-parts | cross-platform + agenix |
| thoughtbot/dotfiles | rcm | Rails consultancy starter |
| TheTrueZeroTwo/DotFiles | shell | 6-distro matrix on Gitea |
| twpayne/chezmoi (project) | Go | docker test.sh distro dispatcher |
| twpayne/dotfiles | chezmoi | author's own; per-OS script subdirs |
| typecraft-dev/dotfiles | stow-like | side-by-side WM rice |
| upnt/dotfiles | chezmoi | Linux+Windows healthcheck |
| utouto97/dotfiles | shell | `zsh -i -c exit` + `nvim --headless` probes |
| williamzujkowski/machine-rites | chezmoi | gitleaks + pre-commit + `chezmoi apply --dry-run` |
| xero/dotfiles | stow | clean per-package layout |
| yadm-dev/yadm | tool | yadm reference |
| yutkat/dotfiles | Nix + home-manager + apt/pacman | true multi-distro, closest to kiyama in spirit |
