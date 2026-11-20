# -*- coding: utf-8 -*-
"""
generar_informe.py - Genera el documento Word de la Semana 15.

Usa como plantilla el informe de la Semana 14 (mismo formato de portada,
titulos, pie de pagina y bloques de codigo) y arma el informe nuevo.
Inserta automaticamente las evidencias que encuentre en la carpeta
'evidencias':
  - dashboard*.png / dashboard*.jpg   -> captura del dashboard de Grafana (la tomas tu)
  - consola*.png / consola*.jpg       -> captura de la ventana de alertas (opcional)
  - influx*.png / influx*.jpg         -> captura de InfluxDB Data Explorer (opcional)
  - alerta_*.png                      -> grafica generada por el sistema de alertas
  - alertas.log                       -> registro de alertas (se copia un extracto)
Si alguna captura no existe, deja un recuadro indicando donde pegarla.
"""
import copy
import glob
import os
import re
from datetime import datetime

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm
from docx.text.paragraph import Paragraph

AQUI = os.path.dirname(os.path.abspath(__file__))
EVID = os.path.join(AQUI, "evidencias")
SALIDA = os.path.join(AQUI, "Semana15_Visualizacion_Alertas_IoT.docx")
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]

doc = Document(os.path.join(AQUI, "plantilla_informe.docx"))
cuerpo = doc.element.body
P = doc.paragraphs

# ---------- Parrafos modelo tomados de la plantilla (formato identico) ----------
MODELOS = {"institucion": 1, "programa": 2, "semana": 3, "titulo": 4, "subtitulo": 5,
           "dato_portada": 6, "salto": 9, "h1": 10, "texto": 11, "vineta": 17,
           "flujo": 23, "imagen": 35, "pie_figura": 36, "h2": 38, "codigo": 40, "referencia": 165}
T = {k: copy.deepcopy(P[i]._p) for k, i in MODELOS.items()}

# Foto del circuito que ya estaba en el informe anterior
blip = P[35]._p.find(".//" + qn("a:blip"))
FOTO_CIRCUITO = os.path.join(AQUI, "circuito.jpg")
if blip is not None and not os.path.exists(FOTO_CIRCUITO):
    with open(FOTO_CIRCUITO, "wb") as f:
        f.write(doc.part.related_parts[blip.get(qn("r:embed"))].blob)

# Se vacia el cuerpo conservando la configuracion de pagina (sectPr)
sect = cuerpo.find(qn("w:sectPr"))
for el in list(cuerpo):
    if el is not sect:
        cuerpo.remove(el)


def rpr_modelo(p, idx=0):
    runs = p.findall(qn("w:r"))
    if runs and idx < len(runs) and runs[idx].find(qn("w:rPr")) is not None:
        return copy.deepcopy(runs[idx].find(qn("w:rPr")))
    return OxmlElement("w:rPr")


def parrafo(modelo, partes, rpr_idx=None):
    """Clona un parrafo modelo y le pone el texto indicado.
    partes: lista de (texto, estilo) con estilo en {"", "b", "i", "bi", "rojo"}."""
    base = T[modelo]
    nuevo = copy.deepcopy(base)
    for hijo in list(nuevo):
        if hijo.tag != qn("w:pPr"):
            nuevo.remove(hijo)
    for n, (texto, estilo) in enumerate(partes):
        r = OxmlElement("w:r")
        idx = rpr_idx[n] if rpr_idx else 0
        rpr = rpr_modelo(base, idx)
        for etiqueta in (["w:b"] if "b" in estilo else []) + (["w:i"] if "i" in estilo else []):
            if rpr.find(qn(etiqueta)) is None:
                rpr.append(OxmlElement(etiqueta))
        if "rojo" in estilo:
            c = OxmlElement("w:color"); c.set(qn("w:val"), "C00000"); rpr.append(c)
        if len(rpr):
            r.append(rpr)
        t = OxmlElement("w:t")
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        t.text = texto
        r.append(t)
        nuevo.append(r)
    sect.addprevious(nuevo)
    return Paragraph(nuevo, doc._body)


def texto(*partes):
    """texto("normal", ("negrita", "b"), ...)"""
    return parrafo("texto", [(p, "") if isinstance(p, str) else p for p in partes])


def vineta(*partes):
    return parrafo("vineta", [(p, "") if isinstance(p, str) else p for p in partes])


