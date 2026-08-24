# Plan: `localllm` CLI + web UI

## Goal

A `localllm` CLI plus a single-page web UI (FastAPI + Jinja + Tailwind) that manages the
local DFlash2 llama.cpp stack: setup (clone+build), opencode wiring, service start/stop,
logs, system/GPU resources, and uninstall. Installable via `uv tool install` from a git URL
and fully self-contained after install (no separate init step).

## Install & usage

```bash
# installed mode
uv tool install https://github.com/HarrisDePerceptron/llama-cpp-dflash2-qwen3.8
localllm web open      # auto-clones the stack to ~/.local/share/localllm, serves UI, opens browser

# dev mode (inside a checkout of this repo)
uv sync
uv run localllm web open   # uses the current checkout as the instance (reuses existing build)
```

CLI: `localllm web serve | open | stop | status` with `--host`, `--port`, `--home` flags.
`web open` = background daemon + pidfile + readiness poll + `webbrowser.open`.
`web stop` = pidfile first, fallback to psutil scan for the uvicorn process.

## Instance resolution (no init command)

1. `--home` flag / `LOCALLLM_HOME` env var
2. Source-tree detection: if the package's parent dir contains `run.sh` + `service.sh`
   (dev mode), use it
3. `~/.local/share/localllm` (XDG_DATA_HOME-aware): auto-clone from
   `UPSTREAM = https://github.com/HarrisDePerceptron/llama-cpp-dflash2-qwen3.8` if missing

## Layout

```
pyproject.toml             # uv project, hatchling, [project.scripts] localllm
localllm/
  __init__.py
  __main__.py              # python -m localllm
  cli.py                   # argparse CLI
  instance.py              # instance resolution + auto-clone
web/
  __init__.py
  main.py                  # FastAPI app, routes, background Job runner
  system.py                # stats/status collectors (psutil, nvidia-smi, systemctl, journalctl)
  templates/index.html     # single-page Tailwind UI
```

`packages = ["localllm", "web"]` in hatch wheel config so both ship in the wheel.

## Runtime

- Web UI: `127.0.0.1:8002` (model server stays on `:8001`)
- State: `~/.local/state/localllm/web.{pid,log}` (XDG_STATE_HOME-aware)
- Background jobs (setup, opencode-setup): daemon thread + `deque(maxlen=1000)` output
  buffer, polled by the UI; no SSE
- Logs: `journalctl --user -u llama-dflash` tail, polled every 2s
- Opencode version: cached with 300s TTL (avoid spawning node every poll)
- Server config: parse `run.sh` args + live `:8001/health` + `/v1/models` via urllib

## API

| Route | Description |
|---|---|
| `GET /` | single page |
| `GET /api/state` | service status, system+GPU stats, agents, server config, instance info |
| `GET /api/logs?lines=N` | journal tail |
| `POST /api/setup` | run `setup.sh` in background |
| `GET /api/jobs/setup` | job state/output |
| `POST /api/opencode-setup` | run `setup-opencode.sh` in background |
| `GET /api/jobs/opencode` | job state/output |
| `POST /api/service/start` | `service.sh start` |
| `POST /api/service/stop` | `service.sh stop` |
| `POST /api/service/uninstall` | `service.sh remove` + `rm -rf llama.cpp/` + strip `llama-server` provider from opencode config (opencode binary kept); UI confirm dialog |

## UI

Single page, dark theme (zinc-950), six cards: Service, System, Llama server, Agents,
Setup, Logs. Polls `/api/state`, `/api/logs`, and job states every 2s.

## Safety

- The live `llama-dflash` service on :8001 may be serving the current inference session —
  never stop/uninstall it during smoke testing.
- Uninstall is destructive and requires a confirm dialog in the UI.
