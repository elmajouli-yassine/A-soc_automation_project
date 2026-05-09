# A-SOC — Complete Setup Guide

This guide walks you through deploying the full A-SOC platform from scratch using the three provided OVA virtual machines.

---

## Prerequisites

- **VirtualBox** ≥ 6.1 or **VMware Workstation/Fusion**
- **Tailscale** account (free at tailscale.com)
- API keys: VirusTotal (free), AbuseIPDB (free)
- Discord server with a webhook-enabled channel
- Gmail account with 2-Step Verification + an App Password

---

## Step 1 — Import OVAs

Import each OVA in VirtualBox (**File → Import Appliance**) in this order:

| OVA | RAM recommended |
|-----|----------------|
| `vm1-thehive-cortex.ova` | 8 GB |
| `vm2-wazuh.ova` | 8 GB |
| `vm3-shuffle.ova` | 8 GB |

Default login for all VMs: `vboxuser` / `vboxuser`  
**Change passwords immediately** after first boot.

Set each VM's network adapter to **Bridged** (or NAT with port forwarding) so they can reach the internet for Tailscale authentication.

---

## Step 2 — Join Tailscale on all 3 VMs

On **each VM**, run:

```bash
sudo tailscale up
# Open the printed URL in your browser to authenticate
tailscale status          # should show all 3 VMs
tailscale ip -4           # note each VM's Tailscale IP
```

Update your `.env` files with the real Tailscale IPs before starting any service.

---

## Step 3 — VM1: Start TheHive + Cortex

```bash
cd ~/docker/testing     # or wherever you placed the repo files
cp .env.example .env
nano .env               # fill in ELASTIC_PASSWORD, THEHIVE_SECRET

# Copy secret.conf
cp thehive/config/secret.conf.example thehive/config/secret.conf
nano thehive/config/secret.conf   # paste your openssl key

docker compose up -d
docker compose ps       # all 5 containers should be Up
```

### First-time TheHive setup

1. Open `http://VM1_IP:9000/thehive`
2. Create organization: `ENSAM`
3. Create admin user inside ENSAM org
4. Create `shuffle-user` with profile `SOAR-Analyst` — generate API key → save it

### First-time Cortex setup

1. Open `http://VM1_IP:9001/cortex`
2. Create org: `ENSAM`
3. Create user `yassine` with roles `read, analyze, orgAdmin` → generate API key → save it
4. Go to **Organization → Analyzers** → enable `VirusTotal_GetReport_3_1` and `AbuseIPDB_2_0`
5. Configure each analyzer with your VirusTotal / AbuseIPDB API key

### Link TheHive → Cortex

Edit `thehive/config/application.conf`, replace `${?CORTEX_API_KEY}` or put the key directly, then:

```bash
docker restart thehive
# Verify
docker exec thehive curl -s http://cortex:9001/cortex/api/status
```

---

## Step 4 — VM2: Configure Wazuh

```bash
# Deploy custom decoder and rules
sudo cp config/decoders/ml-soc-decoder.xml /var/ossec/etc/decoders/
sudo cp config/rules/ml-soc-rules.xml       /var/ossec/etc/rules/
sudo chmod 640 /var/ossec/etc/decoders/ml-soc-decoder.xml
sudo chmod 640 /var/ossec/etc/rules/ml-soc-rules.xml
sudo chown root:wazuh /var/ossec/etc/decoders/ml-soc-decoder.xml
sudo chown root:wazuh /var/ossec/etc/rules/ml-soc-rules.xml

# Create log directory
sudo mkdir -p /var/log/ml-soc
sudo chmod 777 /var/log/ml-soc

# Add localfile + integration blocks to ossec.conf
# Edit /var/ossec/etc/ossec.conf and add the blocks from config/ossec.conf
# Replace SHUFFLE_VM_IP and YOUR_WEBHOOK_ID with real values

sudo systemctl restart wazuh-manager

# Start the ML prediction receiver
sudo python3 scripts/ml_server.py &

# Create OpenSearch index
bash scripts/create-opensearch-index.sh

# Start the index feeder
python3 scripts/ml_index_feeder.py &
```

### Test the decoder

```bash
echo '{"timestamp":"2026-05-07T11:00:00+00:00","ml_label":"DDoS","src_ip":"10.10.10.5","src_port":4444,"dst_ip":"192.168.1.1","dst_port":80,"protocol":"6","flow_duration":5000.0,"flow_packets_per_sec":100.0,"flow_bytes_per_sec":2000.0,"source":"ml_pipeline","confidence":0.98}' \
  | /var/ossec/bin/wazuh-logtest
# Should show: rule 100400, level 14, group ddos, MITRE T1498
```

---

## Step 5 — VM3: Start Shuffle

```bash
cp .env.example .env
nano .env               # set OUTER_HOSTNAME to your VM3 Tailscale IP

docker compose up -d
sleep 120               # give OpenSearch time to start
docker compose ps       # all 4 containers should be Up

# Allow Docker to reach Tailscale IPs
bash scripts/configure-iptables.sh
```

### Import the workflow

1. Open `http://VM3_IP:3001` → log in
2. Go to **Workflows** → **Import** → select `config/workflow-ml-wazuh-thehive.json`
3. Open the imported workflow and replace every `<REPLACE_*>` placeholder:
   - VM1 Tailscale IP in all URLs
   - TheHive API key
   - Cortex API key
   - Discord webhook URL
   - Gmail user + app password
4. Click **Save**
5. Activate the workflow (toggle to **Running**)
6. Copy the **Webhook URL** from the Wazuh-webhook node

### Wire Wazuh → Shuffle

Paste the webhook URL into `/var/ossec/etc/ossec.conf` in the `<hook_url>` field, then:

```bash
sudo systemctl restart wazuh-manager
```

---

## Step 6 — End-to-end Test

Send a simulated DDoS event from VM2:

```bash
curl -s -X POST http://localhost:8080/predict \
  -H "Content-Type: application/json" \
  -d '{
    "ml_label":  "DDoS",
    "src_ip":    "185.220.101.5",
    "dst_ip":    "192.168.1.1",
    "src_port":  54321,
    "dst_port":  80,
    "protocol":  "6",
    "confidence": 0.97,
    "flow_duration": 5000.0
  }'
```

Expected chain:
1. `ml_server.py` writes JSON to `/var/log/ml-soc/predictions.log`
2. Wazuh fires rule 100400 (DDoS, level 14)
3. Integratord POSTs to Shuffle webhook
4. Shuffle creates alert + case in TheHive
5. Cortex runs VirusTotal + AbuseIPDB on `185.220.101.5`
6. Discord notification arrives in your channel
7. Email arrives in your inbox

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Shuffle containers can't reach VM1 | Run `configure-iptables.sh` again; verify `tailscale status` |
| Cortex analyzers fail | Run `fix-permissions.sh`; check Docker socket access |
| TheHive can't connect to Cortex | Verify `CORTEX_API_KEY` in `.env`; run `docker restart thehive` |
| Wazuh rules not firing | Check permissions (640, root:wazuh); restart wazuh-manager; test with wazuh-logtest |
| Shuffle SWARM errors | Ensure `SHUFFLE_SWARM_CONFIG=false` in docker-compose.yml |
| OpenSearch won't start | Check `vm.max_map_count=262144` in `/etc/sysctl.conf` |