def h1(t): parrafo("h1", [(t, "")])
def h2(t): parrafo("h2", [(t, "")])
def salto(): parrafo("salto", []).add_run().add_break(__import__("docx").enum.text.WD_BREAK.PAGE)


def codigo(lineas):
    for linea in lineas:
        parrafo("codigo", [(linea.replace("\t", "    ") or " ", "")])


N_FIG = [0]


def figura(ruta, pie, ancho_cm=15.5, aviso=None):
    N_FIG[0] += 1
    p = parrafo("imagen", [])
    if ruta and os.path.exists(ruta):
        p.add_run().add_picture(ruta, width=Cm(ancho_cm))
    else:
        p = parrafo("texto", [(aviso or "[Pegar aquí la captura]", "bi rojo")])
        p.alignment = 1
    parrafo("pie_figura", [(f"Figura {N_FIG[0]}. {pie}", "")])


def buscar(patron):
    rutas = sorted(glob.glob(os.path.join(EVID, patron)), key=os.path.getmtime)
    return rutas[-1] if rutas else None


# ---------- Datos reales de la ultima alerta (desde alertas.log) ----------
LOG = os.path.join(EVID, "alertas.log")
lineas_log, alerta = [], None
if os.path.exists(LOG):
    with open(LOG, encoding="utf-8", errors="ignore") as f:
        lineas_log = [l.rstrip("\n") for l in f]
    patron = re.compile(r"ALERTA (\S+) \| temperatura ([\d.]+) C supera el umbral dinamico ([\d.]+) C \((.*)\)")
    for i, l in enumerate(lineas_log):
        m = patron.search(l)
        if m:
            alerta = {"i": i, "hora": l[:19], "aula": m.group(1), "temp": m.group(2),
                      "umbral": m.group(3), "detalle": m.group(4)}

hoy = datetime.now()
FECHA = f"{hoy.day} de {MESES[hoy.month - 1]} de {hoy.year}"

# =====================================================================
# PORTADA
# =====================================================================
parrafo("institucion", [("UNIVERSITARIA TECNOLÓGICA DE SANTANDER", "")])
parrafo("programa", [("Proyecto Integrador en IoT", "")])
parrafo("semana", [("Semana 15", "")])
parrafo("titulo", [("Visualización Histórica y Alertas Dinámicas", "")])
parrafo("subtitulo", [("Actividad ABPr: Consolidación del Dashboard y Alertas", "")])
for etiqueta, valor in (("Estudiantes: ", "Neiver Granados y Kevin González"),
                        ("Docente: ", "E. Montero Ojeda"), ("Fecha: ", FECHA)):
    parrafo("dato_portada", [(etiqueta, ""), (valor, "")], rpr_idx=[0, 1])
salto()

# =====================================================================
# 1. INTRODUCCIÓN
# =====================================================================
h1("1. Introducción")
texto("En la Semana 14 resolvimos el problema de la persistencia: los datos que el NodeMCU publica en "
      "Adafruit IO dejaron de depender de los 30 días de histórico de la nube gratuita y pasaron a guardarse "
      "en una base local. Sin embargo, tener los datos guardados no basta si nadie los mira. Para que la "
      "coordinación académica pueda tomar decisiones sobre las aulas, la información tiene que verse de forma "
      "clara y el sistema debe avisar por sí solo cuando algo se sale de lo normal.")
texto("Esta semana se cerró ese ciclo. Los datos ahora se almacenan en InfluxDB, una base de datos pensada "
      "para series de tiempo; se construyó en Grafana un dashboard con la tendencia de las variables, la "
      "comparación entre dos aulas, una tabla de resúmenes diarios y un indicador de estado; y se programó en "
      "Python un sistema de alertas que no usa un valor fijo, sino un umbral que se calcula a partir del "
      "propio histórico de cada aula (media más dos desviaciones estándar).")

# =====================================================================
# 2. OBJETIVOS
# =====================================================================
h1("2. Objetivos")
texto(("Objetivo general: ", "b"), "integrar el flujo de datos del NodeMCU con InfluxDB y Grafana para "
      "visualizar el histórico ambiental de las aulas y detectar anomalías mediante un umbral estadístico.")
