@echo off
REM ANTES de ejecutarlo, cierra las ventanas "1 Ingesta..." y "3 Alertas dinamicas".
REM 1) Borra lecturas invalidas del sensor  2) Actualiza el dashboard
REM 3) Reabre la ingesta y las alertas con el codigo nuevo
setlocal
cd /d "%~dp0"
set "PY=python"
where py >nul 2>nul && set "PY=py -3"
py -3.12 --version >nul 2>nul && set "PY=py -3.12"
%PY% limpiar_lecturas_invalidas.py
copy /y "dashboard_iot_uts.json" "%USERPROFILE%\IoT_S15\dashboards\" >nul && echo [OK] Dashboard actualizado (Grafana lo recarga en unos 10 segundos).
start "1 Ingesta Adafruit IO a InfluxDB" /D "%CD%" cmd /k %PY% ingesta_influx.py
timeout /t 3 /nobreak >nul
start "3 Alertas dinamicas" /D "%CD%" cmd /k %PY% alerta_umbral_dinamico.py
echo [OK] Ingesta y alertas reiniciadas.
pause
