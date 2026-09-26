@echo off
chcp 65001 >nul
rem Desliga o painel agora e impede que ele ligue sozinho ao entrar no Windows.
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Painel Pandora.bat" 2>nul
curl -s -X POST http://127.0.0.1:8765/api/desligar >nul 2>&1
echo Painel desligado e removido da inicializacao do Windows.
pause