texto(("Objetivos específicos:", "b"))
for o in ("Levantar InfluxDB y Grafana en el equipo local y documentar el procedimiento para repetirlo.",
          "Llevar las lecturas de Adafruit IO a InfluxDB sin duplicados y conservando la hora original de cada dato.",
          "Construir un dashboard con al menos cuatro paneles, variables interactivas y exportarlo en formato JSON.",
          "Implementar en Python el cálculo del umbral dinámico (μ + 2σ) y el disparo de alertas.",
          "Simular una anomalía y registrar la evidencia de la alerta."):
    vineta(o)

# =====================================================================
# 3. ARQUITECTURA
# =====================================================================
h1("3. Arquitectura del Sistema")
texto("El recorrido de los datos es el siguiente:")
parrafo("flujo", [("NodeMCU (ESP8266) + sensores → Adafruit IO (MQTT/REST) → ingesta_influx.py → "
                   "InfluxDB (bucket iot_aulas) → Grafana (dashboard) y alerta_umbral_dinamico.py", "b")])
texto(("Hardware: ", "b"), "placa NodeMCU V3 (ESP8266), sensor DHT11 de temperatura y humedad, "
      "fotorresistencia para la luminosidad, LED indicador y buzzer como actuadores, protoboard, "
      "resistencias y cables.")
texto(("Software: ", "b"), "Adafruit IO, InfluxDB OSS 2.10, Grafana 13, Python 3.12 con las librerías "
      "influxdb-client, requests y matplotlib.")
if buscar("montaje*.jpg"):
    figura(buscar("montaje*.jpg"), "Montaje actual del circuito: NodeMCU V3 (ESP8266), sensor DHT11, "
           "fotorresistencia, LED y buzzer sobre la protoboard.", 12.5)
else:
    figura(FOTO_CIRCUITO, "Montaje del circuito: NodeMCU (ESP8266), DHT11, fotorresistencia, LED y buzzer.", 6.8)

h2("3.1 Modelo de datos en InfluxDB")
texto("InfluxDB organiza la información en measurements (equivalentes a tablas), etiquetas o tags "
      "(texto indexado para filtrar) y campos o fields (los valores numéricos). Se definieron tres measurements:")
vineta(("ambiente: ", "b"), "lecturas de los sensores. Tags: aula, dispositivo y fuente. Fields: temperatura, "
       "humedad y luminosidad.")
vineta(("umbral: ", "b"), "valor del umbral dinámico calculado en cada revisión (media, desviación, número de "
       "muestras y umbral_alto), para poder dibujarlo en Grafana.")
vineta(("alertas: ", "b"), "cada alerta disparada, con la temperatura que la causó y el umbral vigente.")
texto("El tag fuente permite distinguir siempre el origen de cada dato: adafruit para las lecturas reales, "
      "simulado para el Aula B y anomalia_manual para los valores inyectados en la prueba.")

# =====================================================================
# 4. INSTRUCCIONES
# =====================================================================
h1("4. Instrucciones para Levantar InfluxDB y Grafana")
h2("4.1 Opción A: instalación manual en Windows (la utilizada)")
texto("Se eligió la instalación manual porque no requiere Docker, WSL2 ni reiniciar el equipo. Todo el "
      "proceso quedó automatizado en el archivo EJECUTAR_TODO.bat, que hace lo siguiente:")
for paso in ("Descarga los binarios oficiales de InfluxDB 2.10.1 (zip) y Grafana 13.3.1 (tar.gz) y los "
             "descomprime en %USERPROFILE%\\IoT_S15, fuera de OneDrive para que la base de datos no se sincronice.",
             "Crea el archivo conf\\custom.ini de Grafana con el usuario admin y deja aprovisionados (provisioning) "
             "la fuente de datos InfluxDB y el dashboard, de modo que aparecen sin configurarlos a mano.",
             "Inicia influxd.exe (puerto 8086) y grafana.exe server (puerto 3000), cada uno en su ventana.",
             "Ejecuta configurar_influxdb.py, que hace la configuración inicial por la API: usuario, organización "
             "uts, bucket iot_aulas con retención infinita y un token de acceso.",
             "Instala las librerías de Python y abre la ingesta, el simulador del Aula B y el sistema de alertas."):
    vineta(paso)
