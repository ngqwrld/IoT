@echo off
REM Inyecta lecturas altas de temperatura en InfluxDB para disparar la alerta.
setlocal
cd /d "%~dp0"
set "PY=python"
where py >nul 2>nul && set "PY=py -3"
py -3.12 --version >nul 2>nul && set "PY=py -3.12"
%PY% simular_anomalia.py Aula_A
echo.
echo Espera unos 20 segundos y revisa la ventana "3 Alertas dinamicas".
pause
