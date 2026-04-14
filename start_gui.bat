@echo off
setlocal

cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python wurde nicht gefunden.
  echo Bitte Python installieren oder zum PATH hinzufuegen.
  pause
  exit /b 1
)

echo Starte GUI...
python gui.py

if errorlevel 1 (
  echo.
  echo [ERROR] GUI konnte nicht gestartet werden.
  pause
  exit /b 1
)

endlocal
