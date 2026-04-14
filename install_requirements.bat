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

if not exist requirements.txt (
  echo [ERROR] requirements.txt wurde nicht gefunden.
  pause
  exit /b 1
)

echo Installiere Python-Abhaengigkeiten aus requirements.txt...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if errorlevel 1 (
  echo.
  echo [ERROR] Installation fehlgeschlagen.
  pause
  exit /b 1
)

echo.
echo [OK] Installation abgeschlossen.
pause
endlocal
