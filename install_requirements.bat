@echo off
setlocal EnableExtensions

cd /d "%~dp0"

REM Prefer Windows Python launcher, then python on PATH
set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"
if not defined PY_CMD (
  where python >nul 2>nul
  if not errorlevel 1 set "PY_CMD=python"
)

if not defined PY_CMD (
  echo [ERROR] Python wurde nicht gefunden.
  echo Bitte Python 3.10+ installieren oder "py" / "python" zum PATH hinzufuegen.
  pause
  exit /b 1
)

if not exist requirements.txt (
  echo [ERROR] requirements.txt wurde nicht gefunden.
  pause
  exit /b 1
)

echo Verwende: %PY_CMD%
echo Installiere Python-Abhaengigkeiten aus requirements.txt...
%PY_CMD% -m pip install --upgrade pip setuptools wheel
%PY_CMD% -m pip install -r requirements.txt

if errorlevel 1 (
  echo.
  echo [ERROR] Installation fehlgeschlagen.
  pause
  exit /b 1
)

echo.
echo [OK] Installation abgeschlossen. Anschliessend z. B. start_gui.bat oder python gui.py
pause
endlocal
