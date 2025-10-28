from __future__ import annotations

"""
Helper to install/start/stop/remove Windows Services for client/server.
Usage (on Windows, in elevated prompt):
  python setup_windows_service.py --role server --action install --config C:\\signing_service\\server_config.json
  python setup_windows_service.py --role server --action start
  python setup_windows_service.py --role server --action stop
  python setup_windows_service.py --role server --action remove

  python setup_windows_service.py --role client --action install --config C:\\signing_service\\client_config.json
"""

import argparse
import sys

try:
    import win32serviceutil  # type: ignore
except Exception:  # pragma: no cover
    win32serviceutil = None


ROLE_TO_MODULE = {
    "server": "signing_service.server.service",
    "client": "signing_service.client.service",
}

SERVICE_CLASS = {
    "server": "SigningServerService",
    "client": "SigningClientService",
}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=["server", "client"], required=True)
    parser.add_argument(
        "--action",
        choices=["install", "remove", "start", "stop", "restart"],
        required=True,
    )
    parser.add_argument("--config", required=False)
    args = parser.parse_args(argv)

    if not win32serviceutil:
        print("This helper must be run on Windows with pywin32 installed.")
        sys.exit(1)

    module = ROLE_TO_MODULE[args.role]
    service_class = SERVICE_CLASS[args.role]
    svc_fqn = f"{module}.{service_class}"

    if args.action == "install":
        if args.config:
            # Pass --config via cmd line. Set to auto start.
            win32serviceutil.InstallService(
                svc_fqn,
                service_class,
                f"Code Signing {args.role.title()}",
                startType=win32serviceutil.SERVICE_AUTO_START,
                exeArgs=f"--config {args.config}",
            )
        else:
            win32serviceutil.InstallService(
                svc_fqn,
                service_class,
                f"Code Signing {args.role.title()}",
                startType=win32serviceutil.SERVICE_AUTO_START,
            )
        print("Installed.")
    elif args.action == "remove":
        win32serviceutil.RemoveService(service_class)
        print("Removed.")
    elif args.action == "start":
        win32serviceutil.StartService(service_class)
        print("Started.")
    elif args.action == "stop":
        win32serviceutil.StopService(service_class)
        print("Stopped.")
    elif args.action == "restart":
        win32serviceutil.RestartService(service_class)
        print("Restarted.")


if __name__ == "__main__":
    main()
