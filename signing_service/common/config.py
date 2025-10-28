from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    signtool_path: str = r"C:\\Program Files (x86)\\Windows Kits\\10\\bin\\x64\\signtool.exe"
    cert_pfx_path: str = r"C:\\certs\\codesign.pfx"
    cert_password: Optional[str] = None
    timestamp_url: str = "http://timestamp.digicert.com"
    work_dir: str = r"C:\\signing_service\\work"
    max_upload_mb: int = 200
    allowed_extensions: tuple[str, ...] = (".exe", ".dll", ".sys", ".msi")


@dataclass
class ClientConfig:
    server_url: str = "http://localhost:8080"
    watch_dir: str = r"C:\\to_sign"
    output_dir: str = r"C:\\signed"
    poll_interval_sec: float = 1.0
    retry_count: int = 3
    retry_backoff_sec: float = 2.0


def load_config(path: str | Path, kind: str) -> ServerConfig | ClientConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if kind == "server":
        cfg = ServerConfig(**data)
        return cfg
    if kind == "client":
        cfg = ClientConfig(**data)
        return cfg
    raise ValueError("kind must be 'server' or 'client'")
