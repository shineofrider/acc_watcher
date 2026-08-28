@echo off
setlocal
cd /d "%~dp0"

echo Installing/updating Python dependencies...
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 exit /b 1

echo.
echo Building acc_watcher.exe...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
python -m PyInstaller --clean --onefile --windowed --name acc_watcher watcher.py
if errorlevel 1 exit /b 1

echo.
echo Build finished: dist\acc_watcher.exe
echo.
echo Install elevated display tasks with:
echo powershell -ExecutionPolicy Bypass -File install_display_tasks.ps1 -ExecutablePath "%CD%\dist\acc_watcher.exe"
echo.
pause
endlocal
