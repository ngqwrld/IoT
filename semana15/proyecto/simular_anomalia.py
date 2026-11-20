# -*- coding: utf-8 -*-
"""
simular_anomalia.py - Inyecta manualmente lecturas de temperatura altas en
InfluxDB para comprobar que el sistema de alertas reacciona.

Escribe 8 lecturas (una cada 5 s) entre 41 y 44 C en el Aula_A, con la
etiqueta fuente="anomalia_manual" para identificarlas despues.
Equivale a cargar en la interfaz de InfluxDB (Data -> Buckets -> iot_aulas
-> Add Data -> Line Protocol) una linea como:
    ambiente,aula=Aula_A,fuente=anomalia_manual temperatura=43.5
"""
import random
import sys
import time
from datetime import datetime

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

import config_iot as cfg

aula = sys.argv[1] if len(sys.argv) > 1 else cfg.AULA_REAL

with InfluxDBClient(url=cfg.INFLUX_URL, token=cfg.INFLUX_TOKEN, org=cfg.INFLUX_ORG) as cliente:
    write_api = cliente.write_api(write_options=SYNCHRONOUS)
    print(f"=== INYECTANDO ANOMALIA EN {aula} ===")
    for i in range(8):
        valor = round(random.uniform(41.0, 44.0), 2)
        write_api.write(bucket=cfg.INFLUX_BUCKET, record=Point(cfg.MEDICION)
                        .tag("aula", aula).tag("dispositivo", "inyeccion_manual")
                        .tag("fuente", "anomalia_manual").field("temperatura", valor))
        print(f"[{datetime.now():%H:%M:%S}] Escrito temperatura = {valor} C  ({i + 1}/8)")
        time.sleep(5)
print("Listo. Revisa la ventana de alertas, la carpeta 'evidencias' y el dashboard.")
