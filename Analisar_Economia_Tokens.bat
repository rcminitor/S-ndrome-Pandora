@echo off
chcp 65001 > nul
title Analisador de Economia de Tokens — Síndrome de Pandora
echo ============================================================
echo Calculando Consumo e Economia de Tokens (Metadados Primeiro)
echo ============================================================
python \\%~dp0painel_local\analisar_tokens_pdf.py\\ %*
echo.
pause
