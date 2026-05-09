#!/usr/bin/env python3
"""
=============================================================
 ml_server.py — ML Prediction Receiver
 A-SOC Project — ENSAM Casablanca

 Listens on Tailscale interface (port 8080) for JSON
 predictions from the ML pipeline, then appends each event
 to the Wazuh-monitored log file.

 Usage:
   sudo python3 ml_server.py [--host 0.0.0.0] [--port 8080]

 Wazuh Logcollector watches: /var/log/ml-soc/predictions.log
=============================================================
"""

import argparse
import json
import logging
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

LOG_FILE   = "/var/log/ml-soc/predictions.log"
LOG_DIR    = os.path.dirname(LOG_FILE)
VALID_LABELS = {
    "Normal", "BENIGN",
    "PortScan",
    "BruteForce", "Brute Force", "FTP-BruteForce", "SSH-BruteForce",
    "DDoS", "DoS", "DoS Hulk", "DoS GoldenEye",
    "DoS slowloris", "DoS Slowhttptest",
    "Bot",
    "Web Attack", "Web Attack – Brute Force",
    "Web Attack – XSS", "Web Attack – Sql Injection",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("ml_server")


def ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def append_to_log(record: dict):
    """Write one JSON line to the prediction log (Wazuh reads it)."""
    with open(LOG_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


class MLHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        logger.info(fmt % args)

    def _send(self, code: int, body: dict):
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        if self.path != "/predict":
            self._send(404, {"error": "Not found"})
            return

        try:
            length  = int(self.headers.get("Content-Length", 0))
            raw     = self.rfile.read(length)
            data    = json.loads(raw)
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("Bad JSON payload: %s", exc)
            self._send(400, {"error": "Invalid JSON"})
            return

        # ── Validate required fields ──────────────────────────
        required = {"ml_label", "src_ip", "dst_ip", "src_port",
                    "dst_port", "protocol", "confidence"}
        missing = required - data.keys()
        if missing:
            self._send(400, {"error": f"Missing fields: {missing}"})
            return

        # ── Enrich with server-side timestamp ─────────────────
        data.setdefault("timestamp",
                        datetime.now(timezone.utc).isoformat())
        data.setdefault("source", "ml_pipeline")

        label = data.get("ml_label", "")
        if label not in VALID_LABELS:
            logger.warning("Unknown label received: %s", label)

        append_to_log(data)
        logger.info("Event logged | label=%-20s src=%s → dst=%s:%s conf=%.3f",
                    label,
                    data.get("src_ip"),
                    data.get("dst_ip"),
                    data.get("dst_port"),
                    float(data.get("confidence", 0)))

        self._send(200, {"status": "ok", "label": label})

    def do_GET(self):
        """Health check endpoint."""
        if self.path == "/health":
            self._send(200, {"status": "running", "log": LOG_FILE})
        else:
            self._send(404, {"error": "Not found"})


def main():
    parser = argparse.ArgumentParser(description="ML-SOC prediction receiver")
    parser.add_argument("--host", default="0.0.0.0",
                        help="Bind address (default: 0.0.0.0 for all interfaces)")
    parser.add_argument("--port", type=int, default=8080,
                        help="Listening port (default: 8080)")
    args = parser.parse_args()

    ensure_log_dir()
    server = HTTPServer((args.host, args.port), MLHandler)
    logger.info("ML-SOC server listening on %s:%d", args.host, args.port)
    logger.info("Writing predictions to: %s", LOG_FILE)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
