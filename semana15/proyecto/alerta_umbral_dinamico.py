# -*- coding: utf-8 -*-
"""
alerta_umbral_dinamico.py - Sistema de alertas con umbral estadistico.

Cada INTERVALO_REVISION segundos, y para cada aula:
  1. Consulta en InfluxDB el historico de temperatura de los ultimos 7 dias
     (sin incluir los ultimos 10 minutos, para que una anomalia reciente no
     "contamine" el calculo de lo que es normal).
  2. Calcula la media (mu) y la desviacion estandar (sigma).
  3. Define el umbral dinamico:  umbral = mu + 2 * sigma
     (si hay menos de MIN_MUESTRAS datos usa el umbral por defecto de 30 C).
  4. Compara la temperatura actual (promedio del ultimo minuto) con el umbral.
  5. Si lo supera: registra la alerta en alertas.log, la guarda en InfluxDB
     (measurement "alertas"), genera una grafica de evidencia y, si esta
     configurado, envia un correo y enciende el LED y el buzzer del NodeMCU
     (feeds "led-rojo" y "buzzer" de Adafruit IO).
Ademas guarda el umbral calculado (measurement "umbral") para que Grafana
pueda dibujarlo como una linea sobre la tendencia de temperatura.
"""
import logging
import os
import smtplib
import time
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

import requests
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

import config_iot as cfg

HORA_COLOMBIA = timezone(timedelta(hours=-5))
CARPETA_EVID = os.path.join(cfg.CARPETA, "evidencias")
os.makedirs(CARPETA_EVID, exist_ok=True)

# --- Registro (log) en consola y en archivo ---
log = logging.getLogger("alertas")
log.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", "%Y-%m-%d %H:%M:%S")
for manejador in (logging.FileHandler(os.path.join(CARPETA_EVID, "alertas.log"), encoding="utf-8"),
                  logging.StreamHandler()):
    manejador.setFormatter(formato)
    log.addHandler(manejador)


def valor_flux(query_api, flux):
    """Ejecuta una consulta Flux que devuelve un solo valor (o None si no hay datos)."""
    for tabla in query_api.query(flux):
        for registro in tabla.records:
            return registro.get_value()
    return None


def filtro(aula):
    return (f'filter(fn:(r)=> r._measurement=="{cfg.MEDICION}" and r._field=="temperatura" '
            f'and r.aula=="{aula}" and r._value > 0.5 and r._value < 80.0)')   # ignora fallos del sensor


def calcular_umbral(query_api, aula):
    """Devuelve (umbral, media, desviacion, n_muestras) a partir del historico."""
    base = (f'from(bucket:"{cfg.INFLUX_BUCKET}") |> range(start:-{cfg.DIAS_HISTORICO}d, stop:-10m) '
            f'|> {filtro(aula)} |> group()')   # group() une las series de distintas etiquetas
    n = valor_flux(query_api, base + ' |> count()') or 0
    if n < 2:
        return cfg.UMBRAL_POR_DEFECTO, None, None, n
    media = valor_flux(query_api, base + ' |> mean()')
    desv = valor_flux(query_api, base + ' |> stddev()') or 0.0
    desv = max(desv, 0.2)   # evita un umbral pegado a la media si el aula estuvo muy estable
    if n < cfg.MIN_MUESTRAS:
        # Historico insuficiente: se informa la media, pero se usa el umbral por defecto
        return cfg.UMBRAL_POR_DEFECTO, media, desv, n
    return media + cfg.K_DESVIACIONES * desv, media, desv, n


def temperatura_actual(query_api, aula):
    flux = (f'from(bucket:"{cfg.INFLUX_BUCKET}") |> range(start:-2m) |> {filtro(aula)} '
            f'|> group() |> mean()')
    return valor_flux(query_api, flux)


