#!/bin/sh
set -eu

: "${BOT_HOST:=127.0.0.1:3000}"
: "${APP_HOST:=127.0.0.1:5000}"
: "${REDIS_HOST:=127.0.0.1}"
: "${REDIS_PORT:=6379}"
: "${PUPPETEER_EXECUTABLE_PATH:=/usr/bin/chromium}"
: "${FLAG:=ICTF26{this_is_not_the_flag}}"

if [ -z "${SECRET_KEY:-}" ]; then
    SECRET_KEY="$(node -e "process.stdout.write(require('crypto').randomBytes(32).toString('hex'))")"
fi

export BOT_HOST APP_HOST REDIS_HOST REDIS_PORT PUPPETEER_EXECUTABLE_PATH FLAG SECRET_KEY

cleanup() {
    kill "$WEB_PID" "$BOT_PID" "$REDIS_PID" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

redis-server --protected-mode no --save "" --appendonly no &
REDIS_PID=$!

for _ in 1 2 3 4 5 6 7 8 9 10; do
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

(cd /app/bot && node index.js) &
BOT_PID=$!

(cd /app/web && python app.py) &
WEB_PID=$!

while true; do
    if ! kill -0 "$REDIS_PID" 2>/dev/null; then
        wait "$REDIS_PID"
        exit $?
    fi

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
