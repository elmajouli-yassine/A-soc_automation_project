#!/usr/bin/env bash
# =============================================================
#  VM1 — First-run setup script
#  A-SOC Project — TheHive + Cortex
# =============================================================
set -euo pipefail

echo "=== [1/5] System update ==="
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git wget nano net-tools python3-pip

echo "=== [2/5] Install Docker ==="
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER"
  echo "Docker installed. You may need to log out and back in."
fi

echo "=== [3/5] Install Tailscale ==="
if ! command -v tailscale &>/dev/null; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi
sudo tailscale up
echo "Authenticate Tailscale via the URL above, then press Enter."
read -r

echo "=== [4/5] Create required directories ==="
mkdir -p cortex/neurons/analyzers
mkdir -p cortex/neurons/responders
mkdir -p cortex/logs

# Cortex needs to write job results
chmod 777 cortex/logs

echo "=== [5/5] Install Cortex analyzers ==="
if [ ! -d "cortex/neurons/Cortex-Analyzers" ]; then
  git clone https://github.com/TheHive-Project/Cortex-Analyzers.git \
    cortex/neurons/Cortex-Analyzers
  cp -r cortex/neurons/Cortex-Analyzers/analyzers/* cortex/neurons/analyzers/
  cp -r cortex/neurons/Cortex-Analyzers/responders/* cortex/neurons/responders/
fi

echo ""
echo "=== Setup complete! ==="
echo "Next: cp .env.example .env && nano .env"
echo "Then: docker compose up -d"
echo ""
echo "TheHive will be at: http://$(hostname -I | awk '{print $1}'):9000/thehive"
echo "Cortex  will be at: http://$(hostname -I | awk '{print $1}'):9001/cortex"
