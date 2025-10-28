from __future__ import annotations

import json
import os
import sys
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


def _resolve_config_path(path: str | Path) -> Path:
    """Resolve config path for both source and PyInstaller-frozen executables.

    Resolution order:
    1) Absolute path, if exists
    2) Exact path relative to current working directory
    3) File with the same base name next to the executable (if frozen)
    4) File with the same base name inside PyInstaller _MEIPASS (if bundled via --add-data)
    5) File with the same base name next to the running module (source layout)
    6) SIGNING_SERVICE_CONFIG_DIR environment directory joined with the base name
    """
    candidate_names: list[Path] = []
    given = Path(path)

    # 1) Absolute path
    if given.is_absolute():
        if given.exists():
            return given
        # fall through to try alternatives with its name

    # 2) Relative to CWD
    candidate_names.append(Path.cwd() / given)

    # 3) Next to the executable when frozen
    try:
        if getattr(sys, "frozen", False):  # PyInstaller onefile/onedir
            exe_dir = Path(sys.executable).resolve().parent
            candidate_names.append(exe_dir / given.name)
    except Exception:
        pass

    # 4) Inside _MEIPASS if bundled via --add-data
    try:
        meipass_dir = Path(getattr(sys, "_MEIPASS", ""))
        if meipass_dir and meipass_dir.exists():
            candidate_names.append(meipass_dir / given.name)
    except Exception:
        pass

    # 5) Next to this module (source tree: signing_service/common)
    module_base = Path(__file__).resolve().parent.parent
    candidate_names.append(module_base / given)
    candidate_names.append(module_base / given.name)

    # 6) Environment override directory
    env_dir = os.environ.get("SIGNING_SERVICE_CONFIG_DIR")
    if env_dir:
        candidate_names.append(Path(env_dir) / given.name)

    for cand in candidate_names:
        if cand.exists():
            return cand

    tried = "\n".join(str(c) for c in [given] + candidate_names)
    raise FileNotFoundError(
        f"Config file not found. Tried the following locations:\n{tried}"
    )


def load_config(path: str | Path, kind: str) -> ServerConfig | ClientConfig:
    resolved = _resolve_config_path(path)
    data = json.loads(resolved.read_text(encoding="utf-8"))
    if kind == "server":
        cfg = ServerConfig(**data)
        return cfg
    if kind == "client":
        cfg = ClientConfig(**data)
        return cfg
    raise ValueError("kind must be 'server' or 'client'")
