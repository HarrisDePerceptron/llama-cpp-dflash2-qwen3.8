#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -n "${LLAMA_UNIT:-}" ]; then
    UNIT="$LLAMA_UNIT"
elif [ -d "$DIR/localllm" ] && [ -d "$DIR/web" ]; then
    # source checkout → dev unit
    UNIT="llama-dflash"
else
    # installed/global copy (~/.local/share/localllm) → production unit
    UNIT="llama-dflash-production"
fi

UNIT_FILE="$HOME/.config/systemd/user/$UNIT.service"

warn_conflict() {
    local other
    for other in "$HOME/.config/systemd/user/"llama-dflash*.service; do
        [ -e "$other" ] || continue
        [ "$(basename "$other")" = "$UNIT.service" ] && continue
        if systemctl --user is-active --quiet "$(basename "$other" .service)" 2>/dev/null; then
            echo "warning: $(basename "$other") is active and also binds :8001;" \
                 "stop it before starting $UNIT" >&2
        fi
    done
}

write_unit() {
    mkdir -p "$(dirname "$UNIT_FILE")"
    cat > "$UNIT_FILE" <<EOF
[Unit]
Description=llama.cpp DFlash2 server (Qwen3.8-27B)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$DIR
ExecStart=/bin/bash $DIR/run.sh
Restart=on-failure
RestartSec=10
TimeoutStartSec=300

[Install]
WantedBy=default.target
EOF
}

case "${1:-}" in
    install)
        write_unit
        systemctl --user daemon-reload
        warn_conflict
        if [ "${LLAMA_INSTALL_START:-1}" = "1" ]; then
            systemctl --user enable --now "$UNIT"
        else
            systemctl --user enable "$UNIT"
        fi
        ;;
    start)
        systemctl --user start "$UNIT"
        ;;
    stop)
        systemctl --user stop "$UNIT"
        ;;
    restart)
        systemctl --user restart "$UNIT"
        ;;
    status)
        systemctl --user status "$UNIT" --no-pager
        ;;
    logs)
        if [ "${2:-}" = "--full" ]; then
            journalctl --user -u "$UNIT" --lines=all -f
        else
            journalctl --user -u "$UNIT" -n 0 -f
        fi
        ;;
    remove)
        systemctl --user disable --now "$UNIT" 2>/dev/null || true
        rm -f "$UNIT_FILE"
        systemctl --user daemon-reload
        ;;
    *)
        echo "usage: $0 {install|start|stop|status|logs [--full]|remove}"
        exit 1
        ;;
esac
