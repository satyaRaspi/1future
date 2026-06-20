@echo off
setlocal
cd /d "%~dp0"

echo Life Path Decoder - GitHub Push Helper

echo.
git --version >nul 2>&1
if errorlevel 1 (
  echo Git is not installed or not available in PATH.
  echo Install Git for Windows first: https://git-scm.com/download/win
  pause
  exit /b 1
)

if not exist .git (
  git init -b main
)

git branch -M main

git status --short

echo.
git add .
git commit -m "Initial commit - Life Path Decoder v1.3.4" || echo Nothing new to commit.

echo.
set /p REPO_URL=Paste your GitHub repo URL, e.g. https://github.com/ssrinivasan13/lifepath-decoder.git: 
if "%REPO_URL%"=="" (
  echo No repo URL entered. Exiting.
  pause
  exit /b 1
)

git remote get-url origin >nul 2>&1
if errorlevel 1 (
  git remote add origin %REPO_URL%
) else (
  git remote set-url origin %REPO_URL%
)

git push -u origin main

echo.
echo Done. Open your GitHub repository to verify the files.
pause
