# Síndrome de Pandora em Felinos — site da tese e ferramentas de estudo

Site do referencial teórico e do acompanhamento da tese de doutorado (UFC): painel de indicadores, metas, projeto IoT, mapa mental, galeria, normas e estatísticas do acervo.

Publicado em: https://rcminitor.github.io/S-ndrome-Pandora/

Os PDFs de artigos de terceiros não estão neste repositório; ficam apenas no cofre privado.

## Ferramentas que rodam no PC

| O quê | Como abrir |
|---|---|
| **Estudo com agentes** (aba do site): Para ler · Lidos · Acervo do cofre · Minha tese + orientador | uma vez: dois cliques em `Ligar painel automaticamente.bat`; depois é só abrir a aba no site |
| O mesmo painel, sem o site | `Iniciar painel.bat` ou http://127.0.0.1:8765 |
| Ler um PDF solto | arrastar o PDF para `Ler com o agente.bat` |
| Estatísticas do acervo (aba do site) | `python analise\estatisticas.py` |
| Configurar a IA (OmniRoute gratuito ou chave) | `python agentes_crewai\configurar.py` |

Primeira vez: `pip install -r agentes_crewai\requirements.txt` e depois `python agentes_crewai\configurar.py`.
Detalhes em [`agentes_crewai/README.md`](agentes_crewai/README.md).

## NotebookLM no painel local

O botão **NotebookLM** abre `/notebooklm`, com a conta Pro como principal e a
Plus selecionada manualmente. Esta integração opcional usa `notebooklm-py`
(testada com 0.8.2), uma biblioteca não oficial; mudanças no Google podem exigir
atualização. Ela não troca contas automaticamente nem envia PDFs por conta própria.

Com o CLI instalado, autentique cada conta separadamente:

```powershell
notebooklm -p pandora-pro login --browser chrome
# Somente se quiser conectar também a conta Plus:
notebooklm -p pandora-plus login --browser chrome
```

Na página, verifique a conexão, liste os cadernos, escolha um e clique em
**Vincular caderno**. Depois envie seu prompt. As consultas podem continuar a
conversa já existente no caderno; nenhuma conversa é apagada. Áudio, imagens e
envio de fontes ainda não estão integrados nesta primeira etapa.

Credenciais ficam nos perfis privados do NotebookLM, fora deste repositório.
Os vínculos de cadernos ficam em `%LOCALAPPDATA%\Pandora\notebooklm.json`.
Não publique essas pastas nem copie suas credenciais para o site. Reinicie o
painel após atualizar o código, quando não houver leituras em andamento.
