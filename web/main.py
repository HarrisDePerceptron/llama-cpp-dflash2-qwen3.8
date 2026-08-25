from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from collections import deque
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from localllm.instance import resolve_instance
from web import system

app = FastAPI(title="localllm")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


class Job:
    def __init__(self) -> None:
        self.state = "idle"  # idle | running | done | error | stopped
        self.output: deque = deque(maxlen=1000)
        self.returncode: int | None = None
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._stop_requested = False

    def start(self, cmd: list[str] | None = None, cwd: Path | None = None, fn=None) -> bool:
        with self._lock:
            if self.state == "running":
                return False
            self.state = "running"
            self.output.clear()
            self.returncode = None
            self._proc = None
            self._stop_requested = False
        if fn is not None:
            threading.Thread(target=self._run_fn, args=(fn,), daemon=True).start()
        else:
            threading.Thread(target=self._run, args=(cmd, cwd), daemon=True).start()
        return True

    def _emit(self, line: str) -> None:
        with self._lock:
            self.output.append(line)

    def stop(self) -> bool:
        with self._lock:
            proc = self._proc
            if self.state != "running" or proc is None:
                return False
            self._stop_requested = True
        if proc.poll() is not None:
            return False
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError, OSError):
            pass
        deadline = time.time() + 5.0
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError, OSError):
                pass
        return True

    def _run(self, cmd: list[str], cwd: Path) -> None:
        p = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        with self._lock:
            self._proc = p
        assert p.stdout is not None
        for line in p.stdout:
            with self._lock:
                self.output.append(line.rstrip("\n"))
        rc = p.wait()
        with self._lock:
            self.returncode = rc
            if rc == 0:
                self.state = "done"
            elif self._stop_requested:
                self.state = "stopped"
                self.output.append("[localllm] stopped by user")
            else:
                self.state = "error"

    def _run_fn(self, fn) -> None:
        try:
            rc = fn(self._emit)
        except Exception as e:
            self._emit(f"[localllm] error: {e}")
            rc = 1
        rc = 0 if rc is None else rc
        with self._lock:
            self.returncode = rc
            self.state = "done" if rc == 0 else "error"

    def snapshot(self) -> dict:
        with self._lock:
            return {"state": self.state, "returncode": self.returncode, "output": list(self.output)}


setup_job = Job()
opencode_job = Job()
uninstall_job = Job()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    inst = resolve_instance()
    return templates.TemplateResponse(request, "index.html", {"unit": system.unit_for(inst.mode)})


@app.get("/api/state")
def api_state():
    inst = resolve_instance()
    server = system.server_config(inst)
    return {
        "instance": {"path": str(inst.path), "mode": inst.mode, "built": inst.built},
        "service": system.service_status(system.unit_for(inst.mode)),
        "system": system.system_stats(),
        "gpus": system.gpu_stats(),
        "agents": system.agents_info(),
        "server": server,
        "speed": system.server_speed(server["url"]),
        "weights": system.model_weights(inst),
    }


@app.get("/api/logs")
def api_logs(lines: int = Query(200, ge=1, le=2000)):
    inst = resolve_instance()
    return {"lines": system.journal_tail(system.unit_for(inst.mode), lines).splitlines()}


@app.post("/api/setup")
def api_setup():
    inst = resolve_instance()
    return {"started": setup_job.start(["bash", str(inst.setup_sh)], inst.path)}


@app.get("/api/jobs/setup")
def api_job_setup():
    return setup_job.snapshot()


@app.post("/api/opencode-setup")
def api_opencode_setup():
    inst = resolve_instance()
    return {"started": opencode_job.start(["bash", str(inst.setup_opencode_sh)], inst.path)}


@app.get("/api/jobs/opencode")
def api_job_opencode():
    return opencode_job.snapshot()


@app.post("/api/jobs/{name}/stop")
def api_job_stop(name: str):
    job = {"setup": setup_job, "opencode": opencode_job}.get(name)
    if job is None:
        return {"ok": False, "detail": f"unknown job: {name}"}
    return {"ok": job.stop()}


def _svc(inst, action: str, timeout: float) -> tuple[int, str, str]:
    return system._run(
        ["bash", str(inst.service_sh), action],
        timeout=timeout,
        extra_env={"LLAMA_UNIT": system.unit_for(inst.mode)},
    )


@app.post("/api/service/start")
def api_service_start():
    inst = resolve_instance()
    rc, out, err = _svc(inst, "start", timeout=600)
    return {"ok": rc == 0, "detail": err or out}


@app.post("/api/service/stop")
def api_service_stop():
    inst = resolve_instance()
    rc, out, err = _svc(inst, "stop", timeout=120)
    return {"ok": rc == 0, "detail": err or out}


class ParamIn(BaseModel):
    name: str
    value: str = ""
    is_flag: bool = False


class ParamsIn(BaseModel):
    params: list[ParamIn]


@app.get("/api/server/params")
def api_server_params():
    inst = resolve_instance()
    return {
        "params": system.parse_run_sh_params(inst.run_sh),
        "raw": system.server_block_raw(inst.run_sh),
    }


@app.post("/api/server/params")
def api_server_params_save(body: ParamsIn):
    inst = resolve_instance()
    try:
        system.write_run_sh_params(inst.run_sh, [p.model_dump() for p in body.params])
    except Exception as e:
        return {"ok": False, "detail": str(e)}
    return {"ok": True, "detail": "run.sh updated"}


@app.post("/api/server/restart")
def api_server_restart():
    inst = resolve_instance()
    rc, out, err = _svc(inst, "restart", timeout=600)
    return {"ok": rc == 0, "detail": err or out}


@app.post("/api/service/uninstall")
def api_service_uninstall():
    inst = resolve_instance()

    def run(emit) -> int:
        emit("uninstalling…")
        system.uninstall_stack(inst, emit=emit)
        return 0

    return {"started": uninstall_job.start(fn=run)}


@app.get("/api/jobs/uninstall")
def api_job_uninstall():
    return uninstall_job.snapshot()
