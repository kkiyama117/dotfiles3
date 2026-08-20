#!/usr/bin/env bash
# AI quick-query of the clipboard (latest copy/yank), end-4 style but via
# OpenAI-compatible APIs. Ollama Cloud primary, OpenRouter fallback.
# Triggered by a Hyprland keybind; result shown as a notification.
set -u

# Load API keys from the chezmoi-rendered secret store (POSIX `export` lines).
SECRETS="${HOME}/.config/zsh/rc/secrets.zsh"
[ -f "$SECRETS" ] && . "$SECRETS" 2>/dev/null

content=$(wl-paste 2>/dev/null | tr '\n' ' ' | head -c 2000)
if [ -z "$content" ]; then
    notify-send --app-name="AI query" --expire-time=5000 "クリップボードが空です"
    exit 0
fi

SYSTEM_PROMPT='あなたは簡潔なアシスタントです。与えられた内容を100文字以内で日本語で説明してください。英語の単語なら意味を、固有名詞なら情報を、数式なら段階的に簡略化してください。分からない場合は「情報なし」とだけ答えてください。'

call_api() {
    # $1=endpoint  $2=api key  $3=model
    curl -s -m 25 -H "Authorization: Bearer $2" -H "Content-Type: application/json" \
        "$1" \
        -d "$(jq -cn --arg m "$3" --arg sys "$SYSTEM_PROMPT" --arg c "$content" \
            '{model:$m,messages:[{role:"system",content:$sys},{role:"user",content:$c}],max_tokens:400}')" \
        | jq -r 'if .error then empty else .choices[0].message.content end' 2>/dev/null
}

# Primary: Ollama Cloud
answer=$(call_api "https://ollama.com/v1/chat/completions" "${OLLAMA_API_KEY:-}" "${AI_QUERY_MODEL:-gpt-oss:20b}")

# Fallback: OpenRouter
if [ -z "$answer" ] && [ -n "${OPENROUTER_API_KEY:-}" ]; then
    answer=$(call_api "https://openrouter.ai/api/v1/chat/completions" "${OPENROUTER_API_KEY:-}" "${AI_QUERY_FALLBACK_MODEL:-openai/gpt-4o-mini}")
fi

if [ -z "$answer" ]; then
    notify-send --app-name="AI query" --expire-time=10000 "AI 応答なし" "両プロバイダとも失敗しました"
    exit 0
fi

# Short single-line selection → use it as the title; otherwise generic title.
if [[ ${#content} -le 30 && "$content" != *$'\n'* ]]; then
    notify-send --app-name="AI query" --expire-time=0 "$content" "$answer"
else
    notify-send --app-name="AI query" --expire-time=0 "AI 応答" "$answer"
fi