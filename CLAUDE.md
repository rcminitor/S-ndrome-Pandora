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

Os PDFs existem **somente no computador local** do Romulo, dentro do cofre. Para abri-los:

- A função `cofreUrl(caminho)` em `painel.js` prefixia com:
  `file:///C:/Users/rcmin/OneDrive/Documents/Pos-Graduacao/Doutorado%20UFC/S%C3%ADndrome%20de%20Pandora/`
- Isso funciona quando o site é aberto **localmente** (`file://` ou servidor local).
- No GitHub Pages (`https://`), o navegador bloqueia `file://` — os links não abrem, mas o caminho fica visível.

**Nunca mude `cofreUrl` para usar caminhos relativos** — o painel não está dentro do cofre.

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
