# Shuffle Workflow Variable Reference

## Input Variables (from Wazuh webhook)

| Variable | Description | Example |
|----------|-------------|---------|
| `$exec.text.src_ip` | Source IP | `185.220.101.5` |
| `$exec.text.dst_ip` | Destination IP | `192.168.1.1` |
| `$exec.text.ml_label` | ML classification | `DDoS` |
| `$exec.text.confidence` | ML confidence score | `0.97` |
| `$exec.text.protocol` | Protocol number | `6` |
| `$exec.severity` | Alert severity | `3` |
| `$exec.all_fields.timestamp` | Alert timestamp | `2026-05-06T18:17:00+01:00` |
| `$exec.all_fields.rule.id` | Wazuh rule ID | `100401` |
| `$exec.all_fields.rule.description` | Rule description | `ML-SOC \| CRITICAL DDoS…` |
| `$exec.all_fields.data.src_ip` | Source IP (full path) | `185.220.101.5` |
| `$exec.all_fields.data.ml_label` | ML label (full path) | `DDoS` |

## TheHive Node Variables

| Variable | Description |
|----------|-------------|
| `$create_alert.body._id` | Created alert ID |
| `$create_alert.body.title` | Alert title |
| `$create_case.body._id` | Created case ID |
| `$create_case.body.number` | Case number (#23) |

## Cortex Job Variables (VirusTotal)

| Variable | Description |
|----------|-------------|
| `$run_virustotal.body.id` | Cortex job ID |
| `$get_vt_report.body.status` | Job status (Success/Failure) |
| `$get_vt_report.body.report.full.attributes.last_analysis_results.Antiy-AVL.result` | Antiy result |
| `$get_vt_report.body.report.full.attributes.last_analysis_results.AlienVault.result` | AlienVault result |
| `$get_vt_report.body.report.full.attributes.last_analysis_results.Fortinet.result` | Fortinet result |
| `$get_vt_report.body.report.full.malicious` | Malicious count |
| `$get_vt_report.body.report.full.suspicious` | Suspicious count |
| `$get_vt_report.body.report.full.harmless` | Harmless count |

## Cortex Job Variables (AbuseIPDB)

| Variable | Description |
|----------|-------------|
| `$run_abuseipdb.body.id` | Cortex job ID |
| `$get_abuseipdb_report.body.report.full.values.#.data.abuseConfidenceScore` | Abuse score (0–100) |
| `$get_abuseipdb_report.body.report.full.values.#.data.isTor` | Is Tor exit node |
| `$get_abuseipdb_report.body.report.full.values.#.data.countryName` | Country |
| `$get_abuseipdb_report.body.report.full.values.#.data.countryCode` | Country code |
| `$get_abuseipdb_report.body.report.full.values.#.data.isp` | ISP name |
| `$get_abuseipdb_report.body.report.full.values.#.data.totalReports` | Total reports |

## Known Limitations

- **French accented characters** in variables (e.g. from `rule.description`) cause JSON parsing errors in the Discord node. Use `$exec.all_fields.data.ml_label` and `$exec.all_fields.data.src_ip` instead.
- **Sleep duration**: 30 seconds is sufficient for most Cortex jobs. Increase to 60s if VirusTotal rate-limits you.
