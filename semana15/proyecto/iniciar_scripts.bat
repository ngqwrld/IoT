@echo off
REM Abre la ingesta real, el simulador del Aula B y el sistema de alertas.
setlocal
cd /d "%~dp0"
set "PY=python"
where py >nul 2>nul && set "PY=py -3"
py -3.12 --version >nul 2>nul && set "PY=py -3.12"
start "1 Ingesta Adafruit IO a InfluxDB" /D "%CD%" cmd /k %PY% ingesta_influx.py
start "2 Simulador Aula B" /D "%CD%" cmd /k %PY% simulador_aula_b.py
timeout /t 5 /nobreak >nul
start "3 Alertas dinamicas" /D "%CD%" cmd /k %PY% alerta_umbral_dinamico.py
echo [OK] Scripts en ejecucion (tres ventanas).
if /i not "%~1"=="nopause" pause
