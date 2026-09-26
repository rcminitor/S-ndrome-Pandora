@echo off
chcp 65001 >nul
rem Arraste um PDF para este arquivo (ou use "Enviar para") e o agente le o artigo.
rem O relatorio fica ao lado do PDF e os artigos citados em "<nome> - citados".
if "%~1"=="" (echo Arraste um PDF sobre este arquivo. & pause & exit /b)
cd /d "%~dp0agentes_crewai"
python leitor_artigos.py "%~1" --destino "%~dpn1 - citados" --relatorio-dir "%~dp1"
start "" "%~dpn1.leitura.md"
pause
