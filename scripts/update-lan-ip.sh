#!/usr/bin/env bash
# macOS/Linux equivalent of update-lan-ip.ps1: detects this machine's
# LAN-facing IPv4 address (the interface actually used to reach the
# network, i.e. the one with the default route — same guests' phones are
# on) and writes it into a local .env file as QR_HOST_IP.
#
# docker-compose.yml reads QR_HOST_IP from the environment (defaulting to
# empty), and docker compose automatically loads a .env file next to
# docker-compose.yml — so this is the one place the IP needs updating,
# instead of hand-editing docker-compose.yml every time the network changes.
#
# Run this whenever the machine's IP might have changed (new network, new
# router, DHCP renewal), then recreate the web container so it picks up
# the new value: docker compose up -d

set -euo pipefail

detect_ip() {
  if command -v ip >/dev/null 2>&1; then
    # Linux (iproute2): "ip route get" reports the source address the
    # kernel would actually use to reach that destination.
    ip route get 1.1.1.1 2>/dev/null | awk '{for (i=1;i<=NF;i++) if ($i=="src") print $(i+1)}' | head -n1
  elif [ "$(uname -s)" = "Darwin" ] && command -v route >/dev/null 2>&1; then
    # macOS: find the interface for the default route, then its IPv4.
    iface=$(route get 1.1.1.1 2>/dev/null | awk '/interface: /{print $2}')
    if [ -n "${iface:-}" ]; then
      ipconfig getifaddr "$iface" 2>/dev/null
    fi
  fi
}

IP="$(detect_ip || true)"

if [ -z "${IP:-}" ]; then
  echo "Could not detect a LAN IP automatically. Is this machine connected to a network?" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

if [ -f "$ENV_FILE" ]; then
  grep -v '^QR_HOST_IP=' "$ENV_FILE" > "$ENV_FILE.tmp" 2>/dev/null || true
  mv "$ENV_FILE.tmp" "$ENV_FILE"
fi
echo "QR_HOST_IP=$IP" >> "$ENV_FILE"

echo "QR_HOST_IP set to $IP in $ENV_FILE"
echo "Run 'docker compose up -d' to apply it (recreates the web container if the IP changed)."