texto("Los comandos esenciales, por si se quiere hacer a mano desde una terminal, son:")
codigo([r'curl.exe -L -o influxdb.zip https://download.influxdata.com/influxdb/releases/influxdb2-2.10.1-windows_amd64.zip',
        r'tar -xf influxdb.zip -C %USERPROFILE%\IoT_S15\influxdb',
        r'influxd.exe --bolt-path %USERPROFILE%\IoT_S15\influx_datos\influxd.bolt --engine-path %USERPROFILE%\IoT_S15\influx_datos\engine',
        r'tar -xzf grafana_13.3.1_windows_amd64.tar.gz -C %USERPROFILE%\IoT_S15',
        r'grafana\bin\grafana.exe server --homepath %USERPROFILE%\IoT_S15\grafana',
        r'py -3.12 -m pip install influxdb-client requests matplotlib python-docx'])
texto("Después de encender el equipo basta con ejecutar iniciar_servicios.bat (InfluxDB y Grafana) e "
      "iniciar_scripts.bat (ingesta, simulador y alertas). Los accesos son http://localhost:8086 para InfluxDB y "
      "http://localhost:3000 para Grafana, ambos con usuario admin.")

h2("4.2 Opción B: docker-compose")
texto("Para un equipo con Docker Desktop se dejó el archivo docker-compose.yml, que levanta los mismos dos "
      "servicios con la misma organización, bucket y token. Se inicia con docker compose up -d:")
with open(os.path.join(AQUI, "docker-compose.yml"), encoding="utf-8") as f:
    codigo([l.rstrip("\n") for l in f if not l.startswith("#")])

h2("4.3 Conexión de Grafana con InfluxDB")
texto("La fuente de datos se crea sola mediante el archivo de aprovisionamiento influxdb_iot.yaml. Si se "
      "quisiera hacer a mano, en Grafana se entra a Connections → Data sources → Add data source → InfluxDB y se "
      "llenan estos datos: lenguaje de consulta Flux, URL http://localhost:8086, organización uts, bucket por "
      "defecto iot_aulas y el token definido en config_iot.py.")

# =====================================================================
# 5. INTEGRACIÓN DE DATOS
# =====================================================================
h1("5. Integración de Datos")
h2("5.1 Ingesta de Adafruit IO a InfluxDB (ingesta_influx.py)")
texto("El script trabaja en dos momentos. Al arrancar descarga el histórico real que Adafruit IO guarda de los "
      "últimos siete días, paginando de mil en mil registros y conservando la fecha original de cada lectura "
      "(campo created_at), de forma que InfluxDB queda con la misma línea de tiempo que vivió el sensor. Después "
      "entra en un ciclo que cada 10 segundos consulta el último valor de cada feed.")
texto("En la Semana 14 notamos que se guardaban lecturas repetidas porque el script consultaba más rápido de lo "
      "que el NodeMCU publicaba. Esta vez cada dato solo se escribe si su created_at es distinto del último "
      "guardado, lo que elimina los duplicados. También se descartan lecturas imposibles para el DHT11 "
      "(por ejemplo 0 °C, que apareció mientras se conectaba el sensor), y las que ya habían entrado se "
      "borraron con limpiar_lecturas_invalidas.py. Las fallas de red se capturan con try/except para que una "
      "caída momentánea no detenga la ingesta, y la clave de Adafruit se toma del script de la semana anterior "
      "para no repetirla en el código.")
h2("5.2 Segunda aula (simulador_aula_b.py)")
texto("El grupo cuenta con un solo NodeMCU, instalado en el Aula A. Para el panel comparativo se generó una "
      "segunda aula con un simulador que sigue un ciclo diario creíble: la temperatura sube hacia las dos de la "
      "tarde, la humedad se comporta al revés y la luminosidad solo aparece de día. Cada punto lleva el tag "
      "fuente=simulado, de modo que nunca se mezcla con los datos reales y se puede filtrar en cualquier consulta.")

# =====================================================================
# 6. DASHBOARD
# =====================================================================
h1("6. Dashboard en Grafana")
texto("El dashboard Monitoreo Ambiental de Aulas – IoT UTS se actualiza cada 10 segundos y tiene seis paneles, "
      "todos con consultas en Flux:")
