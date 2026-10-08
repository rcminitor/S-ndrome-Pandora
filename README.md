# Síndrome de Pandora em Felinos — site da tese e ferramentas de estudo

Site do referencial teórico e do acompanhamento da tese de doutorado (UFC): painel de indicadores, metas, projeto IoT, mapa mental, galeria, normas e estatísticas do acervo.

Publicado em: https://rcminitor.github.io/S-ndrome-Pandora/

Os PDFs dos artigos **não são publicados**: ficam só no cofre, no PC do Romulo
(direitos autorais dos periódicos). O site publica apenas os metadados — o
manifesto `dados_pdfs.js` lista os caminhos relativos ao cofre das fontes ativas.
Para ler um PDF, o site pede ao Painel de Estudo local (`http://127.0.0.1:8765`);
com o painel desligado, abre o DOI ou a busca do artigo. A pasta `PDF/` está no
`.gitignore`, e o Guardião e os testes falham se algum PDF aparecer no site.

## Publicação segura do acervo

O cofre é a origem dos PDFs e fichamentos. O painel mantém os registros já
revisados e só inclui uma fonte nova quando existe um PDF válido dentro de
`PDF/` do cofre (o PDF não é copiado para o site). A exportação não remove fontes automaticamente e não altera o cofre.

```powershell
# Conferir o que seria publicado, sem gravar
.\gerar-dados.ps1 -Check

# Sincronizar depois da conferência
.\gerar-dados.ps1

# Validar dados, vínculos, PDFs e testes de regressão
.\validar-painel.ps1
```

O Guardião bloqueia a publicação quando encontra código duplicado, fichamento
órfão, fonte sem PDF, caminho fora de `PDF/`, arquivo inválido ou status
“fichamento concluído” sem a ficha correspondente. O GitHub Actions repete essa
validação em cada envio para `main`.

## Ferramentas que rodam no PC

| O quê | Como abrir |
|---|---|
| **Estudo com agentes** (aba do site): Para ler · Lidos · Acervo do cofre · Minha tese + orientador | uma vez: dois cliques em `Ligar painel automaticamente.bat`; depois é só abrir a aba no site |
| O mesmo painel, sem o site | `Iniciar painel.bat` ou http://127.0.0.1:8765 |
| Ler um PDF solto | arrastar o PDF para `Ler com o agente.bat` |
| Estatísticas do acervo (aba do site) | `python analise\estatisticas.py` |
| Configurar a IA (OmniRoute gratuito ou chave) | `python agentes_crewai\configurar.py` |
| **Busca Cirúrgica de Trechos** (Economia 95%+ em tokens) | Consultar_Trecho_Cirurgico.bat |
| **Analisador de Economia de Tokens** (Multi-formato) | Analisar_Economia_Tokens.bat |
| **Processar Novos Documentos** (Triagem: PDF, Word, Texto, Imagem) | Processar_Novos_Documentos.bat |

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