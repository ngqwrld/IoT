# -*- coding: utf-8 -*-
"""
limpiar_lecturas_invalidas.py - Borra de InfluxDB las lecturas imposibles del
sensor (por ejemplo 0 C mientras se conectaba el DHT11). El DHT11 mide entre
0 y 50 C, asi que una temperatura <= 0.5 C o >= 80 C es un fallo de lectura.
Para cada lectura invalida se borra ese segundo exacto del Aula_A.
"""
from datetime import timedelta

from influxdb_client import InfluxDBClient

import config_iot as cfg

with InfluxDBClient(url=cfg.INFLUX_URL, token=cfg.INFLUX_TOKEN, org=cfg.INFLUX_ORG) as cliente:
    flux = f'''from(bucket:"{cfg.INFLUX_BUCKET}") |> range(start:-30d)
      |> filter(fn:(r)=> r._measurement=="{cfg.MEDICION}" and r.fuente=="adafruit" and r._field=="temperatura")
      |> filter(fn:(r)=> r._value <= 0.5 or r._value >= 80.0)'''
    tiempos = [r.get_time() for t in cliente.query_api().query(flux) for r in t.records]
    borrar = cliente.delete_api()
    for t in tiempos:
        borrar.delete(t, t + timedelta(seconds=1),
                      f'_measurement="{cfg.MEDICION}" AND aula="{cfg.AULA_REAL}" AND fuente="adafruit"',
                      bucket=cfg.INFLUX_BUCKET, org=cfg.INFLUX_ORG)
    print(f"[LIMPIEZA] {len(tiempos)} lecturas invalidas del sensor eliminadas de InfluxDB.")
