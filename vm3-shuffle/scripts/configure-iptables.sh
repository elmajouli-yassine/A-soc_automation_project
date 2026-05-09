#!/usr/bin/env bash
# =============================================================
#  Configure iptables so Docker containers can reach
#  Tailscale IPs (VM1 TheHive/Cortex, VM2 Wazuh)
#  A-SOC Project — ENSAM Casablanca
#
#  Run once after Tailscale and Docker are both active.
#  Rules are made persistent via iptables-persistent.
# =============================================================
set -euo pipefail

echo "=== Enabling IP forwarding ==="
if ! grep -q "net.ipv4.ip_forward = 1" /etc/sysctl.conf; then
  echo "net.ipv4.ip_forward = 1" | sudo tee -a /etc/sysctl.conf
fi
sudo sysctl -p

echo "=== Adding iptables rules for Docker → Tailscale ==="
sudo iptables -I FORWARD -o tailscale0 -j ACCEPT
sudo iptables -I FORWARD -i tailscale0 -j ACCEPT
sudo iptables -t nat -I POSTROUTING -o tailscale0 -j MASQUERADE

echo "=== Configuring Tailscale to accept routes ==="
sudo tailscale set --accept-routes

echo "=== Making rules persistent ==="
sudo apt install -y iptables-persistent
sudo netfilter-persistent save

echo ""
echo "=== Done. Docker containers can now reach Tailscale IPs. ==="
echo "Test: docker exec shuffle-backend wget -qO- http://VM1_TAILSCALE_IP:9000/thehive/api/v1/status"
