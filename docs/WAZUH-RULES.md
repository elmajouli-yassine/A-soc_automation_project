# Wazuh ML-SOC Rules Reference

## Rule Hierarchy

```
100099 (parent — all ML-SOC events)
  ├── 100100 / 100101  Normal / BENIGN        level 3
  ├── 100200 / 100201  PortScan               level 8 / 10   T1046
  ├── 100300 / 100301  BruteForce             level 12 / 14  T1110
  ├── 100400 / 100401  DDoS                   level 14 / 15  T1498
  ├── 100500 / 100501  Bot                    level 10 / 13  T1071
  └── 100600 / 100601  Web Attack             level 12 / 14  T1190
```

The `*01` variant fires when `data.confidence ≥ 0.90`.

## MITRE ATT&CK Mapping

| Rule IDs | Attack Type | Technique | Tactic |
|----------|------------|-----------|--------|
| 100200–100201 | PortScan | T1046 — Network Service Scanning | Discovery |
| 100300–100301 | Brute Force | T1110 — Brute Force | Credential Access |
| 100400–100401 | DDoS | T1498 — Network Denial of Service | Impact |
| 100500–100501 | Bot | T1071 — Application Layer Protocol | Command & Control |
| 100600–100601 | Web Attack | T1190 — Exploit Public-Facing Application | Initial Access |

## Testing Rules

```bash
# DDoS test
echo '{"timestamp":"2026-01-01T00:00:00Z","ml_label":"DDoS","src_ip":"1.2.3.4","dst_ip":"192.168.1.1","src_port":1234,"dst_port":80,"protocol":"6","confidence":0.98,"flow_duration":5000,"source":"ml_pipeline"}' \
  | /var/ossec/bin/wazuh-logtest

# PortScan test
echo '{"timestamp":"2026-01-01T00:00:00Z","ml_label":"PortScan","src_ip":"10.0.0.1","dst_ip":"192.168.1.1","src_port":54321,"dst_port":443,"protocol":"6","confidence":0.75,"flow_duration":100,"source":"ml_pipeline"}' \
  | /var/ossec/bin/wazuh-logtest
```

## Which rules trigger Shuffle?

Only rules with level ≥ 8 are forwarded to Shuffle (configured in `ossec.conf` `<integration>` block):

```
100200, 100201  PortScan
100300, 100301  BruteForce
100400, 100401  DDoS
100500, 100501  Bot
100600, 100601  Web Attack
```

Normal traffic (100100/100101, level 3) is logged but does **not** trigger Shuffle.
