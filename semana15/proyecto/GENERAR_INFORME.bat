@echo off
REM Genera el Word final insertando las capturas y el log de la carpeta evidencias.
setlocal
cd /d "%~dp0"
set "PY=python"
where py >nul 2>nul && set "PY=py -3"
py -3.12 --version >nul 2>nul && set "PY=py -3.12"
%PY% generar_informe.py
start "" "Semana15_Visualizacion_Alertas_IoT.docx"
pause
