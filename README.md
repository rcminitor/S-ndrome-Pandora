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
