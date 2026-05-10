/
├── var/
│   ├── ossec/
│   │   ├── etc/
│   │   │   ├── ossec.conf                        ← Configuration principale Wazuh
│   │   │   ├── decoders/
│   │   │   │   └── ml-soc-decoder.xml            ← Décodeur JSON personnalisé
│   │   │   └── rules/
│   │   │       └── ml-soc-rules.xml              ← Règles de détection ML-SOC
│   │   └── logs/
│   │       └── alerts/
│   │           └── alerts.json                   ← Alertes générées par Wazuh
│   └── log/
│       └── ml-soc/
│           └── predictions.log                   ← Logs reçus du pipeline ML
│
├── opt/
│   └── ml-soc/
│       ├── ml_server.py                          ← Serveur HTTP Python (port 8080)
│       ├── ml_index_feeder.py                    ← Feeder OpenSearch temps réel
│       └── feeder.pos                            ← Position de lecture alerts.json
│
└── etc/
    └── systemd/system/
        ├── ml-server.service                     ← Service systemd ml_server
        └── ml-feeder.service                     ← Service systemd ml_feeder



## Intégration Shuffle SOAR

### Configuration dans ossec.conf

```xml
<integration>
    <name>shuffle</name>
    <hook_url>http://100.117.88.123:3001/api/v1/hooks/<WEBHOOK_ID></hook_url>
    <rule_id>100200,100201,100300,100301,100400,100401,100500,100501,100600,100601</rule_id>
    <alert_format>json</alert_format>
</integration>
```


# index :  ml-soc-alerts 
# index-pattern : ml-soc-alerts


CONFIG 
NB : pour les fichiers de regles et decoders 
donner les droits 640 (root wazuh others)

UBUNTU CREDENTIALS : 
abdennour/mokaddem

WAZUH CREADENTIALS :
admin/jabN8RE?RFACKnf+1Mt*14rppaLJaTAp


