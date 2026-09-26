# Equipe CrewAI de estudo — Síndrome de Pandora

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
copy .env.exemplo .env
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
