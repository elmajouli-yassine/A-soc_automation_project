#!/usr/bin/env bash
# =============================================================
#  Fix Cortex job directory permissions
#  Run this if Cortex analyzers fail with permission errors
# =============================================================
set -euo pipefail

CORTEX_JOBS_DIR="${1:-./cortex/neurons/jobs}"
mkdir -p "$CORTEX_JOBS_DIR"
sudo chmod 777 "$CORTEX_JOBS_DIR"
sudo chown -R 1000:1000 "$CORTEX_JOBS_DIR"

echo "Permissions fixed on: $CORTEX_JOBS_DIR"
docker restart cortex 2>/dev/null && echo "Cortex restarted." || true
