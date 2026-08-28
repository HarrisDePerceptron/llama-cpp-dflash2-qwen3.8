# AGENTS.md

Local llama.cpp server (DFlash2 speculative decoding, Qwen3.8-27B Q4_K_M) run as a systemd
user service, plus a `localllm` CLI + FastAPI web UI that manages the stack.

## Safety

- The `llama-dflash` (dev) / `llama-dflash-production` (installed) service on `:8001`
  may be serving the *current* inference session
  (model id `llama-server/ggml-org/Qwen3.8-27B-GGUF:Q4_K_M`). Never stop/remove/uninstall
  the stack while working in this repo.
- Uninstall is destructive: `service.sh remove` + `rm -rf llama.cpp/` + strips the
  `llama-server` provider from `~/.config/opencode/opencode.json`.

## Layout

- `run.sh` — starts `llama-server` on `0.0.0.0:8001`; model + DFlash2 draft flags live here
- `service.sh` — systemd **user** service manager: `install|start|stop|status|logs [--full]|remove`.
  Unit name defaults to `llama-dflash`; override with the `LLAMA_UNIT` env var (the web
  UI sets `llama-dflash-production` for installed instances)
- `setup.sh` — idempotent: clones llama.cpp, checks out branch `pr-27342`, builds (CUDA/Metal)
- `setup-opencode.sh` — installs opencode, merges the `llama-server` provider into `~/.config/opencode/opencode.json`
- `llama.cpp/` — nested git repo (NOT a submodule), pinned to `pr-27342` (the DFlash2 PR).
  Treat it as a vendored dependency: don't edit it; `setup.sh` re-checks-out the branch.
- `localllm/` — CLI (`cli.py`) + instance resolution (`instance.py`)
- `web/` — FastAPI app (`main.py`), stats/status collectors (`system.py`), single-page
  Jinja/Tailwind UI (`templates/index.html`) on port 8002; atomic template primitives live
  in `templates/components/`, while complete feature sections live in `templates/partials/`
- `docs/plans/` — design plans; `.agents/skills/` — repo-local skills (see Skills below)

## Skills

Repo-local skills in `.agents/skills/` (managed by `skills-lock.json`; refresh with
`npx skills update`). Load the matching skill before working in the area:

- UI/design work (`web/templates/index.html`, any frontend changes): `tailwind-design-system`
- Server/API work (`web/main.py`, `web/system.py`, routes, responses): `fastapi`

## Frontend UI

- Put one atomic, reusable primitive per file in `web/templates/components/` (for example,
  button, card, or modal). Compose wrappers with Jinja macros and call blocks; keep API and
  feature state out of components.
- Keep components explicit: prefer one macro per variant (e.g. `button_primary`,
  `button_secondary`, `button_icon`) over a single macro with a `variant` param plus a class
  map. Allow some duplication at the component level — especially Tailwind classes — instead
  of centralizing them.
- Keep styling (Tailwind classes) inside components and the client JS (`web/static/js/`).
  Never bridge styling classes from server to client via `window`; `window.__LLM__` carries
  only runtime data (e.g. the systemd `unit`), never classes.
- Put each complete feature in `web/templates/partials/`. A partial composes components and
  keeps its HTML and feature-specific `<script type="module">` together in the same file.
- `components/modal.html` owns the single shared dialog host, appearance, and inline behavior;
  include it once from `index.html`. Feature modal partials provide only their `<template>` body
  and controller, opening the host through `window.Modal.open(...)`.
- Do not create companion JavaScript files for partials; expose only necessary entry points on
  `window`.
- After frontend changes, compile Jinja templates, syntax-check modules, run `git diff --check`,
  and smoke-test `curl -s localhost:8002/api/state`.

## Dev workflow

```bash
uv sync
uv run localllm web open     # dev mode: this checkout is the instance (reuses existing build)
uv run localllm web status
uv run localllm web stop
```

- Instance resolution order: `--home` flag / `LOCALLLM_HOME` env → source checkout
  (detected via `run.sh` + `service.sh` next to the package) → `~/.local/share/localllm`
  (auto-cloned from the GitHub remote).
- Web UI state: `~/.local/state/localllm/web.{pid,log}` (XDG-aware).
- No test suite, no lint/typecheck config. Verify by running:
  - `curl -s localhost:8001/health` → `{"status":"ok"}`
  - `curl -s localhost:8002/api/state`
  - `uv run python -c "from web import system; print(system.gpu_stats())"`

## Gotchas

- `web/system.py:parse_run_sh` reads `run.sh` by finding the `llama-server` line and
  collecting backslash-continued args; keep that format if you edit `run.sh`.
- Web UI has no build step: Tailwind via CDN, 2s polling of `/api/state` + `/api/logs`,
  background jobs are daemon threads with a 1000-line deque buffer (no SSE).
- `llama.cpp/build/` is a build artifact; after moving the repo or switching llama.cpp
  branches, delete it and re-run `./setup.sh`.
- `setup.sh` hard-fails without `nvidia-smi` (Linux) or macOS.
- Ports: model server `8001`, web UI `8002`.
