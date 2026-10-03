@echo off
chcp 65001 > nul
title Processar Novos Documentos (Multi-Formato: PDF, Word, Texto, Imagem)
echo ============================================================
echo Triagem e Ingestao com Custo ZERO de Tokens de IA
echo ============================================================
python \\%~dp0painel_local\mover_pdfs_fichados.py\\ %*
echo.
pause
