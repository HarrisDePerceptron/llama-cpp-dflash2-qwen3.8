#!/usr/bin/env bash
set -euo pipefail

CONFIG_DIR="$HOME/.config/opencode"
CONFIG="$CONFIG_DIR/opencode.json"
SERVER_URL="http://127.0.0.1:8001"

echo "==> Installing opencode..."
curl -fsSL https://opencode.ai/install | bash

case ":$PATH:" in
    *":$HOME/.opencode/bin:"*) ;;
    *) echo "hint: add \$HOME/.opencode/bin to your PATH" ;;
esac

echo "==> Configuring llama-server provider..."
mkdir -p "$CONFIG_DIR"
python3 - "$CONFIG" <<'EOF'
import json, os, sys

path = sys.argv[1]
provider = {
    "npm": "@ai-sdk/openai-compatible",
    "name": "llama-server (local)",
    "options": {"baseURL": "http://127.0.0.1:8001/v1"},
    "models": {
        "ggml-org/Qwen3.8-27B-GGUF:Q4_K_M": {
            "name": "Qwen3.8 27B Q4_K_M (local)"
        }
    },
}

config = {}
if os.path.exists(path):
    with open(path) as f:
        config = json.load(f)

config.setdefault("$schema", "https://opencode.ai/config.json")
config.setdefault("provider", {})
config["provider"]["llama-server"] = provider

with open(path, "w") as f:
    json.dump(config, f, indent=2)
    f.write("\n")
EOF
echo "==> Merged llama-server provider into $CONFIG"

if curl -sf --max-time 3 "$SERVER_URL/health" >/dev/null; then
    echo "==> Model server is up at $SERVER_URL"
else
    echo "warning: model server not reachable at $SERVER_URL (start it with ./service.sh start)"
fi
