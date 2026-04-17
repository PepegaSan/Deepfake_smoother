@echo off
setlocal
cd /d "%~dp0.."
if not exist "gui.py" (
  echo ERROR: Run this from the repo. Expected gui.py in parent of packaging\
  exit /b 1
)
where pyinstaller >nul 2>nul
if errorlevel 1 (
  echo ERROR: pyinstaller not on PATH. Run: pip install pyinstaller
  exit /b 1
)

echo Building one-file exes into dist\ ...
pyinstaller --noconfirm packaging\gui.spec
if errorlevel 1 exit /b 1
pyinstaller --noconfirm packaging\flickercheck.spec
if errorlevel 1 exit /b 1
pyinstaller --noconfirm packaging\compare.spec
if errorlevel 1 exit /b 1
pyinstaller --noconfirm packaging\watcher.spec
if errorlevel 1 exit /b 1

echo.
echo Done. Outputs:
echo   dist\gui.exe
echo   dist\flickercheck_ui.exe
echo   dist\compare.exe
echo   dist\watcher.exe
echo Copy next to settings.ini / ffmpeg.exe as needed.
endlocal
