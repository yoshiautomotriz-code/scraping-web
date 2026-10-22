@echo off
title Servidor OECE - Buscador de Contrataciones
cd /d "%~dp0"
echo ========================================================
echo   Iniciando Servidor OECE y Visualizador Web
echo ========================================================
echo Abriendo navegador en http://localhost:8000 ...
start http://localhost:8000
python servidor.py
pause
