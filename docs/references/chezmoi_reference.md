We use `chezmoi` to manage the dotfiles. Below are the commands we use mainly.
For details, see the [chezmoi documentation](https://www.chezmoi.io/docs/).

| Command | Purpose |
| --- | --- |
| `chezmoi init <repo>` | Initialise the source directory from this repository. |
| `chezmoi apply` | Apply the managed dotfiles to `$HOME`. |
| `chezmoi diff` | Show the diff between the source state and the destination. |
| `chezmoi status` | List files whose state differs between source and destination. |
| `chezmoi add <path>` | Add an existing file under `$HOME` to the source directory. |
| `chezmoi edit <path>` | Edit a managed file via its source representation. |
| `chezmoi cd` | Open a shell in the source directory. |
| `chezmoi update` | `git pull` the source and `chezmoi apply` in one step. |


## chezmoi with bitwarden

https://www.chezmoi.io/user-guide/password-managers/bitwarden/#bitwarden-cli
