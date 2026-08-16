# One-shot startup: refreshes QR_HOST_IP for whatever network this machine
# is currently on, then builds and starts the app. Safe to run every time —
# if the IP hasn't changed this just rewrites the same value.

& "$PSScriptRoot\update-lan-ip.ps1"
docker compose up --build
