# Tailscale VPN Network — A-SOC Configuration

All three VMs communicate exclusively through the **Tailscale mesh VPN**. No public IPs or port-forwarding needed.

## Network Map

| VM | Role | Tailscale IP |
|----|------|-------------|
| VM1 | TheHive + Cortex | `100.125.10.71` |
| VM2 | Wazuh SIEM | `100.89.154.73` |
| VM3 | Shuffle SOAR | `100.117.88.123` |

> These IPs are examples from the project. Yours will differ — update all config files accordingly.

## Setup on each VM

```bash
# Install
curl -fsSL https://tailscale.com/install.sh | sh

# Authenticate (opens browser URL)
sudo tailscale up

# Verify all peers visible
tailscale status

# Get your IP
tailscale ip -4
```

## Docker → Tailscale routing (VM3 only)

Shuffle runs inside Docker containers. To let those containers call TheHive/Cortex Tailscale IPs, routing must be enabled on the VM3 host:

```bash
# Enable IP forwarding
echo 'net.ipv4.ip_forward = 1' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Allow Docker bridge traffic through tailscale0
sudo iptables -I FORWARD -o tailscale0 -j ACCEPT
sudo iptables -I FORWARD -i tailscale0 -j ACCEPT
sudo iptables -t nat -I POSTROUTING -o tailscale0 -j MASQUERADE

# Persist rules
sudo apt install -y iptables-persistent
sudo netfilter-persistent save

# Accept routes from other Tailscale nodes
sudo tailscale set --accept-routes
```

## Verify connectivity

```bash
# From VM3 host
ping 100.125.10.71

# From inside a Docker container on VM3
docker exec shuffle-backend wget -qO- \
  --header "Authorization: Bearer YOUR_THEHIVE_KEY" \
  http://100.125.10.71:9000/thehive/api/v1/user/current
```
