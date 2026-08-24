#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$DIR/llama.cpp"
REPO=https://github.com/ggml-org/llama.cpp.git
PR=27342
BRANCH=pr-27342

if [ -d "$SRC/.git" ]; then
    echo "==> Existing clone found, updating..."
    git -C "$SRC" fetch origin
    if ! git -C "$SRC" show-ref --verify --quiet "refs/heads/$BRANCH"; then
        git -C "$SRC" fetch origin "pull/$PR/head:$BRANCH"
    fi
    git -C "$SRC" switch "$BRANCH"
else
    echo "==> Cloning $REPO ..."
    git clone "$REPO" "$SRC"
    git -C "$SRC" fetch origin "pull/$PR/head:$BRANCH"
    git -C "$SRC" switch "$BRANCH"
fi

echo "==> On branch: $(git -C "$SRC" branch --show-current) ($(git -C "$SRC" log --oneline -1))"

if [[ "$(uname)" == "Darwin" ]]; then
    BACKEND=GGML_METAL
elif command -v nvidia-smi >/dev/null 2>&1; then
    BACKEND=GGML_CUDA
else
    echo "error: neither nvidia-smi nor macOS detected" >&2
    exit 1
fi
echo "==> Backend: $BACKEND"

cmake -B "$SRC/build" -DCMAKE_BUILD_TYPE=Release -D$BACKEND=ON
cmake --build "$SRC/build" -j

echo "==> Done: $SRC/build/bin/llama-server"
