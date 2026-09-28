#!/bin/sh
set -eu

: "${BOT_TOKEN_FILE:=/run/starvault/bot_token}"
: "${BOT_HOST:=127.0.0.1:3000}"
: "${APP_HOST:=127.0.0.1:5000}"
: "${PUPPETEER_EXECUTABLE_PATH:=/usr/bin/chromium}"

export BOT_TOKEN_FILE BOT_HOST APP_HOST PUPPETEER_EXECUTABLE_PATH

mkdir -p "$(dirname "$BOT_TOKEN_FILE")"

if [ -n "${BOT_TOKEN:-}" ]; then
    printf "%s" "$BOT_TOKEN" > "$BOT_TOKEN_FILE"
elif [ ! -s "$BOT_TOKEN_FILE" ]; then
    node -e "require('fs').writeFileSync(process.env.BOT_TOKEN_FILE, require('crypto').randomBytes(32).toString('hex'))"
fi

cleanup() {
    kill "$BOT_PID" "$WEB_PID" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

(cd /app/bot && node index.js) &
BOT_PID=$!

(cd /app/web && node app.js) &
WEB_PID=$!

while true; do
    if ! kill -0 "$BOT_PID" 2>/dev/null; then
        wait "$BOT_PID"
        exit $?
    fi

    if ! kill -0 "$WEB_PID" 2>/dev/null; then
        wait "$WEB_PID"
        exit $?
    fi

    sleep 2
done
