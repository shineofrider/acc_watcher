============================================
ACC Watcher – Quick Start
============================================

Overview
--------
ACC Watcher is a small Windows file-command watcher. It monitors a mapped
folder and executes a predefined command when a .txt file is created.

It now also includes a small monitoring GUI and optional elevated Windows
Scheduled Tasks for switching between a physical monitor and the VDD virtual
display used by Steam Link.

Contents
--------
watcher.py                   Main application + monitoring GUI
requirements.txt             Python dependency list
build.bat                    Build standalone EXE with PyInstaller
install_display_tasks.ps1    Install elevated display-switching tasks
uninstall_display_tasks.ps1  Remove the display-switching tasks

Requirements
------------
• Windows PC with Python 3.8+ (64-bit) when building from source
• The watched folder must exist and be accessible by the logged-in user
• .txt files containing a single command word

The current default watched path is:
    S:\

Edit WATCH_PATH in watcher.py if required.

Supported commands
------------------
shutdown      – Shutdown computer immediately
sleep         – Suspend computer
notepad       – Launch Notepad
vlc           – Launch VLC
spotify       – Launch Spotify
teamviewer    – Launch TeamViewer
vdisplayon    – Request Steam Link display mode
vdisplayoff   – Request normal desktop display mode

Display switching architecture
------------------------------
The watcher itself does NOT require administrator privileges.

The two VDD commands call Windows Scheduled Tasks:

    acc_watcher\SteamLinkDisplay-On
    acc_watcher\SteamLinkDisplay-Off

Those tasks are installed with "Run with highest privileges" and execute the
same acc_watcher.exe with:

    --display-mode on
    --display-mode off

Display mode "on":
    1. Enable the Virtual Display Driver.
    2. Wait briefly for Windows to enumerate it.
    3. Run DisplaySwitch.exe /external.

Display mode "off":
    1. Run DisplaySwitch.exe /internal to return to the physical display.
    2. Wait briefly.
    3. Disable the Virtual Display Driver.

This keeps the normal physical display configuration untouched and avoids
running the whole watcher elevated.

Build
-----
Run build.bat from an ordinary Command Prompt. It installs the dependencies
and creates:

    dist\acc_watcher.exe

Install display tasks
---------------------
After building, open PowerShell as Administrator and run:

    .\install_display_tasks.ps1 -ExecutablePath "C:\path\to\dist\acc_watcher.exe"

If PowerShell is not elevated, the installer requests elevation itself.

The installer creates the two tasks for the current interactive user with
highest privileges. No password is stored by the script.

The GUI
-------
Starting acc_watcher.exe without arguments opens the monitoring GUI.
It shows:

• watcher status
• VDD presence/status
• whether both display tasks are installed
• last received command
• recent activity

The GUI also has buttons for manually requesting Steam Link mode or normal
desktop mode. These buttons use the same Scheduled Tasks as remote commands.

Privileged display mode
----------------------
The executable also supports the following internal command-line modes:

    acc_watcher.exe --display-mode on
    acc_watcher.exe --display-mode off

These modes are intended for the elevated Scheduled Tasks and do not open the
GUI.

Uninstall display tasks
-----------------------
Run:

    .\uninstall_display_tasks.ps1

The script requests administrator privileges if necessary.

Security
--------
The watched folder is effectively a remote command interface: anyone who can
create files in it can request the commands exposed by COMMANDS.

Recommended precautions:
• restrict write access to the watched folder
• expose only commands that are actually needed
• do not add arbitrary shell-command execution
• keep the VDD task definitions limited to the fixed --display-mode actions

Logging
-------
The application writes a log to:

    %LOCALAPPDATA%\acc_watcher\watcher.log

The GUI is intended for local monitoring; the file log is the persistent
record for troubleshooting.
