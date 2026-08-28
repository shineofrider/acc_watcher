#!/usr/bin/env python
"""
Simple file-based command launcher for Windows.
Place .txt files with a single command (e.g. "shutdown") into the
watched folder (default Z:\comandi). When the script detects the file,
it executes the mapped action and deletes the file.

Requirements:
    pip install watchdog

Build standalone EXE:
    pyinstaller --onefile --noconsole watcher.py
"""
import os
import subprocess
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Path to the mapped network folder containing command files
WATCH_PATH = r"s:"  # Change if needed

# Map simple text commands to system actions
COMMANDS = {
    "shutdown": lambda: subprocess.run(["shutdown", "/s", "/t", "0"]),
    "sleep":    lambda: subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"]),
    "notepad":  lambda: subprocess.Popen(["notepad.exe"]),
    "vlc":      lambda: subprocess.Popen([r"C:\Program Files\VideoLAN\VLC\vlc.exe"]),
    # Adjust Spotify path if necessary
    "spotify":  lambda: subprocess.Popen([os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe")]),
    "teamviewer":  lambda: subprocess.Popen([os.path.expandvars(r"C:\Program Files\TeamViewer\TeamViewer.exe")]),
    "vdisplayon":  lambda: subprocess.Popen([os.path.expandvars(r"C:\Scripts\SteamLinkDisplay_on.cmd")]),
    "vdisplayoff":  lambda: subprocess.Popen([os.path.expandvars(r"C:\Scripts\SteamLinkDisplay_off.cmd")]),
}

class Handler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith(".txt"):
            return
        # Wait briefly to ensure file is finished writing
        time.sleep(0.5)
        try:
            with open(event.src_path, encoding="utf-8") as f:
                cmd = f.read().strip().lower()
        except Exception as read_err:
            print(f"[ERR] Unable to read '{{event.src_path}}': {{read_err}}")
            return

        print(f"[INFO] Command received: {{cmd}}")
        action = COMMANDS.get(cmd)
        if action:
            try:
                action()
                print(f"[OK] Executed: {{cmd}}")
            except Exception as exec_err:
                print(f"[ERR] Error executing '{{cmd}}': {{exec_err}}")
        else:
            print(f"[WARN] Unknown command: {{cmd}}")

        # Attempt to delete the processed file
        try:
            os.remove(event.src_path)
        except Exception as del_err:
            print(f"[WARN] Could not delete file '{{event.src_path}}': {{del_err}}")

def main():
    print(f"[START] Watching folder: {{WATCH_PATH}}")
    if not os.path.isdir(WATCH_PATH):
        print(f"[ERR] WATCH_PATH '{{WATCH_PATH}}' does not exist. Edit watcher.py to correct the path.")
        return

    observer = Observer()
    observer.schedule(Handler(), WATCH_PATH, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[INFO] Shutting down watcher.")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
