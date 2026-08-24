from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.request
from collections import deque
from pathlib import Path

import psutil

MODEL_PORT = 8001
UNIT = "llama-dflash"
_OC_VERSION_TTL = 300
_oc_version_cache: tuple[float, str | None] | None = None
_SPEED_WINDOW_S = 20.0
_SPEED_CUR_WINDOW_S = 3.0
_speed_samples: deque[tuple[float, float, float, float, float]] = deque()
_speed_last_avg: dict[str, float | None] = {"prompt": None, "predict": None}
_speed_last_cur: dict[str, float | None] = {"prompt": None, "predict": None}


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


def _http_get_text(url: str, timeout: float = 2.0) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.read().decode()
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


def _line_continues(line: str) -> bool:
    return line.split(" #", 1)[0].rstrip().endswith("\\")


def _locate_server_block(lines: list[str]) -> tuple[int, int] | None:
    start = next((i for i, l in enumerate(lines) if "llama-server" in l.strip()), None)
    if start is None:
        return None
    end = start
    i = start
    while i + 1 < len(lines) and _line_continues(lines[i]):
        end = i + 1
        i += 1
    return start, end


def parse_run_sh_params(path: Path) -> list[dict]:
    args = parse_run_sh(path)
    params: list[dict] = []
    i = 0
    while i < len(args):
        a = args[i]
        if not a.startswith("-"):
            i += 1
            continue
        if i + 1 < len(args) and not args[i + 1].startswith("-"):
            params.append({"name": a, "value": args[i + 1], "is_flag": False})
            i += 2
        else:
            params.append({"name": a, "value": "", "is_flag": True})
            i += 1
    return params


def server_block_raw(path: Path) -> str:
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return ""
    loc = _locate_server_block(lines)
    return "\n".join(lines[loc[0]:loc[1] + 1]) if loc else ""


def render_server_block(binary_line: str, params: list[dict]) -> list[str]:
    binary = binary_line.rstrip()
    if not params:
        return [binary.rstrip("\\ ").rstrip()]
    if not binary.endswith("\\"):
        binary += " \\"
    out = [binary]
    for idx, p in enumerate(params):
        cont = " \\" if idx < len(params) - 1 else ""
        if p.get("is_flag"):
            out.append(f"    {p['name']}{cont}")
        else:
            out.append(f"    {p['name']} {p['value']}{cont}")
    return out


def write_run_sh_params(path: Path, params: list[dict]) -> None:
    lines = path.read_text().splitlines()
    loc = _locate_server_block(lines)
    if loc is None:
        raise ValueError("llama-server invocation not found in run.sh")
    start, end = loc
    block = render_server_block(lines[start], params)
    path.write_text("\n".join(lines[:start] + block + lines[end + 1:]) + "\n")


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


