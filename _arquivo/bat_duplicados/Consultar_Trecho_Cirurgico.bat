@echo off
chcp 65001 > nul
title Consulta Cirúrgica de Trechos (Economia de 95%%+ em Tokens)
echo ========================================================================
echo   Busca Cirúrgica de Trechos em Documentos (Custo ZERO de IA)
echo ========================================================================
python " \%~dp0painel_local\buscar_trecho_cirurgico.py\\ %*
echo.
pause
