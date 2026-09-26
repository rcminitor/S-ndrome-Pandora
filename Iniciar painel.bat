@echo off
chcp 65001 >nul
rem Abre o Painel de Estudo no navegador. Feche esta janela para desligar.
cd /d "%~dp0"
python painel_local\servidor.py
pause