def grafica_evidencia(query_api, aula, umbral, media, temp):
    """Guarda un PNG con la temperatura de las ultimas 2 horas, la media y el umbral."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError:
        return None
    flux = (f'from(bucket:"{cfg.INFLUX_BUCKET}") |> range(start:-2h) |> {filtro(aula)} '
            f'|> group() |> sort(columns:["_time"])')
    xs, ys = [], []
    for tabla in query_api.query(flux):
        for r in tabla.records:
            xs.append(r.get_time().astimezone(HORA_COLOMBIA))
            ys.append(r.get_value())
    if not xs:
        return None
    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=130)
    ax.plot(xs, ys, color="#2f6db5", linewidth=1.6, label="Temperatura (°C)")
    ax.axhline(umbral, color="#c62828", linestyle="--", linewidth=1.6,
               label=f"Umbral dinámico = {umbral:.2f} °C")
    if media is not None:
        ax.axhline(media, color="#7a7a7a", linestyle=":", linewidth=1.2, label=f"Media = {media:.2f} °C")
    altos = [(x, y) for x, y in zip(xs, ys) if y > umbral]
    if altos:
        ax.scatter(*zip(*altos), color="#c62828", s=28, zorder=5, label="Lecturas sobre el umbral")
    ax.set_title(f"Alerta de temperatura – {aula.replace('_', ' ')} (actual {temp:.2f} °C)", fontsize=12)
    ax.set_ylabel("°C")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=HORA_COLOMBIA))
    ax.grid(alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    fig.tight_layout()
    ruta = os.path.join(CARPETA_EVID, f"alerta_{aula}_{datetime.now():%Y%m%d_%H%M%S}.png")
    fig.savefig(ruta)
    plt.close(fig)
    return ruta


def enviar_correo(asunto, cuerpo):
    if not (cfg.EMAIL_ACTIVO and cfg.EMAIL_CLAVE_APP):
        return False
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = asunto, cfg.EMAIL_REMITENTE, cfg.EMAIL_DESTINO
    msg.set_content(cuerpo)
    with smtplib.SMTP(cfg.EMAIL_SMTP, cfg.EMAIL_PUERTO, timeout=15) as s:
        s.starttls()
        s.login(cfg.EMAIL_REMITENTE, cfg.EMAIL_CLAVE_APP)
        s.send_message(msg)
    return True


def publicar_feed(feed, valor, key):
    url = f"https://io.adafruit.com/api/v2/{cfg.AIO_USERNAME}/feeds/{feed}/data"
    try:
        requests.post(url, headers={"X-AIO-Key": key}, json={"value": str(valor)}, timeout=10)
    except Exception:
        pass


def activar_actuadores(valor):
    """Avisa en el NodeMCU a traves de Adafruit IO: el ESP8266 esta suscrito a los
    feeds 'led-rojo' y 'buzzer'. Con alerta enciende el LED y hace sonar el buzzer
    3 segundos; al normalizarse apaga el LED."""
    key = cfg.obtener_aio_key()
    if not key:
        return
    feed_led = getattr(cfg, "FEED_LED", "led-rojo")
    feed_buzzer = getattr(cfg, "FEED_BUZZER", "buzzer")
    publicar_feed(feed_led, valor, key)
    if valor == 1:
        publicar_feed(feed_buzzer, 1, key)
        time.sleep(3)
        publicar_feed(feed_buzzer, 0, key)


if __name__ == "__main__":
    log.info("=== SISTEMA DE ALERTAS DINAMICAS INICIADO (umbral = media + %d*sigma) ===", cfg.K_DESVIACIONES)
    cliente = InfluxDBClient(url=cfg.INFLUX_URL, token=cfg.INFLUX_TOKEN, org=cfg.INFLUX_ORG)
    query_api = cliente.query_api()
    write_api = cliente.write_api(write_options=SYNCHRONOUS)
    ultima_alerta = {}            # aula -> momento de la ultima alerta
    en_alerta = {}                # aula -> True/False (para avisar cuando vuelve a la normalidad)

    try:
        while True:
            for aula in (cfg.AULA_REAL, cfg.AULA_SIMULADA):
                try:
                    umbral, media, desv, n = calcular_umbral(query_api, aula)
                    temp = temperatura_actual(query_api, aula)

                    # Se guarda el umbral para graficarlo en Grafana
                    p = Point("umbral").tag("aula", aula).field("umbral_alto", float(umbral)).field("muestras", int(n))
                    if media is not None:
                        p = p.field("media", float(media)).field("desviacion", float(desv))
                    write_api.write(bucket=cfg.INFLUX_BUCKET, record=p)

                    if temp is None:
                        log.info("%s | sin lecturas en los ultimos 2 min | umbral %.2f C", aula, umbral)
                        continue
                    if n < cfg.MIN_MUESTRAS:
                        detalle = f"historico insuficiente (n={n}), umbral por defecto"
                    else:
                        detalle = f"media {media:.2f} C, sigma {desv:.2f} C, n={n}"
                    if temp <= umbral:
                        if en_alerta.get(aula):
                            log.info("%s | NORMALIZADO | %.2f C <= umbral %.2f C", aula, temp, umbral)
                            activar_actuadores(0)
                        en_alerta[aula] = False
                        log.info("%s | normal | actual %.2f C | umbral %.2f C (%s)", aula, temp, umbral, detalle)
                        continue

                    # --- Temperatura por encima del umbral dinamico ---
                    en_alerta[aula] = True
                    ahora = time.time()
                    if ahora - ultima_alerta.get(aula, 0) < cfg.ENFRIAMIENTO_ALERTA:
                        log.warning("%s | sigue sobre el umbral: %.2f C > %.2f C", aula, temp, umbral)
                        continue
                    ultima_alerta[aula] = ahora
                    log.warning("ALERTA %s | temperatura %.2f C supera el umbral dinamico %.2f C (%s)",
                                aula, temp, umbral, detalle)
                    write_api.write(bucket=cfg.INFLUX_BUCKET, record=Point("alertas").tag("aula", aula)
                                    .field("temperatura", float(temp)).field("umbral", float(umbral)))
                    ruta = grafica_evidencia(query_api, aula, umbral, media, temp)
                    if ruta:
                        log.info("Evidencia grafica guardada en %s", ruta)
                    activar_actuadores(1)
                    try:
                        if enviar_correo(f"[ALERTA IoT] {aula}: {temp:.1f} C",
                                         f"La temperatura del {aula} es {temp:.2f} C y supera el umbral "
                                         f"dinamico de {umbral:.2f} C ({detalle}).\n"
                                         f"Hora: {datetime.now():%Y-%m-%d %H:%M:%S}"):
                            log.info("Correo de alerta enviado a %s", cfg.EMAIL_DESTINO)
                    except Exception as e:
                        log.error("No se pudo enviar el correo: %s", e)
                except Exception as e:
                    log.error("%s | error al evaluar: %s", aula, e)
            time.sleep(cfg.INTERVALO_REVISION)
    except KeyboardInterrupt:
        log.info("Sistema de alertas detenido por el usuario.")
    finally:
        cliente.close()
