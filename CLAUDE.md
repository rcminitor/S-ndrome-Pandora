# Painel "Síndrome de Pandora" — instruções para o Claude

Este repositório é o **site de acompanhamento da tese** do Romulo (UFC). Responda sempre em **português**.

- **Este repo:** `C:\Users\rcmin\Projetos\S-ndrome-Pandora\` — HTML, CSS, JS, commit e deploy.
- **GitHub Pages:** `https://rcminitor.github.io/S-ndrome-Pandora/`
- **Cofre Obsidian (banco de dados):** `C:\Users\rcmin\OneDrive\Documents\Pos-Graduacao\Doutorado UFC\Síndrome de Pandora\` — repositório Git separado; nunca faça commit aqui pelo painel.

---

## Regra fundamental de dois repos

O cofre é a **fonte de dados** (notas, fichamentos, inventário, PDFs).
O painel é o **local de publicação** (lê dados do cofre, exibe no browser, faz commit/push para GitHub Pages).

Nunca misture: commits do painel ficam em `C:\Users\rcmin\Projetos\S-ndrome-Pandora\`; commits do cofre ficam no outro diretório.

---

## Arquivos principais

| Arquivo | Função |
|---|---|
| `index.html` | Estrutura de abas e modais |
| `painel.js` | KPIs, gráficos, aba PDFs, Pomodoro, Gantt |
| `app.js` | Aba Acervo (inventário, drawer, filtros) |
| `painel.css` | Estilo global |
| `dados_inventario.js` | 64 registros do acervo (exportados do cofre) |
| `dados_pdfs.js` | Lista de PDFs disponíveis (exportados do cofre) |
| `dados_metas.js` | Metas e cronograma |
| `dados_estadoarte.js` | Fichamentos para a aba Estado da Arte |

---

## Caminhos de PDF — como funciona

Os campos `arquivo` em `dados_pdfs.js` e `dados_inventario.js` contêm caminhos **relativos à raiz do cofre**, por exemplo:

```
PDF/Primeiras Leituras/01_Stress in owned cats.pdf
```

Os PDFs existem **somente no cofre**, no computador local do Romulo. **Nunca** os copie
para este repositório: ele é público e os PDFs têm direitos autorais. A pasta `PDF/`
está no `.gitignore`; o Guardião (`acervo.py`), o teste `test_site_nao_publica_pdfs` e
a conferência pós-deploy (`verificar_site_publicado.py`) falham se algum PDF aparecer
no site. O histórico foi limpo em 07/10/2026 para retirar os PDFs publicados antes.

Para abrir um PDF:

- `cofreUrl(caminho)` em `painel.js` aponta para o Painel de Estudo local:
  `http://127.0.0.1:8765/pdf?id=acervo:<caminho sem o prefixo PDF/>`, que lê do cofre.
- Antes de abrir, o site testa `/api/ping`. Com o painel desligado, avisa e abre o DOI
  da referência (ou a busca do título no Google Acadêmico).

---

## Convenção de abas

O site tem estas abas (em ordem):

| ID | Rótulo |
|---|---|
| `tab-painel` | Painel (padrão ao carregar) |
| `tab-estadoarte` | Estado da Arte |
| `tab-metas` | Metas |
| `tab-estudo` | Normas |
| `tab-inventory` | Acervo |
| `tab-overview` | Visão Geral |

Abas removidas em sessões anteriores (não recriar): Galeria, PDFs, Registro, Guia, Roteiro, Núcleos.

---

## Deploy

O site é implantado automaticamente via GitHub Pages na branch `main`. Após commit e push, aguarde ~1 minuto para as mudanças aparecerem online.

```
cd C:\Users\rcmin\Projetos\S-ndrome-Pandora
git add <arquivos>
git commit -m "mensagem"
git push origin main
```
