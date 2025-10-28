from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

import requests
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from signing_service.common.config import ClientConfig, load_config
from signing_service.common.utils import ensure_dir, atomic_copy


class NewFileHandler(FileSystemEventHandler):
    def __init__(self, cfg: ClientConfig):
        super().__init__()
        self.cfg = cfg

    def on_created(self, event):  # type: ignore[no-untyped-def]
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() not in {".exe", ".dll", ".sys", ".msi"}:
            return
        self.process_file(path)

    def process_file(self, path: Path) -> None:
        # wait until file is fully written
        size = -1
        while True:
            new_size = path.stat().st_size
            if new_size == size:
                break
            size = new_size
            time.sleep(0.2)

        for attempt in range(self.cfg.retry_count):
            try:
                with path.open("rb") as f:
                    files = {"file": (path.name, f, "application/octet-stream")}
                    resp = requests.post(f"{self.cfg.server_url}/sign", files=files, timeout=600)

                if resp.status_code == 200:
                    ensure_dir(self.cfg.output_dir)
                    out_file = Path(self.cfg.output_dir) / path.name
                    with open(out_file.with_suffix(out_file.suffix + ".tmp"), "wb") as tmp:
                        tmp.write(resp.content)
                    atomic_copy(out_file.with_suffix(out_file.suffix + ".tmp"), out_file)
                    return
                else:
                    print("Sign failed:", resp.status_code, resp.text)
            except Exception as e:  # pragma: no cover - network etc
                print("Error:", e)
            time.sleep(self.cfg.retry_backoff_sec)


# Windows Service scaffolding
try:
    import win32serviceutil  # type: ignore
    import win32service  # type: ignore
    import win32event  # type: ignore
except Exception:  # pragma: no cover
    win32serviceutil = None
    win32service = None
    win32event = None


class SigningClientService(win32serviceutil.ServiceFramework if win32serviceutil else object):  # type: ignore
    _svc_name_ = "SigningClientService"
    _svc_display_name_ = "Code Signing Client"

    def __init__(self, args):  # type: ignore[no-untyped-def]
        if win32serviceutil:
            super().__init__(args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)  # type: ignore[attr-defined]
        self.observer: Optional[Observer] = None

    def SvcStop(self):  # type: ignore[no-untyped-def]
        if win32serviceutil:
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)  # type: ignore[attr-defined]
            win32event.SetEvent(self.stop_event)  # type: ignore[attr-defined]
        if self.observer:
            self.observer.stop()
            self.observer.join()

    def SvcDoRun(self):  # type: ignore[no-untyped-def]
        main()


def main(argv: Optional[list[str]] = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Code signing client")
    parser.add_argument("--config", required=False, default="client_config.json")
    args = parser.parse_args(argv)

    cfg = load_config(args.config, kind="client")

    ensure_dir(cfg.watch_dir)
    ensure_dir(cfg.output_dir)

    event_handler = NewFileHandler(cfg)
    observer = Observer()
    observer.schedule(event_handler, cfg.watch_dir, recursive=False)
    observer.start()

    print("Watching", cfg.watch_dir)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
