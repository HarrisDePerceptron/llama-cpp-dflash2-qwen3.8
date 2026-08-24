# localllm dashboard redesign

Dark theme + Gemini (ai.google/gemini-for-science) accent palette, modern Tailwind UI/UX,
GPU stats with VRAM breakdown including VRAM used by our model.

## 1. Backend — `web/system.py`

Extend `gpu_stats()`:

- Add `uuid` to the `--query-gpu` field list
  (`index,name,uuid,memory.total,memory.used,utilization.gpu,temperature.gpu,power.draw`).
- Parse 8 parts per line; add `"uuid"` and `"model_mem_mb": 0` to each GPU dict.
- Second call: `nvidia-smi --query-compute-apps=process_name,used_memory,gpu_uuid
  --format=csv,noheader,nounits`.
- For each compute app whose `process_name` contains `llama-server`, add its
  `used_memory` to the matching GPU's `model_mem_mb` (match via `uuid`, skip
  `Not Available`).
- No API shape change: `gpus` stays top-level in `/api/state` (main.py:70).

## 2. Frontend — `web/templates/index.html` (full rewrite)

Keep: Tailwind CDN, all API endpoints, 2s polling, log auto-scroll pinning,
job output rendering, confirm/alert flows.

### Theme (dark + Gemini accents)
- `bg-zinc-950` base, `bg-zinc-900` cards with `border-zinc-800`, `rounded-2xl`,
  subtle shadow; hover: `border-zinc-700`.
- Inline `tailwind.config` extending:
  - fonts: `['"Google Sans"', 'Inter', 'Roboto', 'system-ui', 'sans-serif']`
    (+ load Inter from Google Fonts as fallback), mono stack for code/paths.
  - Gemini colors: blue `#8ab4f8`/`#4285f4`, purple `#b39ddb`/`#a142f4`,
    pink `#f7a1c4`/`#f0509a`? use `#ec407a`-ish, amber `#fdd663`/`#f9ab00`.
- Signature accent: 4-color Gemini "sparkle" gradient
  `linear-gradient(135deg, #4285f4, #a142f4, #ec407a, #f9ab00)` used for:
  logo sparkle, primary progress bars (VRAM model portion, CPU), primary buttons.
- Custom CSS: `.gemini-gradient`, thin scrollbars for log/job panes.

### Layout (`max-w-7xl mx-auto`, `lg:grid-cols-3 gap-5`)
- **Header** (sticky, blur): inline SVG 4-color Gemini sparkle + "localllm"
  wordmark; right: instance path (mono, muted) + overall status pill
  (emerald "all systems go" / amber "degraded" / red "down", derived from
  service.active + server.up).
- **GPU card** (`lg:col-span-2`, the centerpiece): per-GPU block with
  name + index, util % bar, temp, power; VRAM bar split into:
  - model portion: Gemini gradient (width = model_mem_mb / total)
  - other used: zinc-600 (width = (used - model) / total)
  - legend: `model 12.3 GB · other 1.2 GB · free 8.5 GB` (GB, 1 decimal)
  - empty state: "no NVIDIA GPU detected".
- **System card**: CPU bar (gradient), RAM bar, swap row, load avg.
- **Service card**: status dot + `active (enabled)` text; Start (gradient
  primary), Stop (neutral), Uninstall (red ghost, right-aligned); detail pre.
- **Llama server card**: status dot + up/down; rows for url, model, draft,
  ctx/ngl; loaded model ids as pills.
- **Agents card**: opencode version, provider status; Configure button.
- **Setup card**: built/not-built state + Run setup button.
- **Logs card** (`lg:col-span-3`): dark console block
  (`bg-black/60 rounded-xl`), mono, auto-scroll pinning kept.

### JS changes
- `renderSystem(s)` no longer reads `s.gpus` (bug: gpus is top-level, the
  TypeError currently aborts the whole refresh).
- New `renderGpus(gpus)` fed from `state.gpus`.
- `fmtGB(mb)` helper for VRAM legend.
- Status pill helper in `refresh()`.

## 3. Verify
- `uv run python -c "from web import system; print(system.gpu_stats())"`
  (expect `model_mem_mb` key; >0 while llama-server runs).
- Boot app briefly (`uv run uvicorn web.main:app` or existing entrypoint),
  `curl -s localhost:PORT/api/state | python -m json.tool`, open `/` and check
  rendering + no console errors.
