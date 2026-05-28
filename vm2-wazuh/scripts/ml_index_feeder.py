#!/usr/bin/env python3
"""
ML-SOC | Index Feeder
======================
Lit alerts.json en temps réel, filtre les alertes ML-SOC
et les envoie dans OpenSearch index 'ml-soc-alerts'.
Sans doublons grâce au _id unique + position file.
"""

import json
import time
import logging
import sys
import urllib.request
import urllib.error
import urllib.parse
import ssl
import base64
from pathlib import Path

# ── Configuration ─────────────────────────────────────────
ALERTS_FILE   = "/var/ossec/logs/alerts/alerts.json"
OS_URL        = "https://127.0.0.1:9200"
OS_INDEX      = "ml-soc-alerts"
OS_USER       = "admin"
OS_PASS       = "jabN8RE?RFACKnf+1Mt*14rppaLJaTAp"
ML_SOC_SOURCE = "/var/log/ml-soc/predictions.log"
POLL_INTERVAL = 0.5
POSITION_FILE = "/var/log/ml-soc/feeder.pos"

# ── Logging ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("ml-index-feeder")

# ── SSL + Auth ────────────────────────────────────────────
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

credentials = base64.b64encode(f"{OS_USER}:{OS_PASS}".encode()).decode()
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {credentials}"
}


def send_to_opensearch(doc: dict) -> bool:
    """Envoie un document dans OpenSearch avec _id unique pour éviter doublons."""
    # ID unique basé sur timestamp + src_ip + rule_id
    raw_id  = f"{doc.get('wazuh_timestamp','')}_{doc.get('src_ip','')}_{doc.get('rule_id','')}"
    doc_id  = urllib.parse.quote(raw_id, safe='')
    url     = f"{OS_URL}/{OS_INDEX}/_doc/{doc_id}"
    body    = json.dumps(doc).encode("utf-8")
    req     = urllib.request.Request(url, data=body, headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=5) as resp:
            result = json.loads(resp.read())
            return result.get("result") in ("created", "updated")
    except urllib.error.URLError as e:
        log.error("OpenSearch error: %s", e)
        return False


def parse_alert(line: str) -> dict | None:
    """Parse une ligne JSON de alerts.json et retourne un doc ML-SOC ou None."""
    try:
        alert = json.loads(line.strip())
    except json.JSONDecodeError:
        return None

    # Filtre — uniquement les alertes venant de predictions.log
    if alert.get("location") != ML_SOC_SOURCE:
        return None

    data  = alert.get("data", {})
    rule  = alert.get("rule", {})
    mitre = rule.get("mitre", {})

    return {
        "wazuh_timestamp":  alert.get("timestamp"),
        "timestamp":        data.get("timestamp"),
        "ml_label":         data.get("ml_label"),
        "src_ip":           data.get("src_ip"),
        "dst_ip":           data.get("dst_ip"),
        "src_port":         int(data.get("src_port", 0)),
        "dst_port":         int(data.get("dst_port", 0)),
        "protocol":         data.get("protocol"),
        "flow_duration":    float(data.get("flow_duration", 0)),
        "confidence":       float(data.get("confidence", 0)),
        "rule_id":          rule.get("id"),
        "rule_level":       rule.get("level"),
        "rule_description": rule.get("description"),
        "mitre_id":         mitre.get("id", []),
    }


def tail_forever(filepath: str):
    """Lit le fichier en temps réel en sauvegardant la position."""
    log.info("Lecture de %s en temps réel...", filepath)

    # Lire la dernière position sauvegardée
    last_pos = 0
    if Path(POSITION_FILE).exists():
        try:
            last_pos = int(Path(POSITION_FILE).read_text().strip())
            log.info("Reprise depuis position : %d", last_pos)
        except Exception:
            last_pos = 0
    else:
        # Première fois → aller à la fin du fichier
        last_pos = Path(filepath).stat().st_size
        log.info("Première exécution → position fin : %d", last_pos)

    with open(filepath, "r", encoding="utf-8") as f:
        f.seek(last_pos)
        while True:
            line = f.readline()
            if line:
                pos = f.tell()
                Path(POSITION_FILE).write_text(str(pos))
                yield line
            else:
                time.sleep(POLL_INTERVAL)


def main():
    log.info("ML-SOC Index Feeder démarré")
    log.info("Source  : %s", ALERTS_FILE)
    log.info("Index   : %s/%s", OS_URL, OS_INDEX)
    log.info("Filtre  : location = %s", ML_SOC_SOURCE)

    for line in tail_forever(ALERTS_FILE):
        doc = parse_alert(line)
        if doc is None:
            continue

        label = doc.get("ml_label", "?")
        src   = doc.get("src_ip", "?")
        lvl   = doc.get("rule_level", "?")
        conf  = doc.get("confidence", 0)

        if send_to_opensearch(doc):
            log.info("✅ Indexé | %-12s | %-15s | level=%-2s | conf=%.4f",
                     label, src, lvl, conf)
        else:
            log.error("❌ Échec  | %-12s | %-15s", label, src)


if __name__ == "__main__":
    main()
