# Agentes de estudo — Síndrome de Pandora

## Painel de Estudo (o jeito mais fácil)

Dois cliques em **`Iniciar painel.bat`** (na raiz do projeto). O painel abre no navegador, em `http://127.0.0.1:8765`, e só funciona no seu PC.

| Aba | O que faz |
|---|---|
| **Para ler** | Clique num PDF e em **Ler com o agente**. Ele traz só o relevante (traduzido na íntegra), mostra quem o autor citou em cada trecho e baixa os artigos citados de acesso aberto para `<artigo> - citados`, na mesma pasta. **Marcar como lido** move o PDF e a leitura para Lidos. |
| **Lidos** | O que você já estudou, com a leitura do agente ao lado. |
| **Acervo do cofre** | Os PDFs das pastas `PDF\` do cofre. Não são movidos: o agente trabalha numa cópia em Para ler, para não quebrar os links do Obsidian. |
| **Minha tese** | Editor das seções (arquivos `.md` em `Notas\Tese`, que abrem também no Obsidian) + **orientador**: *Me questione*, *Revise o texto* ou debata respondendo a ele. As conversas ficam em `Notas\Tese\Debates`. |

Pastas criadas no cofre: `Leitura\1_Para_ler`, `Leitura\2_Lido` e `Notas\Tese`.

### Qual IA usar

`python configurar.py` oferece: **1** OmniRoute (gratuito, no PC) · **2** Gemini direto (chave do Google AI Studio) · **3** Anthropic (paga) · **4** OpenAI (paga). Para testar a escolha: `python testar_ia.py`.

### Gratuito primeiro, pago quando o gratuito acabar

Com o OmniRoute ou o Gemini como principal e uma **chave paga de reserva** (Anthropic `sk-ant-…` ou OpenAI `sk-…`) (o `configurar.py` pergunta), todos os agentes tentam primeiro o gratuito. Se ele falhar (limite estourado, fora do ar, chave recusada), a mesma tarefa é refeita com a chave paga, sozinha. A reserva vale por 30 minutos (`RESERVA_MINUTOS`) e depois o gratuito é tentado de novo. O registro avisa sempre que a reserva paga entra.

O orientador usa **só** o seu texto e as leituras já feitas pelo agente. Ele não inventa referência: o que vier de conhecimento geral aparece marcado como "precisa de fonte".

## Equipe de estudo (`estudo_crew.py`)

Três agentes que ensinam um tema da tese usando **só o seu acervo** (inventário + fichamentos):

| Agente | Modelo | O que entrega |
|---|---|---|
| Tutor | forte (`MODELO_TUTOR`) | explicação acadêmica + versão simples + o que falta ler |
| Examinador | barato (`MODELO_BARATO`) | 5 flashcards → aparecem na aba **Estudo & Normas** do site |
| Revisor de rastreabilidade | barato | frases sem fonte ou com código errado |

## Instalar e configurar (uma vez)

```
cd agentes_crewai
pip install -r requirements.txt
python configurar.py
```
Preencha `LLM_API_KEY` no `.env` **desta pasta** (ele não vai para o GitHub).

## Usar

```
python estudo_crew.py "eixo HHA e adrenais" --simular      # vê o contexto e o custo estimado, sem gastar
python estudo_crew.py "eixo HHA e adrenais"                # roda de verdade
python estudo_crew.py "estresse" --codigos 50,S4           # escolhe as fontes à mão
python estudo_crew.py "origem do termo" --fichamento "caminho\do\fichamento.md"
```
Saídas: `saidas/<data>_<tema>.md`, `saidas/uso_tokens.csv` e `../dados_flashcards.js`.

## Por que gasta poucos tokens

1. **Nunca manda PDF**: manda de 1 a 5 “cartões” de ~120 tokens cada, tirados do inventário.
2. **Teto de contexto** (`CONTEXTO_MAX_CHARS`) e **teto de resposta** por agente (`MAX_TOKENS_*`).
3. **Modelo forte só onde precisa** (Tutor); os outros dois usam o barato.
4. **Cada agente vê só o necessário**: o Examinador não recebe os cartões, só a explicação.
5. **Sem memória, sem delegação, no máximo 2 iterações**: nada de conversa interna escondida.
6. **Cache**: repetir a mesma pergunta com o mesmo contexto custa 0 token.
7. **Medição**: `uso_tokens.csv` registra o gasto de cada execução.
8. **Gateway opcional**: `LLM_BASE_URL` aponta para um gateway compatível com OpenAI (ex.: seu OmniRoute) para usar modelos gratuitos.

> Regra da tese: o texto gerado é material de estudo. Nada vai para a tese sem conferência no PDF.

---

# Leitor de artigos (`leitor_artigos.py`)

Lê um PDF, traduz **na íntegra** os trechos relevantes à tese, mostra **quem o autor citou em cada trecho** e segue essas citações: localiza cada artigo citado e **baixa o PDF quando existe versão legal de acesso aberto**. Depois repete o processo nos artigos baixados (árvore de citações).

```
python leitor_artigos.py "C:\caminho\artigo.pdf" --simular        # vê trechos, citações e custo, sem gastar nada
python leitor_artigos.py "C:\caminho\artigo.pdf"                  # traduz + segue as citações (profundidade 1)
python leitor_artigos.py artigo.pdf --profundidade 2               # + quem os citados citaram
python leitor_artigos.py artigo.pdf --sem-traducao                 # só citações e downloads (0 token)
python leitor_artigos.py artigo.pdf --baixar todos                 # todas as referências, não só as dos trechos relevantes
```

**O relatório** (`saidas/leitura_<artigo>.md`) traz:
1. Os trechos relevantes: página, texto original e tradução integral, com a lista "O autor cita aqui".
2. A árvore de citações, com o estado de cada item: 📄 baixado · 🔓 aberto · 🔒 sem acesso aberto (Portal CAPES / biblioteca) · ❓ DOI não localizado.
3. Os trechos não traduzidos, **mantidos no original**. Nada é retirado.

**Onde entra a IA (e onde não entra):**

| Etapa | Quem faz | Custo |
|---|---|---|
| Extrair texto, páginas e citações | Python (PyMuPDF) | 0 token |
| Pré-filtro por termos da tese | Python | 0 token |
| Triagem fina dos trechos | agente Triador (modelo barato, só devolve os números dos trechos) | baixo |
| Tradução integral | agente Tradutor, em lotes, com cache | principal |
| Achar DOI e acesso aberto, baixar | Python (Crossref, OpenAlex, Unpaywall) | 0 token |

**Salvaguardas:**
- A tradução é conferida: se sair muito mais curta que o original ou perder um marcador de citação, o trecho é marcado com ⚠️.
- DOI achado por busca aparece como "conferir".
- PDF sem camada de texto não é traduzido: faça OCR antes.
- Só baixa acesso aberto legal. Artigo pago aparece como 🔒, com a indicação do Portal CAPES.

Os PDFs baixados (`biblioteca/`) e as traduções (`saidas/leitura_*`) **não vão para o GitHub** (direitos autorais); ficam só no seu PC.
