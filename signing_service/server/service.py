from __future__ import annotations

import io
import os
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request, send_file
from waitress import serve

from signing_service.common.config import ServerConfig, load_config
from signing_service.common.utils import ensure_dir, run_command, sha256_of_file


app = Flask(__name__)

config: Optional[ServerConfig] = None


@app.route("/healthz", methods=["GET"])  # liveness/readiness
def healthz():
    return jsonify({"status": "ok"})


@app.route("/sign", methods=["POST"])
def sign_module():
    assert config is not None

    if "file" not in request.files:
        return jsonify({"error": "file field required"}), 400

    file = request.files["file"]
    filename = file.filename or ""

    ext = os.path.splitext(filename)[1].lower()
    if config.allowed_extensions and ext not in config.allowed_extensions:
        return jsonify({"error": f"extension {ext} not allowed"}), 400

    content = file.read()
    if len(content) > config.max_upload_mb * 1024 * 1024:
        return jsonify({"error": "file too large"}), 413

    # workspace
    work_dir = Path(config.work_dir)
    ensure_dir(work_dir)
    input_path = work_dir / f"input_{os.getpid()}_{filename}"
    signed_path = work_dir / f"signed_{os.getpid()}_{filename}"

    input_path.write_bytes(content)

    # invoke signtool
    cmd = [
        config.signtool_path,
        "sign",
        "/f",
        config.cert_pfx_path,
        "/p",
        config.cert_password or "",
        "/tr",
        config.timestamp_url,
        "/td",
        "sha256",
        "/fd",
        "sha256",
        "/v",
        str(input_path),
    ]

    code, out, err = run_command(cmd)
    if code != 0:
        return (
            jsonify(
                {
                    "error": "signtool failed",
                    "return_code": code,
                    "stdout": out[-4000:],
                    "stderr": err[-4000:],
                    "config": {k: v for k, v in asdict(config).items() if k != "cert_password"},
                }
            ),
            500,
        )

    # signtool signs in place, so just read back
    digest = sha256_of_file(input_path)
    with open(input_path, "rb") as f:
        data = f.read()

    return send_file(
        io.BytesIO(data),
        mimetype="application/octet-stream",
        as_attachment=True,
        download_name=filename,
        last_modified=None,
        etag=False,
        conditional=False,
        headers={"X-File-SHA256": digest},
    )


# Windows Service entry (pywin32) - optional for non-Windows runtime
try:
    import win32serviceutil  # type: ignore
    import win32service  # type: ignore
    import win32event  # type: ignore
except Exception:  # pragma: no cover
    win32serviceutil = None
    win32service = None
    win32event = None


class SigningServerService(win32serviceutil.ServiceFramework if win32serviceutil else object):  # type: ignore
    _svc_name_ = "SigningServerService"
    _svc_display_name_ = "Code Signing Server"

    def __init__(self, args):  # type: ignore[no-untyped-def]
        if win32serviceutil:
            super().__init__(args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)  # type: ignore[attr-defined]
        self.httpd = None

    def SvcStop(self):  # type: ignore[no-untyped-def]
        if win32serviceutil:
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)  # type: ignore[attr-defined]
            win32event.SetEvent(self.stop_event)  # type: ignore[attr-defined]

    def SvcDoRun(self):  # type: ignore[no-untyped-def]
        main()



def main(argv: Optional[list[str]] = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Code signing server")
    parser.add_argument("--config", required=False, default="server_config.json")
    parser.add_argument("--host", required=False)
    parser.add_argument("--port", type=int, required=False)

    args = parser.parse_args(argv)
    global config
    config = load_config(args.config, kind="server")
    if args.host:
        config.host = args.host
    if args.port:
        config.port = args.port

    ensure_dir(config.work_dir)

    # run waitress production WSGI server
    serve(app, host=config.host, port=config.port)


if __name__ == "__main__":
    main()
