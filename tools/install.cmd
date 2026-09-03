@echo off
rem install.cmd - Future Ministry (Calvin) dept package launcher for Windows (installer v2, Stage0 + package).
rem ASCII ONLY: cmd.exe parses batch files with the OEM code page; UTF-8 Korean here breaks parsing (measured 2026-09-02).
rem Usage:  install.cmd [bootstrap / install / doctor / handle URL / receiver-register / env] [options]
rem         (no subcommand = bootstrap, i.e. double-click)
rem Exit codes come straight from fm.cli: 0 ok / 1 failures / 2 bad args or URL / 10 Javis not installed.
rem Env:    FM_PKG_DIR = use this package root (no clone/pull; CI/dev) - FM_CI=1 = fully non-interactive.
rem Trust:  only the bundled Javis runtime (python3/git). Never system Git, winget, UAC, or user PATH.
setlocal EnableExtensions
chcp 65001 >nul 2>&1
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONDONTWRITEBYTECODE=1"
set "GIT_TERMINAL_PROMPT=0"

rem -- 1. bundled Javis runtime ---------------------------------------------------------------
set "JROOT=%FM_JAVIS_ROOT%"
if not defined JROOT set "JROOT=%LOCALAPPDATA%\cys"
set "PY=%JROOT%\runtime\python\python3.exe"
set "GIT=%JROOT%\runtime\git\cmd\git.exe"
if exist "%PY%" goto :have_py
echo.
echo [STOP] Javis (cys) is not installed on this PC yet.
echo        Please install Javis first, then run this file again:
echo        https://github.com/idoforgod/cys-terminal/releases/latest
if not "%FM_CI%"=="1" start "" "https://github.com/idoforgod/cys-terminal/releases/latest"
if not "%FM_CI%"=="1" pause
exit /b 10
:have_py

rem -- 2. locate the package (fm\cli.py next to this file means we are inside the package) ----
set "CLI=%~dp0fm\cli.py"
if exist "%CLI%" goto :run
if defined FM_PKG_DIR (
  set "CLI=%FM_PKG_DIR%\tools\fm\cli.py"
  goto :run
)
rem standalone (Stage0 download): fetch the package with the bundled git
set "PKG=%USERPROFILE%\Future-Ministry\_pkg\future-ministry-dept"
if not defined FM_REPO_URL set "FM_REPO_URL=https://github.com/yijae78/future-ministry-dept"
if exist "%PKG%\.git" (
  echo [pkg] updating %PKG%
  "%GIT%" -C "%PKG%" pull --ff-only
  if errorlevel 1 echo [pkg] update skipped ^(offline?^) - continuing with the copy on disk
) else (
  if exist "%PKG%" (
    echo [pkg] moving the broken folder aside
    move /y "%PKG%" "%PKG%.broken-%RANDOM%" >nul
  )
  if not exist "%USERPROFILE%\Future-Ministry\_pkg" mkdir "%USERPROFILE%\Future-Ministry\_pkg"
  echo [pkg] cloning %FM_REPO_URL%
  "%GIT%" clone "%FM_REPO_URL%" "%PKG%"
)
set "CLI=%PKG%\tools\fm\cli.py"
if not exist "%CLI%" (
  echo [STOP] could not fetch the package. Check the internet connection and run this file again.
  if not "%FM_CI%"=="1" pause
  exit /b 1
)

:run
if "%~1"=="" (
  "%PY%" -X utf8 "%CLI%" bootstrap
) else (
  "%PY%" -X utf8 "%CLI%" %*
)
exit /b %ERRORLEVEL%