for nombre, desc in (("Estado actual (gauge): ", "indica qué tan cerca está la temperatura actual del umbral "
                      "dinámico, en una escala donde 0 % es la temperatura media del aula y 100 % es el umbral "
                      "μ + 2σ. Es verde por debajo de μ + 1σ (50 %), amarillo entre μ + 1σ y μ + 2σ, y rojo cuando "
                      "se supera el umbral. Como la escala sale del umbral que calcula el script, el color cambia "
                      "solo cuando cambia el comportamiento histórico del aula."),
                     ("Temperatura actual vs. umbral (stat): ", "pone lado a lado la lectura más reciente y el "
                      "umbral calculado por el script de alertas, en grados Celsius."),
                     ("Últimas alertas (tabla): ", "las diez alertas más recientes con su hora, aula, "
                      "temperatura y umbral."),
                     ("Tendencia de temperatura y luminosidad (24 h): ", "serie de tiempo con dos ejes, más la "
                      "línea punteada roja del umbral dinámico."),
                     ("Comparativa Aula A vs. Aula B: ", "temperatura de ambas aulas en la misma gráfica, con "
                      "promedio, máximo y mínimo en la leyenda."),
                     ("Agregaciones diarias (tabla): ", "promedio, máximo y mínimo por día de los últimos siete "
                      "días, con los días cortados a la medianoche de Colombia.")):
    vineta((nombre, "b"), desc)
texto(("Variables interactivas: ", "b"), "Aula (se llena sola con los valores del tag aula), Magnitud "
      "(temperatura, humedad o luminosidad para la tabla diaria) y Agrupar cada (1 min a 1 h, define la "
      "ventana de promedio de las gráficas). Al cambiarlas se recalculan todos los paneles.")
texto(("Exportación: ", "b"), "el dashboard se exportó en JSON con exportar_dashboard.py, que lo descarga por la "
      "API de Grafana al archivo evidencias/dashboard_exportado.json. Es equivalente a Share → Export → Save to "
      "file, y el mismo JSON (dashboard_iot_uts.json) permite importarlo en cualquier otra instalación.")
figura(buscar("dashboard_alerta*.jpg") or buscar("dashboard*.png") or buscar("dashboard*.jpg"),
       "Dashboard final en Grafana con la variable Aula = Aula_A, después de la prueba de anomalía: la tabla "
       "de alertas registra el evento y la tabla diaria refleja el máximo inyectado.",
       aviso="[Pegar aquí la captura del dashboard completo: guárdala como evidencias/dashboard.png]")
if buscar("dashboard_variables*.jpg"):
    texto("Al cambiar las variables a Aula = Aula_B y Agrupar cada = 15m, todos los paneles se recalculan. "
          "Como el Aula B tiene siete días de histórico, la tabla de agregaciones muestra un renglón por día y "
          "en la tendencia se aprecia el ciclo diario completo de temperatura y luminosidad.")
    figura(buscar("dashboard_variables*.jpg"), "El mismo dashboard con Aula = Aula_B y agrupación de 15 minutos.")

# =====================================================================
# 7. ALERTAS DINÁMICAS
# =====================================================================
h1("7. Sistema de Alertas Dinámicas")
h2("7.1 Lógica del umbral dinámico")
texto("Un umbral fijo, por ejemplo 30 °C, sirve para todas las aulas por igual y por eso falla: en un salón "
      "que siempre está fresco no avisa cuando la temperatura sube de forma anormal, y en uno que siempre es "
      "caluroso dispara alarmas a cada rato. El umbral dinámico aprende qué es normal para cada aula:")
parrafo("flujo", [("Umbral = μ + 2σ", "b")])
texto("donde μ es la temperatura media y σ la desviación estándar de las lecturas de los últimos siete días. "
      "Si los datos se distribuyen de forma aproximadamente normal, cerca del 97,7 % de las lecturas quedan por "
      "debajo de μ + 2σ, así que superar ese valor es algo poco frecuente que merece atención.")
