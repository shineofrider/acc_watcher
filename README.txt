============================================
File-based Command Watcher – Quick Start
============================================

Contents
--------
watcher.py          Python script that watches a folder and executes commands
requirements.txt    Python dependencies
build.bat           Helper script to create watcher.exe with PyInstaller

Requirements
------------
• Windows PC with Python 3.8+ (64-bit) installed
• The 'Z:\comandi' folder must exist and be mapped on Windows
• .txt files containing a single command word placed in that folder

Supported commands (default)
----------------------------
shutdown    – Shutdown computer immediately
sleep       – Suspend computer
notepad     – Launch Notepad
vlc         – Launch VLC media player
spotify     – Launch Spotify

Modify or extend the COMMANDS dict in watcher.py to add more actions.

Build EXE
---------
1. Open Command Prompt in this folder.
2. Run:
       build.bat
   This installs PyInstaller and produces a standalone watcher.exe
   located in the 'dist' subfolder.

Install as a Windows Service (optional)
---------------------------------------
1. Download NSSM (Non‑Sucking Service Manager) from https://nssm.cc/
2. From an elevated Command Prompt:
       nssm install FileWatcher "C:\path\to\dist\watcher.exe"
3. Start the service:
       nssm start FileWatcher

Security Tips
-------------
• Optionally add a shared secret to commands (parse and verify in watcher.py)
• Restrict write access to the watched folder to trusted users only.
