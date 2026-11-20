# Semana 15 – Visualización Histórica y Alertas Dinámicas

**Integrantes:** Neiver Granados y Kevin González  
**Actividad ABPr:** Consolidación del Dashboard y Alertas (Corte III)  
**Plataforma:** NodeMCU V3 (ESP8266) + DHT11 + fotorresistencia + LED + buzzer

## Flujo de datos

```
NodeMCU (ESP8266) ──MQTT──▶ Adafruit IO ──▶ ingesta_influx.py ──▶ InfluxDB (bucket iot_aulas)
                                                                    │
                                     Grafana (dashboard) ◀──────────┤
                                                                    │
            LED + buzzer ◀──MQTT── Adafruit IO ◀── alerta_umbral_dinamico.py (μ + 2σ)
```

## Contenido

| Carpeta / archivo | Qué es |
|---|---|
| `informe/Semana15_Visualizacion_Alertas_IoT.docx` | Documento técnico de la entrega |
| `proyecto/` | Código listo para ejecutar en Windows |
| `proyecto/proyecto_iot_esp8266.ino` | Código del NodeMCU (publica sensores y escucha `led-rojo` y `buzzer`) |
| `proyecto/dashboard_iot_uts.json` | Dashboard de Grafana (importable) |
| `proyecto/docker-compose.yml` | Alternativa para levantar InfluxDB y Grafana con Docker |
| `proyecto/evidencias/` | Capturas, gráfica de la alerta, `alertas.log` y dashboard exportado |

### Scripts de Python

| Script | Función |
|---|---|
| `config_iot.py` | Configuración compartida (InfluxDB, Grafana, Adafruit, parámetros del umbral) |
| `configurar_influxdb.py` | Configuración inicial de InfluxDB: usuario, organización, bucket y token |
| `ingesta_influx.py` | Adafruit IO → InfluxDB, con histórico, sin duplicados y validando lecturas |
| `simulador_aula_b.py` | Genera los datos de la segunda aula (etiqueta `fuente=simulado`) |
| `alerta_umbral_dinamico.py` | Calcula μ + 2σ y dispara la alerta (log, InfluxDB, gráfica, LED y buzzer) |
| `simular_anomalia.py` | Inyecta lecturas altas para probar la alerta |
| `limpiar_lecturas_invalidas.py` | Borra lecturas imposibles del sensor |
| `exportar_dashboard.py` | Exporta el dashboard a JSON por la API de Grafana |
| `generar_informe.py` | Genera el Word con las evidencias de la carpeta `evidencias/` |

## Cómo ejecutarlo

1. Copia tu clave de Adafruit IO en un archivo `proyecto/aio_key.txt` (está en `.gitignore`, nunca se sube).
2. En `proyecto_iot_esp8266.ino` reemplaza `TU_RED_WIFI`, `TU_PASSWORD` y `TU_AIO_KEY`, y cárgalo al NodeMCU.
3. Doble clic en `EJECUTAR_TODO.bat`: descarga InfluxDB 2.10.1 y Grafana 13.3.1, los configura y abre el dashboard.
4. Grafana: http://localhost:3000 · InfluxDB: http://localhost:8086 (usuario `admin`).
5. Para probar la alerta: `SIMULAR_ANOMALIA.bat`.
6. Para volver a generar el informe: `GENERAR_INFORME.bat`.

Los días siguientes basta con `iniciar_servicios.bat` y luego `iniciar_scripts.bat`.

## Umbral dinámico

```
umbral = media + 2 · desviación estándar   (últimos 7 días, sin los últimos 10 minutos)
```

- Con menos de 30 muestras se usa un umbral por defecto de 30 °C.
- La desviación se toma como mínimo 0,2 °C para que un aula muy estable no genere falsas alarmas.
- Una misma aula no vuelve a alertar antes de 5 minutos.

## Resultado de la prueba

El 20 de noviembre de 2026, a las 11:39:06, se inyectaron manualmente en InfluxDB lecturas de 42,6 a 44,0 °C en el Aula A. El sistema detectó un promedio de **36,16 °C**, por encima del umbral dinámico de **29,57 °C** (media 28,59 °C, σ 0,49 °C, n = 40). La alerta quedó en `alertas.log`, en el panel de alertas de Grafana y en la gráfica de evidencia, y en la placa se encendió el LED y sonó el buzzer.

> El Aula B es simulada porque el grupo cuenta con un solo NodeMCU; todos sus datos llevan la etiqueta `fuente=simulado`.
