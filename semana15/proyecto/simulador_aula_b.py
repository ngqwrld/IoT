# -*- coding: utf-8 -*-
"""
simulador_aula_b.py - Genera los datos de una segunda aula (Aula_B).

El grupo cuenta con un solo NodeMCU, ubicado en el Aula_A. Para el panel de
comparacion entre dos aulas se simula una segunda aula con un ciclo diario
realista (mas calor al mediodia, luz solo de dia). Todos sus puntos llevan la
etiqueta fuente="simulado" para distinguirlos de los datos reales.
"""
import math
import random
import time
from datetime import datetime, timedelta, timezone

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

import config_iot as cfg

HORA_COLOMBIA = timezone(timedelta(hours=-5))


def lectura(fecha_utc):
    """Calcula temperatura, humedad y luminosidad segun la hora del dia."""
    h = fecha_utc.astimezone(HORA_COLOMBIA)
    hora = h.hour + h.minute / 60
    ciclo = math.sin((hora - 8) / 24 * 2 * math.pi)          # maximo cerca de las 2 p. m.
    temp = 24.5 + 2.8 * ciclo + random.gauss(0, 0.35)
    hum = 60 - 9 * ciclo + random.gauss(0, 1.2)
    luz = max(0.0, 70 * math.sin((hora - 6) / 12 * math.pi)) if 6 <= hora <= 18 else 0.0
    luz = max(0.0, luz + random.gauss(0, 2))
    return round(temp, 2), round(hum, 1), round(luz, 0)


def punto(fecha):
    t, hm, lz = lectura(fecha)
    return (Point(cfg.MEDICION)
            .tag("aula", cfg.AULA_SIMULADA)
            .tag("dispositivo", "simulador")
            .tag("fuente", "simulado")
            .field("temperatura", t).field("humedad", hm).field("luminosidad", lz)
            .time(fecha, WritePrecision.S))


def ya_tiene_historico(cliente):
    q = f'''from(bucket:"{cfg.INFLUX_BUCKET}") |> range(start:-{cfg.DIAS_HISTORICO}d)
      |> filter(fn:(r)=> r._measurement=="{cfg.MEDICION}" and r.aula=="{cfg.AULA_SIMULADA}" and r._field=="temperatura")
      |> count()'''
    tablas = cliente.query_api().query(q)
    return any(rec.get_value() > 100 for t in tablas for rec in t.records)


if __name__ == "__main__":
    print(f"=== SIMULADOR {cfg.AULA_SIMULADA} -> INFLUXDB ===")
    cliente = InfluxDBClient(url=cfg.INFLUX_URL, token=cfg.INFLUX_TOKEN, org=cfg.INFLUX_ORG)
    write_api = cliente.write_api(write_options=SYNCHRONOUS)

    if not ya_tiene_historico(cliente):
        ahora = datetime.now(timezone.utc)
        inicio = ahora - timedelta(days=cfg.DIAS_HISTORICO)
        puntos, f = [], inicio
        while f < ahora:
            puntos.append(punto(f))
            f += timedelta(minutes=5)
        write_api.write(bucket=cfg.INFLUX_BUCKET, record=puntos)
        print(f"[HISTORICO] {len(puntos)} lecturas simuladas de {cfg.DIAS_HISTORICO} dias (cada 5 min)")

    try:
        while True:
            ahora = datetime.now(timezone.utc)
            write_api.write(bucket=cfg.INFLUX_BUCKET, record=punto(ahora))
            t, hm, lz = lectura(ahora)
            print(f"[SIMULADO] {ahora.astimezone(HORA_COLOMBIA):%H:%M:%S} | {cfg.AULA_SIMULADA} | {t} C | {hm} % | luz {lz}")
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n[INFO] Simulador detenido.")
    finally:
        cliente.close()
