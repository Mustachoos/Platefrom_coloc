#!/usr/bin/env bash
# One-shot startup: refreshes QR_HOST_IP for whatever network this machine
# is currently on, then builds and starts the app. Safe to run every time —
# if the IP hasn't changed this just rewrites the same value.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/update-lan-ip.sh"
docker compose up --build
