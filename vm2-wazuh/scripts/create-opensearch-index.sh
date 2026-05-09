#!/usr/bin/env bash
# =============================================================
#  Create the custom ml-soc-alerts OpenSearch index
#  Run once after Wazuh/OpenSearch starts.
#
#  Usage: bash create-opensearch-index.sh
# =============================================================
set -euo pipefail

OS_URL="https://127.0.0.1:9200"
OS_USER="admin"
OS_PASS="${OPENSEARCH_PASSWORD:-StrongOpenSearch321!}"
INDEX="ml-soc-alerts"

echo "=== Checking OpenSearch availability ==="
until curl -sk -u "${OS_USER}:${OS_PASS}" "${OS_URL}/_cluster/health" \
      | python3 -m json.tool | grep -q '"status"'; do
  echo "Waiting for OpenSearch…"
  sleep 5
done
echo "OpenSearch is up."

echo "=== Creating index: ${INDEX} ==="
curl -sk -X PUT \
  -u "${OS_USER}:${OS_PASS}" \
  -H "Content-Type: application/json" \
  "${OS_URL}/${INDEX}" \
  -d '{
    "settings": {
      "number_of_shards":   1,
      "number_of_replicas": 0
    },
    "mappings": {
      "properties": {
        "wazuh_timestamp":   { "type": "date" },
        "timestamp":         { "type": "date" },
        "ml_label":          { "type": "keyword" },
        "src_ip":            { "type": "ip" },
        "dst_ip":            { "type": "ip" },
        "src_port":          { "type": "integer" },
        "dst_port":          { "type": "integer" },
        "protocol":          { "type": "keyword" },
        "flow_duration":     { "type": "float" },
        "confidence":        { "type": "float" },
        "rule_id":           { "type": "keyword" },
        "rule_level":        { "type": "integer" },
        "rule_description":  { "type": "text" },
        "mitre_id":          { "type": "keyword" }
      }
    }
  }' | python3 -m json.tool

echo ""
echo "=== Index created successfully ==="
echo "Verify: curl -sk -u ${OS_USER}:*** ${OS_URL}/${INDEX} | python3 -m json.tool"
