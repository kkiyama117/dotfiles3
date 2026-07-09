unsetopt promptcr            # Prevent overwriting non-newline output at the prompt

setopt auto_list             # Display a list of possible completions with ^I (when there are multiple candidates for completion, display a list)
setopt auto_menu             # 補完キー連打で順に補完候補を自動で補完
setopt auto_remove_slash     # Automatically remove trailing / in completions

setopt correct               # Auto correct mistakes

setopt list_types            # 補完候補一覧でファイルの種別を識別マーク表示 (訳注:ls -F の記号)
setopt ignore_eof            # Don't logout with C-d
setopt interactive_comments  # コマンドラインでも # 以降をコメントと見なす

setopt no_flow_control       # Do not use C-s/C-q flow control
setopt notify
setopt pushd_to_home         # no pushd argument == pushd $HOME
setopt pushd_ignore_dups     # Delete old duplicates in the directory stack.
setopt path_dirs             # Find subdirectories in PATH when / is included in command name
setopt print_eight_bit       # Through "8-bit" (like the name of Japanese file)

