# -*- coding: utf-8 -*-
"""
config_iot.py - Configuracion compartida del proyecto Semana 15.
Todos los scripts (ingesta, simulador, alertas) importan estos valores,
asi cualquier cambio se hace en un solo lugar.
"""
import os
import re

CARPETA = os.path.dirname(os.path.abspath(__file__))

# --- InfluxDB (instalado localmente, puerto por defecto 8086) ---
INFLUX_URL = "http://localhost:8086"
INFLUX_ORG = "uts"
INFLUX_BUCKET = "iot_aulas"
INFLUX_TOKEN = "uts-iot-semana15-token-local"   # token fijo creado en la configuracion inicial
INFLUX_USER = "admin"
INFLUX_PASSWORD = "admin12345"
MEDICION = "ambiente"                            # measurement donde se guardan las lecturas

# --- Grafana (puerto por defecto 3000) ---
GRAFANA_URL = "http://localhost:3000"
GRAFANA_USER = "admin"
GRAFANA_PASSWORD = "admin12345"
DASHBOARD_UID = "iot-uts-s15"

# --- Adafruit IO ---
AIO_USERNAME = "ngqwrld"
AIO_KEY = ""   # NO escribir la clave aqui: va en aio_key.txt (no se sube a GitHub)
FEEDS = ["temperatura", "humedad", "luminosidad"]
FEED_LED = "led-rojo"     # feeds a los que esta suscrito el NodeMCU:
FEED_BUZZER = "buzzer"    # la alerta enciende el LED y hace sonar el buzzer

# --- Aulas ---
AULA_REAL = "Aula_A"        # aula donde esta el NodeMCU (datos reales via Adafruit IO)
AULA_SIMULADA = "Aula_B"    # segunda aula (datos generados por simulador_aula_b.py)

# --- Parametros del umbral dinamico ---
DIAS_HISTORICO = 7          # ventana del historico usada para la media y la desviacion
K_DESVIACIONES = 2          # umbral = media + K * desviacion estandar
MIN_MUESTRAS = 30           # si hay menos datos, se usa el umbral por defecto
UMBRAL_POR_DEFECTO = 30.0   # grados Celsius
INTERVALO_REVISION = 20     # segundos entre cada evaluacion de alertas
ENFRIAMIENTO_ALERTA = 300   # segundos minimos entre dos alertas de la misma aula

# --- Correo (opcional). Con Gmail se necesita una "contrasena de aplicacion". ---
EMAIL_ACTIVO = False
EMAIL_SMTP = "smtp.gmail.com"
EMAIL_PUERTO = 587
EMAIL_REMITENTE = "nygranados@uts.edu.co"
EMAIL_CLAVE_APP = ""
EMAIL_DESTINO = "nygranados@uts.edu.co"


def obtener_aio_key():
    """Devuelve la clave de Adafruit IO buscandola, en orden, en: la variable
    AIO_KEY de arriba, la variable de entorno AIO_KEY, el archivo aio_key.txt
    (excluido de git) y el script ingesta_iot.py de la Semana 14."""
    if AIO_KEY and AIO_KEY != "TU_AIO_KEY":
        return AIO_KEY
    if os.environ.get("AIO_KEY"):
        return os.environ["AIO_KEY"]
    archivo_clave = os.path.join(CARPETA, "aio_key.txt")
    if os.path.exists(archivo_clave):
        with open(archivo_clave, encoding="utf-8") as f:
            clave = f.read().strip()
        if clave:
            return clave
    candidatos = [
        os.path.join(CARPETA, "..", "Semana14_Almacenamiento_IoT", "ingesta_iot.py"),
        os.path.join(CARPETA, "..", "Semana14_Almacenamiento_IoT", "ingesta_iot (1).py"),
    ]
    for ruta in candidatos:
        if os.path.exists(ruta):
            with open(ruta, encoding="utf-8", errors="ignore") as f:
                m = re.search(r'AIO_KEY\s*=\s*["\']([^"\']+)["\']', f.read())
            if m and m.group(1) != "TU_AIO_KEY":
                return m.group(1)
    return ""
