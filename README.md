# 🛡️ A-SOC — ML-Powered Security Operations Center

> **ENSAM Casablanca** | Cybersecurity & Cloud Computing  
> Supervised by: **Mme Rihab Benaich**  
> Authors: **Yassine El Majouli , Mokaddem Abdennour , Elhamile Hatim ,  Ibrahim gourgaiz**

A fully automated SOC platform that uses **Machine Learning** to detect network attacks and orchestrates the full incident-response pipeline — from detection to case management and analyst notification.

---

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Tailscale VPN Mesh Network                   │
│                                                                 │
│  ┌──────────────────┐      ┌──────────────────┐                 │
│  │   VM2 — Wazuh    │      │  VM3 — Shuffle   │                 │
│  │  100.89.154.73   │────▶│  100.117.88.123   │                │
│  │                  │      │                  │                 │
│  │  • Wazuh Manager │      │  • Shuffle SOAR  │                 │
│  │  • OpenSearch    │      │  • OpenSearch    │                 │
│  │  • Dashboard     │      │    (internal)    │                 │
│  │  • ml_server.py  │      │                  │                 │
│  └──────────────────┘      └────────┬─────────┘                 │
│           ▲                         │                           │
│           │ ML predictions          │ Webhook alerts            │
│           │ (HTTP/Tailscale)        ▼                           │
│  ┌────────┴─────────┐      ┌──────────────────┐                 │
│  │ ML Pipeline      │      │ VM1 — TheHive    │                 │
│  │ (your machine)   │      │  100.125.10.71   │                 │
│  │                  │      │                  │                 │
│  │ • DDoS           │      │ • TheHive  :9000 │                 │
│  │ • PortScan       │      │ • Cortex   :9001 │                 │
│  │ • BruteForce     │      │ • Cassandra      │                 │
│  │ • Bot            │      │ • Elasticsearch  │                 │
│  │ • WebAttack      │      │ • Nginx (TLS)    │                 │
│  └──────────────────┘      └──────────────────┘                 │
│                                                                 │
│              ┌──────────────────────────┐                       │
│              │   Notifications          │                       │
│              │  • Discord (webhook)     │                       │
│              │  • Email (Gmail SMTP)    │                       │
│              └──────────────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
ML Pipeline
    │  JSON predictions (HTTP POST → Tailscale)
    ▼
Wazuh ml_server.py ──▶ /var/log/ml-soc/predictions.log
    │
    ▼  Logcollector watches file
Wazuh Analysisd
    │  Decoder: ml-soc-decoder.xml
    │  Rules:   ml-soc-rules.xml (100099–100601)
    │  MITRE:   T1046, T1110, T1498, T1071, T1190
    ▼
Wazuh Integratord ──▶ Shuffle Webhook
    │                      │
    ▼                      ▼
OpenSearch            Change Me (filter)
ml-soc-alerts              │
    │                 Create Alert (TheHive)
    ▼                      │
Dashboard             POST IP observable
(Visualizations)           │
                      Create Case (TheHive)
                           │
                    ┌──────┴──────┐
                    ▼             ▼
             VirusTotal      AbuseIPDB
              (Cortex)        (Cortex)
                    │             │
                    ▼             ▼
             Get VT Report  Get AbuseIPDB Report
                    └──────┬──────┘
                           ▼
                    Discord + Email notification
```

---

## 🖥️ Virtual Machines

| VM | Role | Tailscale IP | OVA |
|----|------|-------------|-----|
| **VM1** | TheHive + Cortex | `100.125.10.71` | `vm1-thehive-cortex.ova` |
| **VM2** | Wazuh SIEM (All-in-One) | `100.89.154.73` | `vm2-wazuh.ova` |
| **VM3** | Shuffle SOAR | `100.117.88.123` | `vm3-shuffle.ova` |

> OVA files are hosted on :
- [vm1-thehive-cortex](https://github.com/elmajouli-yassine/A-soc_automation_project/tree/master/vm1-thehive-cortex/thehive-cortex_VM.md)
- [vm2-wazuh](https://github.com/elmajouli-yassine/A-soc_automation_project/tree/master/vm2-wazuh/VM-OVA-FORMAT-LINK-MEGA.md)
- [vm3-shuffle](https://github.com/elmajouli-yassine/A-soc_automation_project/tree/master/vm3-shuffle/shuffle-VM.md)
> Default VM credentials: `user: vboxuser` / `pass: 12345678` (change after import).

---

## 📁 Repository Structure

```
a-soc-project/
│
├── README.md                        ← You are here
├── .env.example                     ← Template for all secrets
│
├── vm1-thehive-cortex/              ← VM1: TheHive + Cortex stack
|   |── thehive-cortex_VM.md
│   ├── docker-compose.yml           ← Full stack definition
│   ├── .env.example
│   ├── thehive/
│   │   └── config/
│   │       ├── application.conf     ← TheHive main config
│   │       └── secret.conf.example  ← Secret key template
│   ├── cortex/
│   │   └── config/
│   │       └── application.conf     ← Cortex main config
│   ├── nginx/
│   │   └── conf.d/
│   │       └── thehive-cortex.conf  ← Reverse proxy config
│   └── scripts/
│       ├── setup.sh                 ← First-run setup script
│       └── fix-permissions.sh       ← Fix Cortex job dir perms
│
├── vm2-wazuh/                       ← VM2: Wazuh SIEM
|   |── VM-OVA-FORMAT-LINK-MEGA.md
│   ├── config/
│   │   ├── ossec.conf               ← Wazuh manager config (localfile block)
│   │   ├── decoders/
│   │   │   └── ml-soc-decoder.xml   ← Custom JSON decoder
│   │   └── rules/
│   │       └── ml-soc-rules.xml     ← ML-SOC detection rules + MITRE
│   └── scripts/
│       ├── ml_server.py             ← HTTP server receiving ML predictions
│       ├── ml_index_feeder.py       ← Feeds alerts into OpenSearch index
│       └── create-opensearch-index.sh ← Creates ml-soc-alerts index + mapping
│
├── vm3-shuffle/                     ← VM3: Shuffle SOAR
|   |── shuffle-VM.md
│   ├── docker-compose.yml           ← Shuffle stack definition
│   ├── .env.example
│   ├── config/
│   │   └── workflow-ml-wazuh-thehive.json  ← Exportable Shuffle workflow
│   └── scripts/
│       ├── setup.sh                 ← Install Docker, Tailscale, Shuffle
│       └── configure-iptables.sh    ← Docker → Tailscale routing rules
│
└── docs/
    ├── SETUP-GUIDE.md               ← Step-by-step deployment guide
    ├── TAILSCALE-NETWORK.md         ← VPN mesh configuration
    ├── WAZUH-RULES.md               ← Rules & MITRE mapping reference
    └── SHUFFLE-VARIABLES.md         ← Shuffle workflow variable reference
