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
echo "Starting Life Path Decoder DEV mode on http://127.0.0.1:${PORT}"
python -m uvicorn app.main:app --host 127.0.0.1 --port "${PORT}" --reload --reload-dir app --reload-exclude '.venv/*' --reload-exclude 'data/*'
