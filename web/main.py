from __future__ import annotations

import subprocess
import threading
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
        self.state = "idle"  # idle | running | done | error
        self.output: deque = deque(maxlen=1000)
        self.returncode: int | None = None
        self._lock = threading.Lock()

    def start(self, cmd: list[str], cwd: Path) -> bool:
        with self._lock:
            if self.state == "running":
                return False
            self.state = "running"
            self.output.clear()
            self.returncode = None
        threading.Thread(target=self._run, args=(cmd, cwd), daemon=True).start()
        return True

    def _run(self, cmd: list[str], cwd: Path) -> None:
        p = subprocess.Popen(
            cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        assert p.stdout is not None
        for line in p.stdout:
            with self._lock:
                self.output.append(line.rstrip("\n"))
        rc = p.wait()
        with self._lock:
            self.returncode = rc
            self.state = "done" if rc == 0 else "error"

    def snapshot(self) -> dict:
        with self._lock:
            return {"state": self.state, "returncode": self.returncode, "output": list(self.output)}


setup_job = Job()
opencode_job = Job()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/api/state")
def api_state():
    inst = resolve_instance()
    server = system.server_config(inst)
    return {
        "instance": {"path": str(inst.path), "mode": inst.mode, "built": inst.built},
        "service": system.service_status(),
        "system": system.system_stats(),
        "gpus": system.gpu_stats(),
        "agents": system.agents_info(),
        "server": server,
        "speed": system.server_speed(server["url"]),
        "weights": system.model_weights(inst),
    }


@app.get("/api/logs")
def api_logs(lines: int = Query(200, ge=1, le=2000)):
    return {"lines": system.journal_tail(lines).splitlines()}


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


@app.post("/api/service/start")
def api_service_start():
    inst = resolve_instance()
    rc, out, err = system._run(["bash", str(inst.service_sh), "start"], timeout=600)
    return {"ok": rc == 0, "detail": err or out}


@app.post("/api/service/stop")
def api_service_stop():
    inst = resolve_instance()
    rc, out, err = system._run(["bash", str(inst.service_sh), "stop"], timeout=120)
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
    rc, out, err = system._run(["bash", str(inst.service_sh), "restart"], timeout=600)
    return {"ok": rc == 0, "detail": err or out}


@app.post("/api/service/uninstall")
def api_service_uninstall():
    inst = resolve_instance()
    return {"ok": True, "steps": system.uninstall_stack(inst)}
