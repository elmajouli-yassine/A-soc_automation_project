#!/usr/bin/env bash
# =============================================================
#  VM3 — Shuffle SOAR First-run Setup
#  A-SOC Project — ENSAM Casablanca
# =============================================================
set -euo pipefail

echo "=== [1/6] System update ==="
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git wget nano net-tools

echo "=== [2/6] Install Docker ==="
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER"
fi

echo "=== [3/6] Install Docker Compose plugin ==="
sudo apt install -y docker-compose-plugin
docker compose version

echo "=== [4/6] OpenSearch memory requirement ==="
sudo swapoff -a
sudo sysctl -w vm.max_map_count=262144
if ! grep -q "vm.max_map_count" /etc/sysctl.conf; then
  echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
fi

echo "=== [5/6] OpenSearch data directory ==="
sudo mkdir -p /etc/shuffle/opensearch/data
sudo chmod 777 /etc/shuffle/opensearch/data

echo "=== [6/6] Install Tailscale ==="
if ! command -v tailscale &>/dev/null; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi
sudo tailscale up
echo "Authenticate Tailscale via the URL above, then press Enter."
read -r

echo ""
echo "=== Setup complete! ==="
echo "Next steps:"
echo "  1. cp .env.example .env && nano .env   (set your Tailscale IP)"
echo "  2. docker compose up -d"
echo "  3. bash scripts/configure-iptables.sh  (Docker → Tailscale routing)"
echo "  4. Open http://\$(tailscale ip -4):3001  — Shuffle UI"
