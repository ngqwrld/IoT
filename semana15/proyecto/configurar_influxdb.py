# -*- coding: utf-8 -*-
"""
configurar_influxdb.py
Realiza la configuracion inicial (onboarding) de InfluxDB 2 por medio de su API:
crea el usuario administrador, la organizacion, el bucket y un token fijo.
Solo usa la libreria estandar de Python (urllib), no necesita instalar nada.
"""
import json
import time
import urllib.request
import urllib.error

from config_iot import (INFLUX_URL, INFLUX_ORG, INFLUX_BUCKET,
                        INFLUX_TOKEN, INFLUX_USER, INFLUX_PASSWORD)


def peticion(metodo, ruta, cuerpo=None):
    """Envia una peticion HTTP a InfluxDB y devuelve (codigo, json)."""
    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    req = urllib.request.Request(INFLUX_URL + ruta, data=datos, method=metodo,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            texto = r.read().decode("utf-8")
            return r.status, (json.loads(texto) if texto else {})
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode("utf-8", "ignore")}


def esperar_influx(max_segundos=60):
    """Espera a que InfluxDB responda en /health (tarda unos segundos en arrancar)."""
    print("[INFO] Esperando a que InfluxDB arranque...")
    inicio = time.time()
    while time.time() - inicio < max_segundos:
        try:
            codigo, _ = peticion("GET", "/health")
            if codigo == 200:
                print("[OK] InfluxDB esta en linea en", INFLUX_URL)
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


if __name__ == "__main__":
    if not esperar_influx():
        print("[ERROR] InfluxDB no respondio. Verifica que la ventana de InfluxDB este abierta.")
        raise SystemExit(1)

    # Si 'allowed' es False, la configuracion inicial ya se hizo antes.
    _, estado = peticion("GET", "/api/v2/setup")
    if not estado.get("allowed", False):
        print("[OK] InfluxDB ya estaba configurado. No se hizo ningun cambio.")
        raise SystemExit(0)

    cuerpo = {
        "username": INFLUX_USER,
        "password": INFLUX_PASSWORD,
        "org": INFLUX_ORG,
        "bucket": INFLUX_BUCKET,
        "retentionPeriodSeconds": 0,   # 0 = retencion infinita (no se borra el historico)
        "token": INFLUX_TOKEN,
    }
    codigo, resp = peticion("POST", "/api/v2/setup", cuerpo)
    if codigo in (200, 201):
        print("[OK] Configuracion inicial completa:")
        print(f"     Usuario: {INFLUX_USER}  | Organizacion: {INFLUX_ORG}  | Bucket: {INFLUX_BUCKET}")
    else:
        print("[ERROR] No se pudo configurar InfluxDB:", codigo, resp)
        raise SystemExit(1)
