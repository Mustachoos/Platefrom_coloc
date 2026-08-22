#!/usr/bin/env bash
# One-shot startup: builds and starts the app. Safe to run every time.
set -euo pipefail
docker compose up --build
