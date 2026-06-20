#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PORT="${PORT:-8000}"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if command -v lsof >/dev/null 2>&1 && lsof -ti tcp:${PORT} >/dev/null 2>&1; then
  echo "Port ${PORT} is already in use. Stop the old server first:"
  echo "  lsof -ti tcp:${PORT} | xargs kill -9"
  exit 1
fi
echo "Starting Life Path Decoder on http://127.0.0.1:${PORT}"
python -m uvicorn app.main:app --host 127.0.0.1 --port "${PORT}"
