#!/usr/bin/env bash
# =============================================================
# ML-SOC | Création de l'index OpenSearch (Wazuh backend)
# =============================================================
# Prérequis :
#   - curl installé
#   - OpenSearch accessible (Wazuh 4.x intègre OpenSearch)
#   - Fichier ml-soc-index-template.json dans le même répertoire
#
# Usage :
#   chmod +x create_ml_soc_index.sh
#   ./create_ml_soc_index.sh
#
#   Avec variables d'env :
#   OS_HOST=192.168.1.10 OS_PORT=9200 ./create_ml_soc_index.sh
# =============================================================

set -euo pipefail

# ── Paramètres de connexion ──────────────────────────────────
OS_HOST="${OS_HOST:-localhost}"
OS_PORT="${OS_PORT:-9200}"
OS_USER="${OS_USER:-admin}"
OS_PASS="${OS_PASS:-jabN8RE?RFACKnf+1Mt*14rppaLJaTAp}"
OS_TLS="${OS_TLS:-true}"          # true = https | false = http

INDEX_NAME="ml-soc-predictions-$(date +%Y.%m)"   # ex: ml-soc-predictions-2026.04
TEMPLATE_NAME="ml-soc-predictions-template"
TEMPLATE_FILE="$(dirname "$0")/ml-soc-index-template.json"

# ── Construction de l'URL ────────────────────────────────────
if [ "$OS_TLS" = "true" ]; then
  BASE_URL="https://${OS_HOST}:${OS_PORT}"
  CURL_TLS="-k"                   # -k = ignore self-signed cert (Wazuh défaut)
else
  BASE_URL="http://${OS_HOST}:${OS_PORT}"
  CURL_TLS=""
fi

CURL_AUTH="-u ${OS_USER}:${OS_PASS}"
CURL_OPTS="${CURL_TLS} ${CURL_AUTH} -s -o /dev/null -w '%{http_code}'"
CURL_OPTS_VERBOSE="${CURL_TLS} ${CURL_AUTH} -s -w '\nHTTP %{http_code}\n'"

# ── Couleurs terminal ────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'
RED='\033[0;31m';   NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC}    $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()  { echo -e "${RED}[ERR]${NC}   $*"; exit 1; }
info() { echo -e "        $*"; }

echo ""
echo "============================================="
echo " ML-SOC | Déploiement index OpenSearch"
echo "============================================="
echo " Host     : ${BASE_URL}"
echo " Index    : ${INDEX_NAME}"
echo " Template : ${TEMPLATE_NAME}"
echo "============================================="
echo ""

# ── 0. Vérifier la connexion ─────────────────────────────────
info "Test de connexion à OpenSearch…"
HTTP_CODE=$(curl ${CURL_TLS} ${CURL_AUTH} -s -o /dev/null -w '%{http_code}' "${BASE_URL}/")
if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 401 ]; then
  ok "OpenSearch accessible (HTTP $HTTP_CODE)"
else
  err "Impossible de joindre OpenSearch (HTTP $HTTP_CODE) — vérifier OS_HOST, OS_PORT, OS_TLS"
fi

# ── 1. Vérifier que le fichier template existe ───────────────
if [ ! -f "$TEMPLATE_FILE" ]; then
  err "Fichier introuvable : $TEMPLATE_FILE"
fi
ok "Template trouvé : $TEMPLATE_FILE"

# ── 2. Enregistrer l'index template ─────────────────────────
info "Enregistrement du template '${TEMPLATE_NAME}'…"

HTTP_CODE=$(curl ${CURL_TLS} ${CURL_AUTH} \
  -s -o /dev/null -w '%{http_code}' \
  -X PUT "${BASE_URL}/_index_template/${TEMPLATE_NAME}" \
  -H "Content-Type: application/json" \
  -d @"${TEMPLATE_FILE}")

case "$HTTP_CODE" in
  200) ok "Template enregistré (HTTP 200)";;
  201) ok "Template créé (HTTP 201)";;
  *) err "Échec enregistrement template (HTTP $HTTP_CODE)";;
esac

# ── 3. Créer l'index pour le mois courant ───────────────────
info "Vérification de l'index '${INDEX_NAME}'…"

HTTP_CODE=$(curl ${CURL_TLS} ${CURL_AUTH} \
  -s -o /dev/null -w '%{http_code}' \
  -X HEAD "${BASE_URL}/${INDEX_NAME}")

if [ "$HTTP_CODE" -eq 200 ]; then
  warn "Index '${INDEX_NAME}' existe déjà — ignoré"
else
  info "Création de l'index '${INDEX_NAME}'…"
  RESPONSE=$(curl ${CURL_TLS} ${CURL_AUTH} \
    -s -w '\nHTTP %{http_code}' \
    -X PUT "${BASE_URL}/${INDEX_NAME}" \
    -H "Content-Type: application/json" \
    -d '{
      "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1
      },
      "aliases": {
        "ml-soc-predictions": {}
      }
    }')

  HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP" | awk '{print $2}')
  if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 201 ]; then
    ok "Index '${INDEX_NAME}' créé (HTTP $HTTP_CODE)"
  else
    err "Échec création index (HTTP $HTTP_CODE)\n$RESPONSE"
  fi
fi

# ── 4. Vérifier le mapping de l'index ───────────────────────
info "Vérification du mapping…"
curl ${CURL_TLS} ${CURL_AUTH} \
  -s "${BASE_URL}/${INDEX_NAME}/_mapping" \
  | python3 -m json.tool --indent 2 2>/dev/null \
  | grep '"type"' \
  | sort -u \
  | sed 's/^/          /'

ok "Mapping vérifié"

# ── 5. Injecter une ligne de test ────────────────────────────
info "Injection d'un document de test…"

TEST_DOC=$(cat <<'EOF'
{
  "@timestamp":   "2026-04-26T12:49:59Z",
  "timestamp":    "2026-04-26T12:49:59Z",
  "inject_ts":    "2026-04-26T12:49:59Z",
  "ml_label":     "PortScan",
  "confidence":   0.9464,
  "src_ip":       "100.67.42.115",
  "src_port":     58039,
  "dst_ip":       "100.123.225.126",
  "dst_port":     80,
  "protocol":     "6",
  "flow_duration": 325449.0,
  "high_confidence": true
}
EOF
)

RESPONSE=$(curl ${CURL_TLS} ${CURL_AUTH} \
  -s -w '\nHTTP %{http_code}' \
  -X POST "${BASE_URL}/${INDEX_NAME}/_doc" \
  -H "Content-Type: application/json" \
  -d "$TEST_DOC")

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP" | awk '{print $2}')
if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 201 ]; then
  ok "Document de test injecté (HTTP $HTTP_CODE)"
else
  warn "Injection test échouée (HTTP $HTTP_CODE) — vérifier les permissions"
fi

# ── 6. Ajouter l'index pattern dans Wazuh Dashboard ─────────
echo ""
echo "============================================="
echo " ÉTAPE MANUELLE — Wazuh Dashboard"
echo "============================================="
echo " 1. Aller dans : Stack Management → Index Patterns"
echo " 2. Créer un pattern : ml-soc-predictions-*"
echo " 3. Champ de temps  : @timestamp"
echo " 4. Sauvegarder"
echo ""
echo " URL directe :"
echo "   https://${OS_HOST}/app/management/kibana/indexPatterns"
echo "============================================="
echo ""

ok "Déploiement terminé"
echo ""
echo " Index actif     : ${INDEX_NAME}"
echo " Alias lecture   : ml-soc-predictions"
echo " Template actif  : ${TEMPLATE_NAME}"
echo ""
