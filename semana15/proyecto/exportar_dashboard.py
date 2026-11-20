# -*- coding: utf-8 -*-
"""exportar_dashboard.py - Descarga el dashboard desde la API de Grafana y lo
guarda como JSON (equivale a Share -> Export -> Save to file)."""
import json
import os
import time

import requests

import config_iot as cfg

# Grafana tarda unos segundos en arrancar: se reintenta durante 90 s
for intento in range(45):
    try:
        r = requests.get(f"{cfg.GRAFANA_URL}/api/dashboards/uid/{cfg.DASHBOARD_UID}",
                         auth=(cfg.GRAFANA_USER, cfg.GRAFANA_PASSWORD), timeout=10)
        if r.status_code == 200:
            break
    except requests.RequestException:
        pass
    time.sleep(2)
else:
    raise SystemExit("[ERROR] Grafana no respondio o el dashboard no se cargo.")
dashboard = r.json()["dashboard"]
dashboard.pop("id", None)
os.makedirs(os.path.join(cfg.CARPETA, "evidencias"), exist_ok=True)
ruta = os.path.join(cfg.CARPETA, "evidencias", "dashboard_exportado.json")
with open(ruta, "w", encoding="utf-8") as f:
    json.dump(dashboard, f, indent=2, ensure_ascii=False)
print(f"[OK] Dashboard '{dashboard['title']}' exportado a {ruta}")
