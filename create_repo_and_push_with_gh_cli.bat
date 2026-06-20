@echo off
setlocal
cd /d "%~dp0"

echo Life Path Decoder - Create GitHub Repo and Push using GitHub CLI

gh --version >nul 2>&1
if errorlevel 1 (
  echo GitHub CLI is not installed.
  echo Install it from: https://cli.github.com/
  pause
  exit /b 1
)

git --version >nul 2>&1
if errorlevel 1 (
  echo Git is not installed or not available in PATH.
  echo Install Git for Windows first: https://git-scm.com/download/win
  pause
  exit /b 1
)

set /p REPO_NAME=Enter new repo name, default lifepath-decoder: 
if "%REPO_NAME%"=="" set REPO_NAME=lifepath-decoder

if not exist .git (
  git init -b main
)

git branch -M main
git add .
git commit -m "Initial commit - Life Path Decoder v1.3.4" || echo Nothing new to commit.

gh auth status >nul 2>&1
if errorlevel 1 (
  gh auth login
)

gh repo create %REPO_NAME% --private --source=. --remote=origin --push

echo.
echo Done. Repository created and pushed.
pause
