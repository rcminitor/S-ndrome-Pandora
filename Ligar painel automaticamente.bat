@echo off
chcp 65001 >nul
rem Faz o Painel de Estudo ligar sozinho (escondido) sempre que voce entrar no Windows.
rem Nao precisa de administrador. Para desfazer: "Desligar painel automatico.bat".
set "INICIAR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Painel Pandora.bat"
(
  echo @echo off
  echo start "" pythonw "%~dp0painel_local\servidor.py" --sem-navegador
) > "%INICIAR%"
start "" pythonw "%~dp0painel_local\servidor.py" --sem-navegador
echo.
echo Pronto. O painel liga sozinho ao entrar no Windows e ja esta ligado agora.
echo Use pelo site: https://rcminitor.github.io/S-ndrome-Pandora/  (aba "Estudo com agentes")
pause
