from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

import psutil

from localllm import __version__
from localllm.instance import resolve_instance, state_dir

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8002


def _pid_file() -> Path:
    return state_dir() / "web.pid"


def _log_file() -> Path:
    return state_dir() / "web.log"


def _read_pid() -> int | None:
    try:
        return int(_pid_file().read_text().strip())
    except (OSError, ValueError):
        return None


def _web_alive(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        p = psutil.Process(pid)
        return "uvicorn" in " ".join(p.cmdline())
    except psutil.Error:
        return False


def _find_web_proc(port: int) -> psutil.Process | None:
    for p in psutil.process_iter(["cmdline"]):
        try:
            cmd = " ".join(p.cmdline() or [])
        except psutil.Error:
            continue
        if "uvicorn" in cmd and f"--port {port}" in cmd:
            return p
    return None


def _wait_ready(port: int, timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def cmd_serve(args: argparse.Namespace) -> int:
    inst = resolve_instance(args.home)
    print(f"localllm: instance {inst.path} ({inst.mode})")
    import uvicorn

    from web.main import app

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def cmd_open(args: argparse.Namespace) -> int:
    inst = resolve_instance(args.home)
    port = args.port
    url = f"http://{args.host}:{port}"

    pid = _read_pid()
    if _web_alive(pid) or _find_web_proc(port):
        webbrowser.open(url)
        print(f"localllm: web already running at {url}")
        return 0

    log_path = _log_file()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "ab")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "web.main:app", "--host", args.host, "--port", str(port)],
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        # neutral cwd: `python -m` puts cwd on sys.path, which would shadow
        # the installed packages if the user happens to be in a checkout
        cwd=str(Path.home()),
    )
    _pid_file().write_text(str(proc.pid))
    log.close()

    if _wait_ready(port):
        webbrowser.open(url)
        print(f"localllm: web running at {url} (pid {proc.pid})")
    else:
        print(
            f"localllm: web process started (pid {proc.pid}) but not ready yet; see {log_path}",
            file=sys.stderr,
        )
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    pid = _read_pid()
    p = None
    if _web_alive(pid):
        p = psutil.Process(pid)
    else:
        p = _find_web_proc(args.port)
    if p is None:
        print("localllm: web is not running")
        _pid_file().unlink(missing_ok=True)
        return 0
    p.terminate()
    try:
        p.wait(timeout=5)
    except psutil.TimeoutExpired:
        p.kill()
    _pid_file().unlink(missing_ok=True)
    print(f"localllm: web stopped (pid {p.pid})")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    inst = resolve_instance(args.home)
    pid = _read_pid()
    if _web_alive(pid):
        status = f"running (pid {pid})"
    else:
        p = _find_web_proc(args.port)
        status = f"running (pid {p.pid})" if p else "not running"
    print(f"instance: {inst.path} ({inst.mode})")
    print(f"web:      {status}  http://{args.host}:{args.port}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="localllm", description="Manage a local DFlash2 llama.cpp stack"
    )
    parser.add_argument("--version", action="version", version=f"localllm {__version__}")
    sub = parser.add_subparsers(dest="cmd")

    webp = sub.add_parser("web", help="web UI")
    websub = webp.add_subparsers(dest="webcmd", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--host", default=DEFAULT_HOST)
        p.add_argument("--port", type=int, default=DEFAULT_PORT)
        p.add_argument("--home", default=None, help="instance directory (default: auto-detect)")

    p = websub.add_parser("serve", help="run the web UI in the foreground")
    add_common(p)
    p.set_defaults(func=cmd_serve)

    p = websub.add_parser("open", help="start in background and open the browser")
    add_common(p)
    p.set_defaults(func=cmd_open)

    p = websub.add_parser("stop", help="stop a background web UI")
    add_common(p)
    p.set_defaults(func=cmd_stop)

    p = websub.add_parser("status", help="show web UI status")
    add_common(p)
    p.set_defaults(func=cmd_status)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
