from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable


def sha256_of_file(path: str | os.PathLike[str]) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_dir(path: str | os.PathLike[str]) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def run_command(args: Iterable[str], cwd: str | None = None, timeout: int | None = 600) -> tuple[int, str, str]:
    proc = subprocess.Popen(
        list(args),
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=False,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        return 124, out, err
    return proc.returncode, out, err


def atomic_copy(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
    dst_path = Path(dst)
    tmp_dir = dst_path.parent
    with tempfile.NamedTemporaryFile(dir=tmp_dir, delete=False) as tmp:
        tmp.close()
        shutil.copy2(src, tmp.name)
        os.replace(tmp.name, dst_path)
