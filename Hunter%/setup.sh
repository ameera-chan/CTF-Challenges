#!/bin/sh
set -eu

: "${PORT:=8080}"
: "${FLAG:=CSUFSEC{2f1d2d60-44a1-47bf-95f4-38e2536ca49c}}"
: "${DEBUG_TOKEN:=caput-apri-defero}"
: "${DECOY_TYPE_COUNT:=50000}"

export PORT FLAG DEBUG_TOKEN DECOY_TYPE_COUNT

exec gunicorn \
  --bind "0.0.0.0:${PORT}" \
  --workers 1 \
  --threads 4 \
  --timeout 30 \
  app:app