```

---

## 🚀 Quick Start

### Prerequisites
- VirtualBox or VMware (to import OVAs)
- [Tailscale](https://tailscale.com) account (free)
- VirusTotal API key (free tier)
- AbuseIPDB API key (free tier)
- Discord webhook URL
- Gmail account with App Password enabled

### 1 — Import OVAs
Import all three OVAs into VirtualBox. Start them in order: **VM1 → VM2 → VM3**.

### 2 — Join Tailscale
On each VM:
```bash
sudo tailscale up
# Authenticate via the printed URL
tailscale status   # verify all three VMs are visible
```

### 3 — Configure VM1 (TheHive + Cortex)
```bash
cd vm1-thehive-cortex/
cp .env.example .env && nano .env          # fill in your API keys
bash scripts/setup.sh
docker compose up -d
```
Then open `http://<VM1_IP>:9000/thehive` and complete the org/user setup — see [docs/SETUP-GUIDE.md](docs/SETUP-GUIDE.md).

### 4 — Configure VM2 (Wazuh)
```bash
# Copy custom rules and decoders
sudo cp vm2-wazuh/config/decoders/ml-soc-decoder.xml /var/ossec/etc/decoders/
sudo cp vm2-wazuh/config/rules/ml-soc-rules.xml       /var/ossec/etc/rules/
sudo chmod 640 /var/ossec/etc/decoders/ml-soc-decoder.xml
sudo chmod 640 /var/ossec/etc/rules/ml-soc-rules.xml

# Start the ML prediction receiver
python3 vm2-wazuh/scripts/ml_server.py &

# Create the custom OpenSearch index
bash vm2-wazuh/scripts/create-opensearch-index.sh

# Start the index feeder
python3 vm2-wazuh/scripts/ml_index_feeder.py &
```

### 5 — Configure VM3 (Shuffle)
```bash
cd vm3-shuffle/
cp .env.example .env && nano .env
bash scripts/setup.sh
bash scripts/configure-iptables.sh
docker compose up -d
```
Then import the workflow: Shuffle UI → Workflows → Import → select `config/workflow-ml-wazuh-thehive.json`.  
Update all node URLs and API keys to match your Tailscale IPs.

---

## 🔑 Credentials & Secrets

**Never commit real credentials.** All secrets go in `.env` files (gitignored).  
Copy `.env.example` → `.env` on each VM and fill in your values.

Key secrets needed:
| Secret | Where used |
|--------|-----------|
| `THEHIVE_API_KEY` | Shuffle → TheHive nodes |
| `CORTEX_API_KEY` | Shuffle → Cortex HTTP nodes |
| `VIRUSTOTAL_API_KEY` | Cortex VirusTotal analyzer config |
| `ABUSEIPDB_API_KEY` | Cortex AbuseIPDB analyzer config |
| `DISCORD_WEBHOOK_URL` | Shuffle Discord node |
| `GMAIL_APP_PASSWORD` | Shuffle Email node |

---

## 🧠 ML Attack Classes

| Label | Wazuh Rule | Level | MITRE ATT&CK |
|-------|-----------|-------|-------------|
| Normal | 100100/100101 | 3 | — |
| PortScan | 100200/100201 | 8–10 | T1046 |
| Brute Force | 100300/100301 | 12–14 | T1110 |
| DDoS | 100400/100401 | 14–15 | T1498 |
| Bot | 100500/100501 | 10–13 | T1071 |
| Web Attack | 100600/100601 | 12–14 | T1190 |

---

*A-SOC Project — ENSAM Casablanca 2025–2026*