def server_speed(base: str) -> dict:
    result = {
        "available": False,
        "live": False,
        "prompt_tps": None,
        "predict_tps": None,
        "prompt_tps_avg": None,
        "predict_tps_avg": None,
        "prompt_tokens": None,
        "predict_tokens": None,
        "prompt_tokens_window": None,
        "predict_tokens_window": None,
        "window_s": int(_SPEED_WINDOW_S),
    }
    text = _http_get_text(f"{base}/metrics")
    if text is None:
        return result
    m: dict[str, float] = {}
    for line in text.splitlines():
        if not line.startswith("llamacpp:"):
            continue
        parts = line.split()
        if len(parts) != 2:
            continue
        try:
            m[parts[0]] = float(parts[1])
        except ValueError:
            pass
    if not m:
        return result
    result["available"] = True
    prompt_tokens = int(m.get("llamacpp:prompt_tokens_total", 0))
    predict_tokens = int(m.get("llamacpp:tokens_predicted_total", 0))
    prompt_seconds = m.get("llamacpp:prompt_seconds_total", 0.0)
    predict_seconds = m.get("llamacpp:tokens_predicted_seconds_total", 0.0)
    result["prompt_tokens"] = prompt_tokens
    result["predict_tokens"] = predict_tokens
    now = time.time()
    samples = _speed_samples
    if samples and (
        prompt_tokens < samples[-1][1]
        or predict_tokens < samples[-1][2]
        or prompt_seconds < samples[-1][3]
        or predict_seconds < samples[-1][4]
    ):
        samples.clear()
        _speed_last_avg["prompt"] = None
        _speed_last_avg["predict"] = None
        _speed_last_cur["prompt"] = None
        _speed_last_cur["predict"] = None
    samples.append((now, prompt_tokens, predict_tokens, prompt_seconds, predict_seconds))
    while samples and now - samples[0][0] > _SPEED_WINDOW_S:
        samples.popleft()

    def rate_over(window_s: float) -> tuple[float | None, float | None]:
        if len(samples) < 2:
            return None, None
        new = samples[-1]
        old = None
        for s in samples:
            if new[0] - s[0] <= window_s:
                old = s
                break
        if old is None or old is new:
            return None, None
        d_prompt_time = new[3] - old[3]
        d_predict_time = new[4] - old[4]
        if d_prompt_time <= 0 and d_predict_time <= 0:
            return None, None
        prompt_rate = max(0, new[1] - old[1]) / d_prompt_time if d_prompt_time > 0 else None
        predict_rate = max(0, new[2] - old[2]) / d_predict_time if d_predict_time > 0 else None
        return prompt_rate, predict_rate

    def hold(key: str, rate: float | None, store: dict, field: str) -> None:
        if rate is not None and rate > 0:
            store[key] = rate
            result[field] = round(rate, 2)
        elif store[key] is not None:
            result[field] = round(store[key], 2)

    cur_prompt, cur_predict = rate_over(_SPEED_CUR_WINDOW_S)
    hold("prompt", cur_prompt, _speed_last_cur, "prompt_tps")
    hold("predict", cur_predict, _speed_last_cur, "predict_tps")
    avg_prompt, avg_predict = rate_over(_SPEED_WINDOW_S)
    hold("prompt", avg_prompt, _speed_last_avg, "prompt_tps_avg")
    hold("predict", avg_predict, _speed_last_avg, "predict_tps_avg")
    result["live"] = (cur_prompt is not None and cur_prompt > 0) or (
        cur_predict is not None and cur_predict > 0
    )
    if len(samples) >= 2:
        old, new = samples[0], samples[-1]
        result["prompt_tokens_window"] = max(0, new[1] - old[1])
        result["predict_tokens_window"] = max(0, new[2] - old[2])
    return result


def _hf_cache_dir() -> Path:
    for var, suffix in (
        ("LLAMA_CACHE", ""),
        ("HF_HUB_CACHE", ""),
        ("HUGGINGFACE_HUB_CACHE", ""),
        ("HF_HOME", "hub"),
        ("XDG_CACHE_HOME", "huggingface/hub"),
    ):
        v = os.environ.get(var)
        if v:
            p = Path(v)
            return p / suffix if suffix else p
    return Path.home() / ".cache" / "huggingface" / "hub"


def _hf_repo_info(role: str, repo: str, revision: str | None) -> dict:
    repo_dir = _hf_cache_dir() / ("models--" + repo.replace("/", "--"))
    info = {
        "role": role,
        "repo": repo,
        "revision": revision,
        "found": False,
        "path": str(repo_dir),
        "files": [],
        "total_bytes": 0,
    }
    if not repo_dir.is_dir():
        return info
    sha = None
    refs = repo_dir / "refs"
    for name in ([revision] if revision else []) + ["main"]:
        ref_file = refs / name
        if ref_file.is_file():
            sha = ref_file.read_text().strip()
            break
    snap = repo_dir / "snapshots" / sha if sha else None
    if snap is None or not snap.is_dir():
        return info
    files = []
    for f in sorted(snap.iterdir()):
        if f.suffix != ".gguf" or not f.is_file():
            continue
        try:
            size = f.stat().st_size
        except OSError:
            continue
        files.append({"name": f.name, "size_bytes": size})
    info["found"] = True
    info["files"] = files
    info["total_bytes"] = sum(x["size_bytes"] for x in files)
    return info


def model_weights(instance) -> dict:
    args = parse_run_sh(instance.run_sh)
    models = []
    for i, a in enumerate(args):
        if a in ("-hf", "-hfd") and i + 1 < len(args):
            role = "model" if a == "-hf" else "draft"
            repo, _, revision = args[i + 1].partition(":")
            models.append(_hf_repo_info(role, repo, revision or None))
    return {"cache_dir": str(_hf_cache_dir()), "models": models}


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