texto("Cada 20 segundos, el script alerta_umbral_dinamico.py hace lo siguiente para cada aula:")
for paso in ("Consulta en InfluxDB, con Flux, el conteo, la media y la desviación estándar de la temperatura "
             "entre hace siete días y hace diez minutos. Se excluyen los últimos diez minutos para que una "
             "anomalía que está ocurriendo no infle la media y se tape a sí misma.",
             "Si hay menos de 30 muestras usa un umbral por defecto de 30 °C, porque con tan pocos datos la media "
             "y la desviación no son representativas. Además, la desviación nunca se toma menor a 0,2 °C, para "
             "que un aula muy estable no genere alertas por una variación mínima.",
             "Compara el promedio del último par de minutos con el umbral y guarda el umbral en InfluxDB.",
             "Si la temperatura lo supera, escribe la alerta en evidencias/alertas.log y en el measurement "
             "alertas, genera una gráfica PNG como evidencia y publica en los feeds led-rojo y buzzer de Adafruit "
             "IO. Como el NodeMCU está suscrito a ellos por MQTT, el LED se enciende y el buzzer suena tres "
             "segundos en el aula. Si se configura una cuenta de Gmail con contraseña de aplicación, también "
             "envía un correo.",
             "Para no saturar de mensajes, una misma aula no vuelve a alertar en cinco minutos; cuando la "
             "temperatura regresa por debajo del umbral, se registra la normalización y se apaga el LED."):
    vineta(paso)

h2("7.2 Simulación de la anomalía y evidencia")
texto("La prueba se hizo inyectando los datos a mano en InfluxDB, como pide la guía. Desde la interfaz web "
      "(Load Data → Buckets → iot_aulas → Add Data → Line Protocol) se cargaron ocho lecturas del Aula A entre "
      "42,6 y 44,0 °C, una cada 5 segundos, con precisión en segundos y la etiqueta fuente=anomalia_manual para "
      "distinguirlas de las reales. Cada línea tiene esta forma:")
codigo(["ambiente,aula=Aula_A,dispositivo=inyeccion_manual,fuente=anomalia_manual temperatura=43.8 1795192703"])
figura(buscar("influx*.jpg") or buscar("influx*.png"), "Inyección manual de la anomalía en InfluxDB mediante Line Protocol.",
       aviso="[Pegar aquí la captura de la carga en InfluxDB]")
texto("El mismo procedimiento quedó automatizado en SIMULAR_ANOMALIA.bat (simular_anomalia.py), por si se "
      "quiere repetir la prueba sin entrar a la interfaz de InfluxDB.")
if alerta:
    texto("El sistema detectó la anomalía en la revisión siguiente. A las "
          f"{alerta['hora'][11:]} del {alerta['hora'][:10]} el promedio de los dos últimos minutos del "
          f"{alerta['aula'].replace('_', ' ')} fue de {alerta['temp']} °C, por encima del umbral dinámico de "
          f"{alerta['umbral']} °C ({alerta['detalle']}). El valor es menor que las lecturas inyectadas porque el "
          "promedio mezcla los datos falsos con las lecturas reales del sensor de esos mismos minutos. Este es el "
          "extracto del archivo alertas.log:")
    ini = max(0, alerta["i"] - 6)
    codigo(lineas_log[ini:alerta["i"] + 6])
    texto("En el mismo instante se comprobó la respuesta física en el aula: el NodeMCU recibió por MQTT las "
          "órdenes de los feeds led-rojo y buzzer, el LED rojo se encendió y el buzzer sonó durante unos tres "
          "segundos, de modo que la alerta no se quedó solo en la pantalla del computador.")
else:
    texto(("[Ejecuta SIMULAR_ANOMALIA.bat con el sistema de alertas abierto y vuelve a generar el informe: "
           "aquí aparecerá el extracto real de alertas.log]", "bi rojo"))
figura(buscar("alerta_*.png"), "Gráfica generada automáticamente por el sistema al disparar la alerta: "
       "temperatura, media y umbral dinámico.",
       aviso="[Aquí se insertará la gráfica evidencias/alerta_Aula_A_....png]")
if buscar("consola*.png") or buscar("consola*.jpg"):
    figura(buscar("consola*.png") or buscar("consola*.jpg"), "Ventana del sistema de alertas en el momento de la alerta.")

