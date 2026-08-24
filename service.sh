#!/usr/bin/env bash
set -euo pipefail

UNIT=llama-dflash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_FILE="$HOME/.config/systemd/user/$UNIT.service"

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
        systemctl --user enable --now "$UNIT"
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
