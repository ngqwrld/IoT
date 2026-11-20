@echo off
REM ==================================================================
REM  SEMANA 15 - Instala, configura y arranca TODO el sistema:
REM   1. Descarga InfluxDB 2.10.1 y Grafana 13.3.1 (instalacion manual)
REM   2. Configura Grafana: usuario, fuente de datos y dashboard
REM   3. Arranca InfluxDB y Grafana y crea org/bucket/token en InfluxDB
REM   4. Instala las librerias de Python
REM   5. Abre la ingesta (Adafruit -> InfluxDB), el simulador del Aula B
REM      y el sistema de alertas, cada uno en su ventana
REM   6. Exporta el dashboard a JSON y lo abre en el navegador
REM ==================================================================
setlocal
cd /d "%~dp0"
set "PROY=%CD%"
set "BASE=%USERPROFILE%\IoT_S15"
set "INFLUX_URL=https://download.influxdata.com/influxdb/releases/influxdb2-2.10.1-windows_amd64.zip"
set "GRAFANA_URL=https://dl.grafana.com/grafana/release/13.3.1/grafana_13.3.1_42849527790_windows_amd64.tar.gz"

set "PY=python"
where py >nul 2>nul && set "PY=py -3"
py -3.12 --version >nul 2>nul && set "PY=py -3.12"

echo.
echo ==== [1/6] Instalando InfluxDB y Grafana en %BASE% ====
if not exist "%BASE%\descargas" mkdir "%BASE%\descargas"
if not exist "%BASE%\influx_datos" mkdir "%BASE%\influx_datos"
if not exist "%BASE%\dashboards" mkdir "%BASE%\dashboards"

if exist "%BASE%\influxdb" (
    echo [OK] InfluxDB ya estaba instalado.
) else (
    echo Descargando InfluxDB ^(unos 45 MB^)...
    curl.exe -L --fail -o "%BASE%\descargas\influxdb.zip" "%INFLUX_URL%"
    if errorlevel 1 goto :error_descarga
    mkdir "%BASE%\influxdb"
    tar -xf "%BASE%\descargas\influxdb.zip" -C "%BASE%\influxdb"
)

if exist "%BASE%\grafana\bin" (
    echo [OK] Grafana ya estaba instalado.
) else (
    echo Descargando Grafana ^(unos 200 MB, puede tardar^)...
    curl.exe -L --fail -o "%BASE%\descargas\grafana.tar.gz" "%GRAFANA_URL%"
    if errorlevel 1 goto :error_descarga
    tar -xzf "%BASE%\descargas\grafana.tar.gz" -C "%BASE%"
    for /d %%D in ("%BASE%\grafana-*" "%BASE%\grafana_*") do if not exist "%BASE%\grafana" move "%%D" "%BASE%\grafana" >nul
)
if not exist "%BASE%\grafana\bin" (
    echo [ERROR] No se encontro Grafana descomprimido en %BASE%\grafana
    goto :fin
)

echo.
echo ==== [2/6] Configurando Grafana (usuario, fuente de datos y dashboard) ====
if not exist "%BASE%\grafana\conf\provisioning\datasources" mkdir "%BASE%\grafana\conf\provisioning\datasources"
if not exist "%BASE%\grafana\conf\provisioning\dashboards" mkdir "%BASE%\grafana\conf\provisioning\dashboards"
copy /y "%PROY%\dashboard_iot_uts.json" "%BASE%\dashboards\" >nul
> "%BASE%\grafana\conf\custom.ini" (
    echo [server]
    echo http_port = 3000
    echo [security]
    echo admin_user = admin
    echo admin_password = admin12345
    echo [users]
    echo default_theme = light
    echo [dashboards]
    echo default_home_dashboard_path = %BASE%\dashboards\dashboard_iot_uts.json
)
> "%BASE%\grafana\conf\provisioning\datasources\influxdb_iot.yaml" (
    echo apiVersion: 1
    echo datasources:
    echo   - name: InfluxDB_IoT
    echo     uid: influxdb_iot
    echo     type: influxdb
    echo     access: proxy
    echo     url: http://localhost:8086
    echo     isDefault: true
    echo     jsonData:
    echo       version: Flux
    echo       organization: uts
    echo       defaultBucket: iot_aulas
    echo     secureJsonData:
    echo       token: uts-iot-semana15-token-local
)
> "%BASE%\grafana\conf\provisioning\dashboards\iot_uts.yaml" (
    echo apiVersion: 1
    echo providers:
    echo   - name: IoT_UTS
    echo     folder: IoT UTS
    echo     type: file
    echo     allowUiUpdates: true
    echo     options:
    echo       path: '%BASE%\dashboards'
)
echo [OK] Grafana configurado.

echo.
echo ==== [3/6] Arrancando InfluxDB y Grafana ====
call "%PROY%\iniciar_servicios.bat" nopause
%PY% configurar_influxdb.py
if errorlevel 1 goto :fin

echo.
echo ==== [4/6] Instalando librerias de Python ====
%PY% -m pip install -q -r requirements.txt

echo.
echo ==== [5/6] Abriendo ingesta, simulador y alertas ====
call "%PROY%\iniciar_scripts.bat" nopause

echo.
echo ==== [6/6] Exportando el dashboard y abriendolo en el navegador ====
%PY% exportar_dashboard.py
start "" "http://localhost:3000/d/iot-uts-s15"

echo.
echo ==================================================================
echo  LISTO. Grafana: http://localhost:3000  (admin / admin12345)
echo         InfluxDB: http://localhost:8086 (admin / admin12345)
echo  Deja abiertas las ventanas negras. Para probar la alerta ejecuta
echo  SIMULAR_ANOMALIA.bat
echo ==================================================================
goto :fin

:error_descarga
echo [ERROR] Fallo una descarga. Revisa tu conexion a Internet y vuelve a ejecutar.

:fin
echo.
pause
