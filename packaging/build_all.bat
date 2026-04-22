@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

if not exist "gui.py" (
  echo [ERROR] Run this from the repo. Expected gui.py in parent of packaging\
  exit /b 1
)

set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"
if not defined PY_CMD (
  where python >nul 2>nul
  if not errorlevel 1 set "PY_CMD=python"
)

if not defined PY_CMD (
  echo [ERROR] Python not found. Install Python 3.10+ or add py/python to PATH.
  exit /b 1
)

echo [%PY_CMD%] Upgrading pip / installing runtime deps from requirements.txt...
%PY_CMD% -m pip install --upgrade pip setuptools wheel
%PY_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] pip install -r requirements.txt failed.
  exit /b 1
)

if exist "packaging\requirements-build.txt" (
  echo [%PY_CMD%] Installing build deps from packaging\requirements-build.txt...
  %PY_CMD% -m pip install -r packaging\requirements-build.txt
  if errorlevel 1 (
    echo [ERROR] pip install build requirements failed.
    exit /b 1
  )
) else (
  echo [WARN] packaging\requirements-build.txt missing — installing PyInstaller only...
  %PY_CMD% -m pip install "pyinstaller>=6.8.0"
)

where pyinstaller >nul 2>nul
if errorlevel 1 (
  echo [ERROR] pyinstaller not on PATH after install. Try: %PY_CMD% -m PyInstaller --version
  exit /b 1
)

echo.
echo Building one-file exes into dist\ ...
%PY_CMD% -m PyInstaller --noconfirm packaging\gui.spec
if errorlevel 1 exit /b 1
%PY_CMD% -m PyInstaller --noconfirm packaging\flickercheck.spec
if errorlevel 1 exit /b 1
%PY_CMD% -m PyInstaller --noconfirm packaging\compare.spec
if errorlevel 1 exit /b 1
%PY_CMD% -m PyInstaller --noconfirm packaging\watcher.spec
if errorlevel 1 exit /b 1

echo.
echo Done. Outputs:
echo   dist\gui.exe
echo   dist\flickercheck_ui.exe
echo   dist\compare.exe
echo   dist\watcher.exe
echo Copy next to settings.ini / ffmpeg.exe as needed. gui.exe needs tkinterdnd2 bundled — already in gui.spec (collect_all).
endlocal
