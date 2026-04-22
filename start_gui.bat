@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"
if not defined PY_CMD (
  where python >nul 2>nul
  if not errorlevel 1 set "PY_CMD=python"
)

if not defined PY_CMD (
  echo [ERROR] Python wurde nicht gefunden.
  pause
  exit /b 1
)

if not exist gui.py (
  echo [ERROR] gui.py wurde nicht gefunden. Batch muss im Projektroot liegen.
  pause
  exit /b 1
)

echo Starte Control Center (%PY_CMD% gui.py)...
%PY_CMD% gui.py

if errorlevel 1 (
  echo.
  echo [ERROR] GUI konnte nicht gestartet werden. Dependencies installiert? Siehe install_requirements.bat
  pause
  exit /b 1
)

endlocal
