# llama-cpp-dflash2

Local [llama.cpp](https://github.com/ggml-org/llama.cpp) server with **DFlash2 speculative decoding** running **Qwen3.8-27B (Q4_K_M)**, managed as a systemd user service and wired into [opencode](https://opencode.ai) as a local model provider.

## Layout

```
.
├── llama.cpp/           # nested git repo: llama.cpp @ DFlash2 PR branch + local commits
│   └── build/           # CMake build output (bin/llama-server, libggml-*.so)
├── run.sh               # starts llama-server (port 8001)
├── service.sh           # systemd user-service manager
├── setup.sh             # clone + checkout + build llama.cpp
├── setup-opencode.sh    # install opencode + register local provider
└── .gitignore           # ignores llama.cpp/ (nested repo)
```

The `llama.cpp/` directory is a **nested git repo** (not a submodule): it keeps its own `.git` with the upstream remote plus local DFlash2 work on branch `pr-27342`. This repo tracks only the scripts.

## Prerequisites

- Linux (NVIDIA GPU) or macOS (Apple Silicon)
- `git`, `cmake`, `curl`, `python3`
- C/C++ toolchain (GCC/Clang) and, for CUDA: NVIDIA drivers + CUDA toolkit
- systemd (for the service)

## Quick start

```bash
# 1. Clone + checkout DFlash2 branch + build the server
./setup.sh

# 2. Install + start the systemd user service (auto-starts at boot/login)
./service.sh install

# 3. Install opencode and register the local provider
./setup-opencode.sh
```

Verify:

```bash
./service.sh status
curl -s localhost:8001/health   # {"status":"ok"}
```

## Scripts

### `setup.sh`

Clones `ggml-org/llama.cpp` into `llama.cpp/`, fetches PR 27342 into branch `pr-27342`, and builds `llama-server`.

- Auto-detects backend: `nvidia-smi` present → `GGML_CUDA=ON`, macOS → `GGML_METAL=ON`
- Idempotent: an existing clone is fetched/switched, not re-cloned. Your local `pr-27342` branch (with local DFlash2 commits) is never overwritten by upstream fetches.
- Rebuilds into `llama.cpp/build/` (Release).

### `service.sh`

Manages the `llama-dflash` systemd **user** service.

| Command | Action |
| --- | --- |
| `./service.sh install` | Write unit file, `daemon-reload`, enable + start (auto-starts at boot/login via linger) |
| `./service.sh start` | Start the service |
| `./service.sh stop` | Stop the service |
| `./service.sh status` | Show service status |
| `./service.sh logs` | Tail live logs (new entries only) |
| `./service.sh logs --full` | Print full log history, then keep tailing |
| `./service.sh remove` | Disable + stop, delete the unit file, `daemon-reload` |

Notes:

- The unit runs `run.sh` with `WorkingDirectory` set to this repo root, `Restart=on-failure`, `RestartSec=10`, `TimeoutStartSec=300`.
- Requires `Linger=yes` for the user so the service starts at boot: `loginctl enable-linger $USER`.
- The unit file is written to `~/.config/systemd/user/llama-dflash.service`.

### `run.sh`

Starts the server. Key settings:

- Model: `-hf ggml-org/Qwen3.8-27B-GGUF:Q4_K_M` (target)
- Draft: `-hfd incoai/Qwen3.8-27B-DFlash2-GGUF:Q4_K_M` with `--spec-type draft-dflash --spec-draft-n-max 3`
- `--ctx-size 70000`, `--flash-attn on`, `--kv-unified`, quantized KV cache (`q4_0`), `-ngl 97`
- Listens on `0.0.0.0:8001`
- Sets `LD_LIBRARY_PATH` to `llama.cpp/build/bin` so the binary finds `libggml-*.so` after the repo move (the baked-in RUNPATH is absolute).

Models are downloaded from Hugging Face on first run into the default cache.

### `setup-opencode.sh`

- Installs/updates opencode: `curl -fsSL https://opencode.ai/install | bash`
- Merges the `llama-server` provider into `~/.config/opencode/opencode.json` (creates it if missing, preserves other providers):

  ```json
  "llama-server": {
    "npm": "@ai-sdk/openai-compatible",
    "name": "llama-server (local)",
    "options": { "baseURL": "http://127.0.0.1:8001/v1" },
    "models": {
      "ggml-org/Qwen3.8-27B-GGUF:Q4_K_M": { "name": "Qwen3.8 27B Q4_K_M (local)" }
    }
  }
  ```

- Warns if the model server isn't reachable on port 8001.

## Using the model in opencode

Select the model as:

```
llama-server/ggml-org/Qwen3.8-27B-GGUF:Q4_K_M
```

## Rebuilding

If you move the repo or change the branch, the CMake cache (absolute paths) may go stale. Delete `llama.cpp/build/` and re-run `./setup.sh`.

## Uninstall

```bash
./service.sh remove     # stop + remove the service
rm -rf llama.cpp/       # remove the nested repo + build
```
