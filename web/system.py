from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

import psutil

MODEL_PORT = 8001
UNIT = "llama-dflash"
_OC_VERSION_TTL = 300
_oc_version_cache: tuple[float, str | None] | None = None


def _run(cmd: list[str], timeout: float = 10.0) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except (OSError, subprocess.TimeoutExpired):
        return 1, "", "timeout"


def _http_get(url: str, timeout: float = 2.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def system_stats() -> dict:
    vm = psutil.virtual_memory()
    s = psutil.swap_memory()
    try:
        load = list(os.getloadavg())
    except (OSError, AttributeError):
        load = None
    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "cpu_count": psutil.cpu_count(),
        "load_avg": load,
        "mem_total_gb": round(vm.total / 2**30, 1),
        "mem_used_gb": round((vm.total - vm.available) / 2**30, 1),
        "mem_percent": vm.percent,
        "swap_total_gb": round(s.total / 2**30, 1),
        "swap_used_gb": round(s.used / 2**30, 1),
    }


def _num(v: str) -> float | None:
    try:
        return float(v)
    except ValueError:
        return None


def gpu_stats() -> list[dict]:
    if shutil.which("nvidia-smi") is None:
        return []
    rc, out, _ = _run(
        [
            "nvidia-smi",
            "--query-gpu=index,name,uuid,memory.total,memory.used,utilization.gpu,temperature.gpu,power.draw",
            "--format=csv,noheader,nounits",
        ]
    )
    if rc != 0:
        return []
    gpus = []
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 8:
            continue
        gpus.append(
            {
                "index": int(parts[0]),
                "name": parts[1],
                "uuid": parts[2],
                "mem_total_mb": int(_num(parts[3]) or 0),
                "mem_used_mb": int(_num(parts[4]) or 0),
                "util_percent": _num(parts[5]),
                "temp_c": _num(parts[6]),
                "power_w": _num(parts[7]),
                "model_mem_mb": 0,
            }
        )
    rc2, apps_out, _ = _run(
        [
            "nvidia-smi",
            "--query-compute-apps=process_name,used_memory,gpu_uuid",
            "--format=csv,noheader,nounits",
        ]
    )
    if rc2 == 0:
        by_uuid = {g["uuid"]: g for g in gpus if g["uuid"] != "Not Available"}
        for line in apps_out.splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 3:
                continue
            name, mem, uuid = parts[0], _num(parts[1]), parts[2]
            if "llama-server" in name and uuid in by_uuid:
                by_uuid[uuid]["model_mem_mb"] += int(mem or 0)
    return gpus


def service_status() -> dict:
    unit_file = Path.home() / ".config/systemd/user" / f"{UNIT}.service"
    rc, out, _ = _run(["systemctl", "--user", "is-active", UNIT])
    active = out if rc == 0 else "inactive"
    rc2, out2, _ = _run(["systemctl", "--user", "is-enabled", UNIT])
    enabled = out2 if rc2 == 0 else "disabled"
    return {"installed": unit_file.exists(), "active": active, "enabled": enabled}


def journal_tail(lines: int = 200) -> str:
    rc, out, _ = _run(["journalctl", "--user", "-u", UNIT, "-n", str(lines), "--no-pager"])
    return out


def _opencode_version() -> str | None:
    global _oc_version_cache
    now = time.time()
    if _oc_version_cache and now - _oc_version_cache[0] < _OC_VERSION_TTL:
        return _oc_version_cache[1]
    rc, out, _ = _run(["opencode", "--version"], timeout=15)
    v = out or None
    _oc_version_cache = (now, v)
    return v


def agents_info() -> dict:
    cfg = Path.home() / ".config/opencode/opencode.json"
    provider = None
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text())
            provider = data.get("provider", {}).get("llama-server")
        except (json.JSONDecodeError, OSError):
            provider = None
    return {
        "opencode_installed": shutil.which("opencode") is not None,
        "opencode_version": _opencode_version(),
        "provider_configured": provider is not None,
        "provider": provider,
    }


def parse_run_sh(path: Path) -> list[str]:
    try:
        text = path.read_text()
    except OSError:
        return []
    args: list[str] = []
    capturing = False
    for line in text.splitlines():
        stripped = line.strip()
        if not capturing:
            if "llama-server" not in stripped:
                continue
            rest = stripped[stripped.find("llama-server") + len("llama-server") :].strip()
            capturing = True
        else:
            rest = stripped
        if " #" in rest:
            rest = rest.split(" #", 1)[0].strip()
        if rest.endswith("\\"):
            rest = rest[:-1].strip()
        if rest:
            args.extend(rest.split())
        else:
            break
    return args


def server_config(instance) -> dict:
    args = parse_run_sh(instance.run_sh)
    d: dict = {}
    for i, a in enumerate(args):
        if i + 1 >= len(args):
            continue
        if a == "--port":
            d["port"] = int(args[i + 1])
        elif a == "--host":
            d["host"] = args[i + 1]
        elif a == "-hf":
            d["model"] = args[i + 1]
        elif a == "-hfd":
            d["draft"] = args[i + 1]
        elif a == "--ctx-size":
            d["ctx_size"] = int(args[i + 1])
        elif a == "-ngl":
            d["ngl"] = int(args[i + 1])
    base = f"http://127.0.0.1:{d.get('port', MODEL_PORT)}"
    health = _http_get(f"{base}/health")
    models = _http_get(f"{base}/v1/models")
    model_ids = []
    if isinstance(models, dict):
        model_ids = [m.get("id") for m in models.get("data", []) if isinstance(m, dict)]
    return {
        "configured": d,
        "up": health is not None,
        "health": health,
        "model_ids": model_ids,
        "url": base,
    }


def remove_opencode_provider() -> str:
    cfg = Path.home() / ".config/opencode/opencode.json"
    if not cfg.exists():
        return "opencode config not found; nothing to remove"
    try:
        data = json.loads(cfg.read_text())
    except json.JSONDecodeError:
        return "opencode config is not valid JSON; left untouched"
    provider = data.get("provider", {})
    if "llama-server" not in provider:
        return "llama-server provider not present; nothing to remove"
    del provider["llama-server"]
    if not provider:
        data.pop("provider", None)
    cfg.write_text(json.dumps(data, indent=2) + "\n")
    return "removed llama-server provider from opencode config"


def uninstall_stack(instance) -> list[str]:
    steps: list[str] = []
    rc, _, err = _run(["bash", str(instance.service_sh), "remove"], timeout=120)
    steps.append(f"service.sh remove: {'ok' if rc == 0 else (err or 'failed')}")
    if instance.llama_cpp_dir.exists():
        shutil.rmtree(instance.llama_cpp_dir, ignore_errors=True)
        steps.append("removed llama.cpp/")
    steps.append(remove_opencode_provider())
    return steps