# =====================================================================
# 8. ORGANIZACIÓN DEL REPOSITORIO
# =====================================================================
h1("8. Organización del Repositorio")
codigo(["Semana15_Visualizacion_Alertas/",
        "├── EJECUTAR_TODO.bat           instala, configura y arranca todo",
        "├── iniciar_servicios.bat       arranca InfluxDB y Grafana",
        "├── iniciar_scripts.bat         arranca ingesta, simulador y alertas",
        "├── SIMULAR_ANOMALIA.bat        inyecta la anomalía de prueba",
        "├── ACTUALIZAR_DASHBOARD_Y_ALERTAS.bat  aplica cambios sin reinstalar",
        "├── proyecto_iot_esp8266.ino    código del NodeMCU (MQTT, LED y buzzer)",
        "├── docker-compose.yml          alternativa con Docker",
        "├── config_iot.py               configuración compartida",
        "├── configurar_influxdb.py      configuración inicial de InfluxDB",
        "├── ingesta_influx.py           Adafruit IO -> InfluxDB",
        "├── simulador_aula_b.py         datos de la segunda aula",
        "├── alerta_umbral_dinamico.py   umbral μ + 2σ y alertas",
        "├── simular_anomalia.py         inyección manual de valores altos",
        "├── limpiar_lecturas_invalidas.py  borra lecturas imposibles del sensor",
        "├── exportar_dashboard.py       exporta el dashboard a JSON",
        "├── dashboard_iot_uts.json      dashboard de Grafana",
        "├── generar_informe.py          genera este documento",
        "└── evidencias/                 capturas, alertas.log, gráficas y JSON exportado"])

# =====================================================================
# 9. CONCLUSIONES
# =====================================================================
h1("9. Conclusiones")
for c in ("InfluxDB resultó más adecuada que SQLite para esta etapa: las agregaciones por ventanas de tiempo "
          "(promedio cada 5 minutos, máximos diarios) se escriben en una sola línea de Flux con aggregateWindow, "
          "algo que en SQL exigía consultas con GROUP BY sobre fechas convertidas a texto.",
          "Grafana permitió pasar de una tabla de números a una vista que se entiende en segundos. Las variables "
          "del dashboard hacen que el mismo tablero sirva para cualquier aula sin duplicar paneles.",
          "El umbral μ + 2σ se adapta a cada salón. Excluir los últimos diez minutos del cálculo fue clave: sin "
          "ese detalle, una anomalía larga terminaría subiendo la media y ocultándose a sí misma.",
          "Comparar created_at antes de escribir resolvió las lecturas duplicadas que se habían observado en la "
          "Semana 14.",
          "La alerta no se queda en la pantalla: llega por MQTT al NodeMCU y enciende el LED y el buzzer, de modo "
          "que quien está en el aula también se entera. Como mejora queda reemplazar el Aula B simulada por un "
          "segundo NodeMCU real."):
    vineta(c)

# =====================================================================
# 10. ANEXOS
# =====================================================================
salto()
h1("10. Anexos: Código Fuente")
for letra, archivo in zip("ABCDEF", ("config_iot.py", "ingesta_influx.py", "simulador_aula_b.py",
                                     "alerta_umbral_dinamico.py", "simular_anomalia.py", "configurar_influxdb.py")):
    h2(f"Anexo {letra}. {archivo}")
    with open(os.path.join(AQUI, archivo), encoding="utf-8") as f:
        # La clave real de Adafruit IO nunca se imprime en el informe
        codigo([re.sub(r'(AIO_KEY\s*=\s*)"[^"]*"', r'\1"TU_AIO_KEY"', l.rstrip("\n")) for l in f])

h1("11. Referencias")
for autor, titulo, url in (("Grafana Labs. (2026). ", "Grafana documentation", ". https://grafana.com/docs/grafana/latest/"),
                           ("InfluxData. (2026). ", "InfluxDB OSS v2 documentation", ". https://docs.influxdata.com/influxdb/v2/"),
                           ("InfluxData. (2026). ", "Flux language documentation", ". https://docs.influxdata.com/flux/"),
                           ("InfluxData. (2026). ", "influxdb-client-python", ". https://github.com/influxdata/influxdb-client-python"),
                           ("Adafruit. (2024). ", "Adafruit IO HTTP API", ". https://io.adafruit.com/api/docs/")):
    parrafo("referencia", [(autor, ""), (titulo, "i"), (url, "")])

# ---------- Pie de pagina: Semana 15 ----------
for seccion in doc.sections:
    for pie in (seccion.footer, seccion.first_page_footer):
        for t in pie._element.iter(qn("w:t")):
            t.text = (t.text.replace("Semana 14 · Almacenamiento ", "Semana 15 · Visualización y Alertas ")
                      .replace(" con SQLite · Página ", " · Página "))

doc.save(SALIDA)
print(f"[OK] Informe generado: {SALIDA}")
