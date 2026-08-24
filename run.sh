#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export LD_LIBRARY_PATH="$DIR/llama.cpp/build/bin:$LD_LIBRARY_PATH"

echo "Hello world. loading dfalsh 2 model.."

"$DIR/llama.cpp/build/bin/llama-server" \
    --host 0.0.0.0 \
    --port 8001 \
    --metrics \
    -hf ggml-org/Qwen3.8-27B-GGUF:Q4_K_M \
    -hfd incoai/Qwen3.8-27B-DFlash2-GGUF:Q4_K_M \
    --spec-type draft-dflash \
    --spec-draft-n-max 4 \
    --no-mmproj \
    --ctx-size 70000 \
    --flash-attn on \
    --kv-unified \
    --reasoning on \
    --reasoning-effort low \
    --cache-type-k q4_0 \
    --cache-type-v q4_0 \
    --temp 0.7 \
    --top-p 0.8 \
    --top-k 20 \
    --min-p 0.0 \
    -np 1 \
    -ngl 97 \
    --fit off
