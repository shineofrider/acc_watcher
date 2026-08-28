#!/usr/bin/env python
"""ACC Watcher: network command watcher with Windows tray GUI."""
from __future__ import annotations

import argparse
import json
import logging
import os
import queue
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Optional

import tkinter as tk
from tkinter import ttk

import pystray
from PIL import Image, ImageDraw
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

WATCH_PATH = "S:\\"
TASK_ON = r"acc_watcher\SteamLinkDisplay-On"
TASK_OFF = r"acc_watcher\SteamLinkDisplay-Off"
VDD_NAMES = ("Virtual Display Driver", "IddSampleDriver Device HDR")
LOG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "acc_watcher"
LOG_FILE = LOG_DIR / "watcher.log"

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("acc_watcher")


def run_process(args: list[str], timeout: float = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, timeout=timeout,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def run_powershell(command: str, timeout: float = 30) -> subprocess.CompletedProcess[str]:
    return run_process(["powershell.exe", "-NoProfile", "-NonInteractive",
                        "-ExecutionPolicy", "Bypass", "-Command", command], timeout)


def get_vdd_status() -> dict:
    names = ",".join("'" + n.replace("'", "''") + "'" for n in VDD_NAMES)
    command = (f"$d=Get-PnpDevice -Class Display -ErrorAction SilentlyContinue | "
               f"Where-Object {{$_.FriendlyName -in @({names})}} | "
               f"Select-Object -First 1 FriendlyName,Status,InstanceId; "
               f"if($d){{$d|ConvertTo-Json -Compress}}")
    try:
        result = run_powershell(command, 5)
        if result.returncode != 0 or not result.stdout.strip():
            return {"installed": False, "status": "Unknown", "error": result.stderr.strip()}
        data = json.loads(result.stdout.strip())
        return {"installed": True, "status": data.get("Status", "Unknown"),
                "friendly_name": data.get("FriendlyName", "Virtual Display Driver"),
                "instance_id": data.get("InstanceId", "")}
    except Exception as exc:
        return {"installed": False, "status": "Unknown", "error": str(exc)}


def set_vdd_enabled(enabled: bool) -> bool:
    names = ",".join("'" + n.replace("'", "''") + "'" for n in VDD_NAMES)
    command = (f"$d=Get-PnpDevice -Class Display -ErrorAction Stop | "
               f"Where-Object {{$_.FriendlyName -in @({names})}} | Select-Object -First 1; "
               f"if(-not $d){{throw 'Virtual Display Driver not found'}}; "
               f"if({str(enabled).lower()}){{Enable-PnpDevice -InstanceId $d.InstanceId -Confirm:$false}} "
               f"else {{Disable-PnpDevice -InstanceId $d.InstanceId -Confirm:$false}}")
    result = run_powershell(command, 30)
    if result.returncode != 0:
        logger.error("VDD %s failed: %s", "enable" if enabled else "disable", result.stderr.strip())
        return False
    return True


def switch_display_mode(mode: str) -> int:
    logger.info("Display mode request: %s", mode)
    try:
        display_switch = os.path.join(os.environ["WINDIR"], "System32", "DisplaySwitch.exe")
        if mode == "on":
            if not set_vdd_enabled(True):
                return 10
            time.sleep(2)
            result = run_process([display_switch, "/external"], 15)
        elif mode == "off":
            result = run_process([display_switch, "/internal"], 15)
            time.sleep(2)
            if not set_vdd_enabled(False):
                return 11
        else:
            raise ValueError(f"Unknown display mode: {mode}")
        if result.returncode != 0:
            logger.error("DisplaySwitch failed (%s): %s", result.returncode, result.stderr.strip())
            return 12
        logger.info("Display mode %s applied", mode)
        return 0
    except Exception:
        logger.exception("Display mode %s failed", mode)
        return 13


def run_display_task(mode: str) -> bool:
    task = TASK_ON if mode == "on" else TASK_OFF
    try:
        result = run_process(["schtasks.exe", "/run", "/tn", task], 15)
        if result.returncode != 0:
            logger.error("Cannot run task %s: %s", task, result.stderr.strip())
            return False
        logger.info("Started scheduled task %s", task)
        return True
    except Exception:
        logger.exception("Cannot run scheduled task %s", task)
        return False


def task_exists(task: str) -> bool:
    try:
        return run_process(["schtasks.exe", "/query", "/tn", task], 5).returncode == 0
    except Exception:
        return False


def launch_program(path: str) -> None:
    subprocess.Popen([os.path.expandvars(path)], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def command_shutdown() -> None:
    subprocess.run(["shutdown.exe", "/s", "/t", "0"], check=False)


def command_reboot() -> None:
    subprocess.run(["shutdown.exe", "/r", "/t", "0"], check=False)


def command_sleep() -> None:
    subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=False)


COMMANDS: dict[str, Callable[[], object]] = {
    "shutdown": command_shutdown,
    "reboot": command_reboot,
    "restart": command_reboot,
    "sleep": command_sleep,
    "notepad": lambda: launch_program("notepad.exe"),
    "vlc": lambda: launch_program(r"C:\Program Files\VideoLAN\VLC\vlc.exe"),
    "spotify": lambda: launch_program(r"%APPDATA%\Spotify\Spotify.exe"),
    "teamviewer": lambda: launch_program(r"C:\Program Files\TeamViewer\TeamViewer.exe"),
    "vdisplayon": lambda: run_display_task("on"),
    "vdisplayoff": lambda: run_display_task("off"),
}


class Handler(FileSystemEventHandler):
    def __init__(self, callback: Callable[[str, bool, str], None]):
        self.callback = callback
        self.lock = threading.Lock()
        self.processing: set[str] = set()

    def on_created(self, event):
        self._queue_file(event)

    def on_modified(self, event):
        self._queue_file(event)

    def _queue_file(self, event) -> None:
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
            cmd = None
            for _ in range(10):
                try:
                    with open(path, encoding="utf-8-sig") as f:
                        value = f.read().strip().lower()
                    if value:
                        cmd = value
                        break
                except OSError:
                    pass
                time.sleep(0.25)
            if cmd is None:
                logger.error("Unable to read command file %s", path)
                self.callback("?", False, "Read error or empty command")
                return

            logger.info("Command received: %s", cmd)
            action = COMMANDS.get(cmd)
            if not action:
                logger.warning("Unknown command: %s", cmd)
                self.callback(cmd, False, "Unknown command")
            else:
                try:
                    result = action()
                    ok = result is not False
                    self.callback(cmd, ok, "Executed" if ok else "Execution failed")
                    logger.info("Command %s: %s", cmd, "OK" if ok else "FAILED")
                except Exception as exc:
                    logger.exception("Command %s failed", cmd)
                    self.callback(cmd, False, str(exc))
            try:
                os.remove(path)
            except OSError as exc:
                logger.warning("Could not delete %s: %s", path, exc)
        finally:
            with self.lock:
                self.processing.discard(os.path.abspath(path))


class WatcherApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ACC Watcher")
        self.root.geometry("650x430")
        self.root.minsize(600, 380)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.root.withdraw()
        self.events: queue.Queue[tuple[str, bool, str]] = queue.Queue()
        self.status_events: queue.Queue[tuple[dict, bool]] = queue.Queue()
        self.observer: Optional[Observer] = None
        self.running = False
        self.tray: Optional[pystray.Icon] = None
        self._build_ui()

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="ACC Watcher", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(outer, text=f"Watching: {WATCH_PATH}").pack(anchor="w", pady=(0, 12))
        status = ttk.LabelFrame(outer, text="Status", padding=10)
        status.pack(fill="x")
        self.watch_label = ttk.Label(status, text="Watcher: starting...")
        self.watch_label.pack(anchor="w")
        self.vdd_label = ttk.Label(status, text="VDD: checking...")
        self.vdd_label.pack(anchor="w")
        self.tasks_label = ttk.Label(status, text="Display tasks: checking...")
        self.tasks_label.pack(anchor="w")
        self.last_label = ttk.Label(status, text="Last command: -")
        self.last_label.pack(anchor="w")
        controls = ttk.LabelFrame(outer, text="Display (local test)", padding=10)
        controls.pack(fill="x", pady=10)
        ttk.Button(controls, text="Steam Link mode", command=lambda: self._manual_display("on")).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Desktop mode", command=lambda: self._manual_display("off")).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Refresh", command=self.refresh).pack(side="left")
        log_frame = ttk.LabelFrame(outer, text="Activity", padding=8)
        log_frame.pack(fill="both", expand=True)
        self.log = tk.Text(log_frame, height=10, state="disabled", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)

    def _create_tray_image(self):
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((6, 6, 58, 58), outline="white", width=5)
        draw.rectangle((27, 16, 37, 48), fill="white")
        return image

    def start(self):
        if not os.path.isdir(WATCH_PATH):
            self._append(f"ERROR: watched path does not exist: {WATCH_PATH}")
            self.watch_label.configure(text="Watcher: PATH NOT FOUND")
        else:
            self.observer = Observer()
            self.observer.schedule(Handler(self.on_command), WATCH_PATH, recursive=False)
            self.observer.start()
            self.running = True
            self.watch_label.configure(text="Watcher: RUNNING")
            logger.info("Watching %s", WATCH_PATH)
            self._append(f"Watching {WATCH_PATH}")
        self.tray = pystray.Icon(
            "acc_watcher", self._create_tray_image(), "ACC Watcher",
            menu=pystray.Menu(
                pystray.MenuItem("Open", self._tray_open),
                pystray.MenuItem("Steam Link mode", lambda: self._manual_display("on")),
                pystray.MenuItem("Desktop mode", lambda: self._manual_display("off")),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit", self._tray_exit),
            ),
        )
        threading.Thread(target=self.tray.run, daemon=True).start()
        self.refresh()
        self.root.after(200, self._drain_events)
        self.root.after(3000, self._periodic_refresh)
        self.root.mainloop()

    def on_command(self, cmd: str, ok: bool, message: str):
        self.events.put((cmd, ok, message))

    def _drain_events(self):
        while True:
            try:
                cmd, ok, message = self.events.get_nowait()
            except queue.Empty:
                break
            self.last_label.configure(text=f"Last command: {cmd} — {message}")
            self._append(f"{'OK' if ok else 'ERROR'}  {cmd}: {message}")
        while True:
            try:
                vdd, tasks = self.status_events.get_nowait()
            except queue.Empty:
                break
            self._apply_status(vdd, tasks)
        self.root.after(200, self._drain_events)

    def _periodic_refresh(self):
        self.refresh()
        self.root.after(3000, self._periodic_refresh)

    def refresh(self):
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self):
        vdd = get_vdd_status()
        tasks = task_exists(TASK_ON) and task_exists(TASK_OFF)
        self.status_events.put((vdd, tasks))

    def _apply_status(self, vdd: dict, tasks: bool):
        if vdd.get("installed"):
            self.vdd_label.configure(text=f"VDD: {vdd.get('status', 'Unknown')} ({vdd.get('friendly_name', 'VDD')})")
        else:
            self.vdd_label.configure(text="VDD: NOT FOUND")
        self.tasks_label.configure(text=f"Display tasks: {'READY' if tasks else 'NOT INSTALLED'}")

    def _manual_display(self, mode: str):
        if not run_display_task(mode):
            self._append(f"ERROR: could not start display task ({mode})")
        else:
            self._append(f"Requested {'Steam Link' if mode == 'on' else 'Desktop'} mode")
            self.root.after(2500, self.refresh)

    def _tray_open(self, icon=None, item=None):
        self.root.after(0, self.show_window)

    def _tray_exit(self, icon=None, item=None):
        self.root.after(0, self.close)

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide_window(self):
        self.root.withdraw()

    def _append(self, text: str):
        logger.info(text)
        if not self.root.winfo_exists():
            return
        self.log.configure(state="normal")
        self.log.insert("end", f"{time.strftime('%H:%M:%S')}  {text}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def close(self):
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=2)
        if self.tray:
            try:
                self.tray.stop()
            except Exception:
                pass
        self.root.destroy()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--display-mode", choices=("on", "off"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.display_mode:
        return switch_display_mode(args.display_mode)
    WatcherApp().start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
