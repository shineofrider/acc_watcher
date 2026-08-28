#!/usr/bin/env python
"""ACC Watcher: simple file-command watcher."""
from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

WATCH_PATH = r"S:\"
TASK_ON = r"acc_watcher\SteamLinkDisplay-On"
TASK_OFF = r"acc_watcher\SteamLinkDisplay-Off"
LOG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "acc_watcher"
LOG_FILE = LOG_DIR / "watcher.log"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("acc_watcher")


def run(args: list[str], timeout: float = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, timeout=timeout,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def run_task(task: str) -> bool:
    try:
        result = run(["schtasks.exe", "/run", "/tn", task], 15)
        if result.returncode != 0:
            logger.error("schtasks failed for %s: %s", task, result.stderr.strip())
            return False
        logger.info("Started scheduled task %s", task)
        return True
    except Exception:
        logger.exception("Unable to start task %s", task)
        return False


def launch(path: str) -> bool:
    try:
        subprocess.Popen([os.path.expandvars(path)], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return True
    except Exception:
        logger.exception("Unable to launch %s", path)
        return False


def shutdown() -> bool:
    return run(["shutdown.exe", "/s", "/t", "0"], 10).returncode == 0


def reboot() -> bool:
    return run(["shutdown.exe", "/r", "/t", "0"], 10).returncode == 0


def sleep() -> bool:
    return run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], 10).returncode == 0


# Add or edit commands here. The callable should return True on success.
COMMANDS: dict[str, Callable[[], bool]] = {
    "shutdown": shutdown,
    "reboot": reboot,
    "restart": reboot,
    "sleep": sleep,
    "notepad": lambda: launch("notepad.exe"),
    "vlc": lambda: launch(r"C:\Program Files\VideoLAN\VLC\vlc.exe"),
    "spotify": lambda: launch(r"%APPDATA%\Spotify\Spotify.exe"),
    "teamviewer": lambda: launch(r"C:\Program Files\TeamViewer\TeamViewer.exe"),
    "vdisplayon": lambda: run_task(TASK_ON),
    "vdisplayoff": lambda: run_task(TASK_OFF),
}


class Handler(FileSystemEventHandler):
    def __init__(self, callback: Callable[[str, bool, str], None] | None = None):
        self.callback = callback
        self.lock = threading.Lock()
        self.processing: set[str] = set()

    def on_created(self, event):
        self._queue(event)

    def on_modified(self, event):
        self._queue(event)

    def _queue(self, event) -> None:
        if event.is_directory or not event.src_path.lower().endswith(".txt"):
            return
        path = os.path.abspath(event.src_path)
        with self.lock:
            if path in self.processing:
                return
            self.processing.add(path)
        threading.Thread(target=self._process, args=(path,), daemon=True).start()

    def _process(self, path: str) -> None:
        try:
            time.sleep(0.5)
            command = None
            for _ in range(10):
                try:
                    with open(path, encoding="utf-8-sig") as f:
                        value = f.read().strip().lower()
                    if value:
                        command = value
                        break
                except OSError:
                    pass
                time.sleep(0.25)

            if command is None:
                self._report("?", False, "Read error or empty command")
                return

            logger.info("Command received: %s", command)
            action = COMMANDS.get(command)
            if action is None:
                logger.warning("Unknown command: %s", command)
                self._report(command, False, "Unknown command")
            else:
                try:
                    ok = bool(action())
                    logger.info("Command %s: %s", command, "OK" if ok else "FAILED")
                    self._report(command, ok, "Executed" if ok else "Execution failed")
                except Exception as exc:
                    logger.exception("Command failed: %s", command)
                    self._report(command, False, str(exc))
            try:
                os.remove(path)
            except OSError:
                logger.exception("Cannot delete command file: %s", path)
        finally:
            with self.lock:
                self.processing.discard(os.path.abspath(path))

    def _report(self, command: str, ok: bool, message: str) -> None:
        if self.callback:
            self.callback(command, ok, message)


def run_watcher() -> int:
    if not os.path.isdir(WATCH_PATH):
        logger.error("Watch path does not exist: %s", WATCH_PATH)
        return 1
    observer = Observer()
    observer.schedule(Handler(), WATCH_PATH, recursive=False)
    observer.start()
    logger.info("Watching %s", WATCH_PATH)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join(timeout=3)
    return 0


if __name__ == "__main__":
    raise SystemExit(run_watcher())
