@echo off
chcp 65001 >nul
rem Primeira vez: liga a pasta do cofre ao repositorio PRIVADO sindrome-de-pandora no GitHub.
rem Nada e apagado. Depois disso o painel faz o backup sozinho, uma vez por dia.
cd /d "%~dp0"
python painel_local\backup_cofre.py --ligar
pause
