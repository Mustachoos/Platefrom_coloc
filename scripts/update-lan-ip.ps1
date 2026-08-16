# Detects this machine's LAN-facing IPv4 address (the adapter that has a
# default gateway configured and is up — i.e. the one actually connected
# to the router, on the same network guests' phones will be on) and writes
# it into a local .env file as QR_HOST_IP.
#
# docker-compose.yml reads QR_HOST_IP from the environment (defaulting to
# empty), and docker compose automatically loads a .env file next to
# docker-compose.yml — so this is the one place the IP needs updating,
# instead of hand-editing docker-compose.yml every time the network changes.
#
# Run this whenever the machine's IP might have changed (new network, new
# router, DHCP renewal), then recreate the web container so it picks up
# the new value: docker compose up -d

$config = Get-NetIPConfiguration | Where-Object {
    $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq 'Up'
} | Select-Object -First 1

if (-not $config) {
    Write-Error "No active network adapter with a default gateway found. Is this machine connected to a network?"
    exit 1
}

$ip = $config.IPv4Address.IPAddress
$envFile = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.env"))

$lines = @()
if (Test-Path $envFile) {
    $lines = Get-Content $envFile | Where-Object { $_ -notmatch '^QR_HOST_IP=' }
}
$lines += "QR_HOST_IP=$ip"
$lines | Set-Content -Path $envFile -Encoding utf8

Write-Host "QR_HOST_IP set to $ip in $envFile"
Write-Host "Run 'docker compose up -d' to apply it (recreates the web container if the IP changed)."
