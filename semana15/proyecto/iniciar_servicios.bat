@echo off
REM Arranca InfluxDB (puerto 8086) y Grafana (puerto 3000) en ventanas propias.
setlocal
set "BASE=%USERPROFILE%\IoT_S15"
set "INFLUXD="
for /r "%BASE%\influxdb" %%F in (influxd.exe) do if exist "%%F" set "INFLUXD=%%F"
if not defined INFLUXD (
    echo [ERROR] No se encontro influxd.exe. Ejecuta primero EJECUTAR_TODO.bat
    goto :fin
)
echo [INFO] Iniciando InfluxDB...
start "InfluxDB - NO CERRAR" "%INFLUXD%" --bolt-path "%BASE%\influx_datos\influxd.bolt" --engine-path "%BASE%\influx_datos\engine" --reporting-disabled
echo [INFO] Iniciando Grafana...
start "Grafana - NO CERRAR" /D "%BASE%\grafana" "%BASE%\grafana\bin\grafana.exe" server --homepath "%BASE%\grafana"
echo [OK] InfluxDB: http://localhost:8086   Grafana: http://localhost:3000
:fin
if /i not "%~1"=="nopause" pause
