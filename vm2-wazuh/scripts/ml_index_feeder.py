#!/usr/bin/env python3
"""
=============================================================
 ml_index_feeder.py — Real-time OpenSearch index feeder
 A-SOC Project — ENSAM Casablanca

 Tails /var/ossec/logs/alerts/alerts.json, filters only
 ML-SOC events, and indexes them into the custom index
 "ml-soc-alerts" with a deduplication key.

 Usage:
   python3 ml_index_feeder.py

 Requires:
   pip install requests
=============================================================
"""

import json
import logging
import os
import time
import urllib3
from pathlib import Path

import requests

# ── Configuration ─────────────────────────────────────────────
ALERTS_FILE   = "/var/ossec/logs/alerts/alerts.json"
POSITION_FILE = "/var/log/ml-soc/feeder.pos"
INDEX_NAME    = "ml-soc-alerts"
OS_URL        = "https://127.0.0.1:9200"
OS_USER       = "admin"
OS_PASS       = os.getenv("OPENSEARCH_PASSWORD", "StrongOpenSearch321!")
ML_LOG_SOURCE = "/var/log/ml-soc/predictions.log"
POLL_INTERVAL = 1  # seconds between file checks

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("ml_feeder")


def load_position() -> int:
    try:
        return int(Path(POSITION_FILE).read_text().strip())
    except (FileNotFoundError, ValueError):
        return 0


def save_position(pos: int):
    Path(POSITION_FILE).parent.mkdir(parents=True, exist_ok=True)
    Path(POSITION_FILE).write_text(str(pos))


def parse_alert(line: str) -> dict | None:
    """Parse one JSON alert line; return None if not an ML-SOC event."""
    try:
        alert = json.loads(line)
    except json.JSONDecodeError:
        return None

    if alert.get("location") != ML_LOG_SOURCE:
        return None

    data = alert.get("data", {})
    rule = alert.get("rule", {})

    wazuh_ts = alert.get("timestamp", "")
    src_ip   = data.get("src_ip", "")
    rule_id  = str(rule.get("id", ""))

    return {
        "_id": f"{wazuh_ts}_{src_ip}_{rule_id}",
        "doc": {
            "wazuh_timestamp": wazuh_ts,
            "timestamp":       data.get("timestamp", wazuh_ts),
            "ml_label":        data.get("ml_label", ""),
            "src_ip":          src_ip,
            "dst_ip":          data.get("dst_ip", ""),
            "src_port":        int(data.get("src_port", 0)),
            "dst_port":        int(data.get("dst_port", 0)),
            "protocol":        data.get("protocol", ""),
            "flow_duration":   float(data.get("flow_duration", 0)),
            "confidence":      float(data.get("confidence", 0)),
            "rule_id":         rule_id,
            "rule_level":      int(rule.get("level", 0)),
            "rule_description": rule.get("description", ""),
            "mitre_id":        (rule.get("mitre", {}).get("id", [None]) or [None])[0],
        },
    }


def index_document(doc_id: str, doc: dict) -> bool:
    url = f"{OS_URL}/{INDEX_NAME}/_doc/{doc_id}"
    try:
        r = requests.put(
            url,
            json=doc,
            auth=(OS_USER, OS_PASS),
            verify=False,
            timeout=10,
        )
        if r.status_code in (200, 201):
            return True
        logger.warning("Index failed (%d): %s", r.status_code, r.text[:200])
        return False
    except requests.RequestException as exc:
        logger.error("OpenSearch request error: %s", exc)
        return False


def tail_and_feed():
    position = load_position()
    logger.info("Starting feeder | position=%d | index=%s", position, INDEX_NAME)

    while True:
        try:
            with open(ALERTS_FILE, "r", encoding="utf-8", errors="replace") as fh:
                fh.seek(position)
                while True:
                    line = fh.readline()
                    if not line:
                        time.sleep(POLL_INTERVAL)
                        break

                    line = line.strip()
                    if not line:
                        continue

                    parsed = parse_alert(line)
                    if parsed:
                        ok = index_document(parsed["_id"], parsed["doc"])
                        if ok:
                            logger.info(
                                "Indexed | id=%-50s label=%s",
                                parsed["_id"],
                                parsed["doc"].get("ml_label"),
                            )

                    position = fh.tell()
                    save_position(position)

        except FileNotFoundError:
            logger.warning("Alerts file not found, retrying in 5s…")
            time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Feeder stopped.")
            break


if __name__ == "__main__":
    tail_and_feed()
