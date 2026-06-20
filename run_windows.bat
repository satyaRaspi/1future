@echo off
setlocal
cd /d %~dp0
if not exist .venv (
  py -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if "%PORT%"=="" set PORT=8000
echo Starting Life Path Decoder on http://127.0.0.1:%PORT%
python -m uvicorn app.main:app --host 127.0.0.1 --port %PORT%
