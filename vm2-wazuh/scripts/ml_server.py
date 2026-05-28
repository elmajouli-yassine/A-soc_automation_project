#!/usr/bin/env python3
"""
ML-SOC | Serveur HTTP — machine Wazuh
======================================
Reçoit les prédictions JSON via POST HTTP
et les écrit dans /var/log/ml-soc/predictions.log
en temps réel (lu par Wazuh logcollector).

Lancement :
    python3 ml_server.py

Endpoint :
    POST http://<tailscale-ip>:8080/ingest
    GET  http://<tailscale-ip>:8080/health
"""

import json
import logging
import signal
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# ── Configuration ─────────────────────────────────────────
HOST     = "0.0.0.0"
PORT     = 8080
LOG_FILE = "/var/log/ml-soc/predictions.log"

# Tous les champs du JSON output de la pipeline
REQUIRED = {
    "timestamp",
    "ml_label",
    "src_ip",
    "src_port",
    "dst_ip",
    "dst_port",
    "protocol",
    "flow_duration",
    "confidence",
}

CRITICAL = {"DDoS", "Bot", "Brute Force", "Web Attack", "PortScan"}

# ── Logging ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/var/log/ml-soc/server.log", mode="a"),
    ],
)
log = logging.getLogger("ml-soc-server")


def ensure_logfile():
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    if not Path(LOG_FILE).exists():
        Path(LOG_FILE).touch(mode=0o640)
        log.info("Fichier log créé : %s", LOG_FILE)


def write_to_log(record: dict):
    """Écrit une ligne JSON dans le fichier surveillé par Wazuh. Flush immédiat."""
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
    with open(LOG_FILE, "a", encoding="utf-8", buffering=1) as f:
        f.write(line)


class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # désactive les logs HTTP verbeux

    def do_POST(self):
        if self.path != "/ingest":
            self._reply(404, {"error": "utiliser POST /ingest"})
            return

        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            self._reply(400, {"error": "body vide"})
            return

        try:
            body   = self.rfile.read(length)
            record = json.loads(body)
        except json.JSONDecodeError:
            self._reply(400, {"error": "JSON invalide"})
            return

        # Vérification de tous les champs du output pipeline
        missing = REQUIRED - record.keys()
        if missing:
            self._reply(400, {"error": f"champs manquants : {sorted(missing)}"})
            return

        # Validation des types
        errors = []
        if not isinstance(record["src_port"],    (int, float)): errors.append("src_port doit être numérique")
        if not isinstance(record["dst_port"],    (int, float)): errors.append("dst_port doit être numérique")
        if not isinstance(record["flow_duration"],(int, float)): errors.append("flow_duration doit être numérique")
        if not isinstance(record["confidence"],  (int, float)): errors.append("confidence doit être numérique")
        if errors:
            self._reply(400, {"error": errors})
            return

        # Écriture dans le log file → Wazuh
        write_to_log(record)

        # Log console
        label    = record["ml_label"]
        src_ip   = record["src_ip"]
        dst_ip   = record["dst_ip"]
        dst_port = record["dst_port"]
        proto    = record["protocol"]
        duration = record["flow_duration"]
        conf     = record["confidence"]

        if label in CRITICAL:
            log.warning(
                "ALERTE %-12s | %s → %s:%s  proto=%s  dur=%.0f  conf=%.4f",
                label, src_ip, dst_ip, dst_port, proto, duration, conf
            )
        else:
            log.info(
                "Normal         | %s → %s:%s  proto=%s  dur=%.0f  conf=%.4f",
                src_ip, dst_ip, dst_port, proto, duration, conf
            )

        self._reply(200, {"status": "ok", "label": label})

    def do_GET(self):
        if self.path == "/health":
            self._reply(200, {
                "status":    "running",
                "port":      PORT,
                "log_file":  LOG_FILE,
                "endpoint":  f"POST http://0.0.0.0:{PORT}/ingest",
            })
        else:
            self._reply(404, {"error": "not found"})

    def _reply(self, code: int, data: dict):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type",   "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    ensure_logfile()
    server = HTTPServer((HOST, PORT), Handler)
    log.info("Serveur HTTP démarré → http://0.0.0.0:%d/ingest", PORT)
    log.info("Log file Wazuh      → %s", LOG_FILE)
    log.info("Champs attendus     → %s", sorted(REQUIRED))

    def _stop(s, f):
        log.info("Arrêt…")
        server.server_close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT,  _stop)
    server.serve_forever()


if __name__ == "__main__":
    main()
