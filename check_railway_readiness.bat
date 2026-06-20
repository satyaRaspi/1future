@echo off
setlocal
cd /d %~dp0

echo Checking Railway-ready files...
if not exist railway.toml (
  echo ERROR: railway.toml missing
  exit /b 1
)
if not exist requirements.txt (
  echo ERROR: requirements.txt missing
  exit /b 1
)
if not exist app\main.py (
  echo ERROR: app\main.py missing
  exit /b 1
)

python -m py_compile app\main.py
if errorlevel 1 (
  echo ERROR: Python compile check failed
  exit /b 1
)

echo Railway readiness check passed.
echo Start command: python -m uvicorn app.main:app --host 0.0.0.0 --port %%PORT%%
