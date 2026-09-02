@echo off
rem register-protocol.cmd - register the cys-install:// URL protocol for this user (HKCU).
rem No admin rights needed. After this, every install button on the dashboard becomes
rem a one-click install into this PC's Javis. Safe to re-run (idempotent overwrite).
rem NOTE: keep this file ASCII-only - cmd.exe parses batch files with the OEM codepage
rem and UTF-8 Korean here breaks parsing (measured 2026-09-02).
setlocal

set "HANDLER=%~dp0cys-install-handler.ps1"
if not exist "%HANDLER%" (
  echo [ABORT] handler not found: %HANDLER%
  exit /b 1
)

set "PSEXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"

reg add "HKCU\Software\Classes\cys-install" /ve /d "URL:cys-install Protocol" /f >nul || goto :fail
reg add "HKCU\Software\Classes\cys-install" /v "URL Protocol" /d "" /f >nul || goto :fail
reg add "HKCU\Software\Classes\cys-install\shell\open\command" /ve /d "\"%PSEXE%\" -NoProfile -ExecutionPolicy Bypass -File \"%HANDLER%\" \"%%1\"" /f >nul || goto :fail

echo [OK] cys-install:// protocol registered. Dashboard install buttons are now one-click.
exit /b 0

:fail
echo [FAIL] could not write the registry entries.
exit /b 1
