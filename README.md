# Síndrome de Pandora em Felinos — site da tese e ferramentas de estudo

Site do referencial teórico e do acompanhamento da tese de doutorado (UFC): painel de indicadores, metas, projeto IoT, mapa mental, galeria, normas e estatísticas do acervo.

Publicado em: https://rcminitor.github.io/S-ndrome-Pandora/

Os PDFs de artigos de terceiros não estão neste repositório; ficam apenas no cofre privado.

## Ferramentas que rodam no PC

| O quê | Como abrir |
|---|---|
| **Painel de Estudo**: Para ler · Lidos · Acervo do cofre · Minha tese + orientador | dois cliques em `Iniciar painel.bat` |
| Ler um PDF solto | arrastar o PDF para `Ler com o agente.bat` |
| Estatísticas do acervo (aba do site) | `python analise\estatisticas.py` |
| Configurar a IA (OmniRoute gratuito ou chave) | `python agentes_crewai\configurar.py` |

Primeira vez: `pip install -r agentes_crewai\requirements.txt` e depois `python agentes_crewai\configurar.py`.
Detalhes em [`agentes_crewai/README.md`](agentes_crewai/README.md).
