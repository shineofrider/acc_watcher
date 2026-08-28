@echo off
REM Build watcher.exe using PyInstaller
pip install --upgrade pip
pip install watchdog pyinstaller
pyinstaller --onefile --noconsole watcher.py
echo.
echo Build finished. Find watcher.exe in the "dist" folder.
pause
