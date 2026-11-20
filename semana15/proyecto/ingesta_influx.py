# -*- coding: utf-8 -*-
"""
ingesta_influx.py - Flujo ESP8266 -> Adafruit IO -> InfluxDB

1) Al arrancar importa el historico REAL que Adafruit IO conserva de los
   ultimos dias (con la fecha original de cada dato).
2) Despues consulta cada 10 s el ultimo valor de cada feed y lo escribe en
   InfluxDB solo si es un dato nuevo (se compara el campo created_at, mejora
   propuesta en las conclusiones de la Semana 14 para no duplicar lecturas).
"""
import time
from datetime import datetime, timedelta, timezone

import requests
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

import config_iot as cfg

AIO_KEY = cfg.obtener_aio_key()
BASE_URL = f"https://io.adafruit.com/api/v2/{cfg.AIO_USERNAME}/feeds"
HEADERS = {"X-AIO-Key": AIO_KEY}


def a_fecha(texto):
    """Convierte '2026-11-13T15:53:17Z' en datetime con zona UTC."""
    return datetime.fromisoformat(texto.replace("Z", "+00:00")).astimezone(timezone.utc)


RANGOS_VALIDOS = {"temperatura": (0.5, 80.0), "humedad": (1.0, 100.0), "luminosidad": (0.0, 1024.0)}


def es_valido(feed, valor):
    """Descarta lecturas imposibles (fallos del DHT11 al conectarlo, ruido, etc.)."""
    minimo, maximo = RANGOS_VALIDOS.get(feed, (float("-inf"), float("inf")))
    return minimo <= float(valor) <= maximo


def crear_punto(feed, valor, fecha):
    """Arma un punto de InfluxDB: measurement 'ambiente', etiquetas del aula y un campo."""
    return (Point(cfg.MEDICION)
            .tag("aula", cfg.AULA_REAL)
            .tag("dispositivo", "nodemcu_esp8266")
            .tag("fuente", "adafruit")
            .field(feed, float(valor))
            .time(fecha, WritePrecision.S))


def importar_historico(write_api, dias):
    """Descarga el historico de cada feed (paginando de 1000 en 1000) y lo guarda."""
    inicio = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for feed in cfg.FEEDS:
        total, fin = 0, None
        while True:
            params = {"start_time": inicio, "limit": 1000}
            if fin:
                params["end_time"] = fin
            r = requests.get(f"{BASE_URL}/{feed}/data", headers=HEADERS, params=params, timeout=20)
            r.raise_for_status()
            datos = r.json()
            if not datos:
                break
            puntos = []
            for d in datos:
                try:
                    if not es_valido(feed, d["value"]):
                        continue
                    puntos.append(crear_punto(feed, d["value"], a_fecha(d["created_at"])))
                except (ValueError, KeyError):
                    continue  # se ignoran valores no numericos
            write_api.write(bucket=cfg.INFLUX_BUCKET, record=puntos)
            total += len(puntos)
            if len(datos) < 1000:
                break
            fin = datos[-1]["created_at"]   # la siguiente pagina termina donde acabo esta
            time.sleep(2.5)                 # respeta el limite de 30 peticiones/min del plan gratuito
        print(f"[HISTORICO] {feed}: {total} registros importados de los ultimos {dias} dias")


def ultimo_dato(feed):
    r = requests.get(f"{BASE_URL}/{feed}/data/last", headers=HEADERS, timeout=10)
    r.raise_for_status()
    d = r.json()
    return d["value"], d["created_at"]


if __name__ == "__main__":
    print("=== INGESTA: ADAFRUIT IO -> INFLUXDB ===")
    if not AIO_KEY:
        print("[ERROR] No se encontro la clave de Adafruit IO. Escribela en config_iot.py (AIO_KEY).")
        raise SystemExit(1)

    cliente = InfluxDBClient(url=cfg.INFLUX_URL, token=cfg.INFLUX_TOKEN, org=cfg.INFLUX_ORG)
    write_api = cliente.write_api(write_options=SYNCHRONOUS)

    try:
        importar_historico(write_api, cfg.DIAS_HISTORICO)
    except Exception as e:
        print(f"[AVISO] No se pudo importar el historico: {e}")

    vistos = {}   # feed -> ultimo created_at guardado
    try:
        while True:
            for feed in cfg.FEEDS:
                try:
                    valor, creado = ultimo_dato(feed)
                    if vistos.get(feed) == creado:
                        continue   # el ESP aun no ha publicado un dato nuevo
                    if not es_valido(feed, valor):
                        vistos[feed] = creado
                        print(f"[DESCARTADO] {creado} | {feed} = {valor} (fuera de rango, fallo del sensor)")
                        continue
                    write_api.write(bucket=cfg.INFLUX_BUCKET,
                                    record=crear_punto(feed, valor, a_fecha(creado)))
                    vistos[feed] = creado
                    print(f"[GUARDADO] {creado} | {cfg.AULA_REAL} | {feed} = {valor}")
                except Exception as e:
                    print(f"[ERROR] {feed}: {e}")
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n[INFO] Ingesta detenida.")
    finally:
        cliente.close()
