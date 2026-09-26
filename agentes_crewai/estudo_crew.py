"""
Equipe CrewAI de estudo — Síndrome de Pandora
=============================================

Três agentes que ajudam a aprender um tema da tese usando SÓ o que já está
no acervo (inventário + fichamentos), com gasto mínimo de tokens:

  1. Tutor      — explica o tema em dois níveis (acadêmico e simples).
  2. Examinador — transforma a explicação em flashcards (vão para o site).
  3. Revisor    — aponta afirmações sem fonte do acervo (regra da tese).

Como economiza tokens
---------------------
  * Contexto compacto: nunca manda PDF. Monta "cartões" curtos a partir de
    dados_inventario.js (+ trecho opcional de um fichamento), com teto de
    caracteres (CONTEXTO_MAX_CHARS).
  * Modelo por agente: só o Tutor usa o modelo mais forte; Examinador e
    Revisor usam o modelo barato.
  * Teto de saída por agente (max_tokens) e temperatura baixa.
  * Cada tarefa recebe apenas o que precisa (o Examinador não vê os cartões).
  * Sem memória de longo prazo, sem delegação, no máximo 2 iterações.
  * Cache em disco: a mesma pergunta com o mesmo contexto custa zero.
  * Relatório de tokens em saidas/uso_tokens.csv a cada execução.

Uso
---
    cd agentes_crewai
    pip install -r requirements.txt
    copy .env.exemplo .env      (e preencha a chave NO .env desta pasta)
    python estudo_crew.py "eixo HHA e adrenais"
    python estudo_crew.py "eixo HHA" --codigos 50,51 --fichamento "..\\..\\Fichamentos\\51 — Fichamento — From FUS to Pandora syndrome.md"
    python estudo_crew.py "enriquecimento ambiental" --simular   (mostra o contexto e a estimativa de tokens, sem chamar o modelo)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

from dotenv import dotenv_values
from pydantic import BaseModel, Field

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
CACHE = AQUI / ".cache"
SAIDAS = AQUI / "saidas"
INVENTARIO = RAIZ / "dados_inventario.js"
FLASHCARDS_JS = RAIZ / "dados_flashcards.js"

# Configuração lida SÓ do .env desta pasta (nada de variável global).
CFG = {
    "MODELO_TUTOR": "anthropic/claude-sonnet-5",
    "MODELO_BARATO": "anthropic/claude-haiku-4-5-20251001",
    "LLM_BASE_URL": "",
    "LLM_API_KEY": "",
    "CONTEXTO_MAX_CHARS": "6000",
    "MAX_TOKENS_TUTOR": "900",
    "MAX_TOKENS_BARATO": "600",
    "MAX_CARTOES": "5",
    **{k: v for k, v in dotenv_values(AQUI / ".env").items() if v is not None},
}

REGRAS = (
    "Regras da tese: use APENAS os cartões fornecidos. Não invente autor, ano, "
    "página, número, amostra ou resultado. O que não estiver nos cartões recebe "
    "'NÃO CONFIRMADO'. Cite o código da fonte entre colchetes, ex.: [50]. "
    "Diferencie o que o artigo afirma de interpretação sua. Responda em português."
)


# ------------------------------------------------------------ contexto
def sem_acento(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def carregar_inventario() -> list[dict]:
    txt = INVENTARIO.read_text(encoding="utf-8-sig")
    return json.loads(txt[txt.index("["): txt.rindex("]") + 1])


def escolher_fontes(inv: list[dict], tema: str, codigos: list[str], limite: int) -> list[dict]:
    if codigos:
        return [a for a in inv if a["codigo"] in codigos][:limite]
    termos = [t for t in re.findall(r"\w{3,}", sem_acento(tema))]
    def pontos(a: dict) -> int:
        alvo = sem_acento(" ".join(a.get(k, "") for k in ("titulo", "grupo", "porQueLer", "comoUsar")))
        bonus = 2 if "fichamento concluido" in a.get("status", "") else 0
        return sum(alvo.count(t) for t in termos) + (bonus if termos else 0)
    ranqueadas = sorted(inv, key=pontos, reverse=True)
    return [a for a in ranqueadas if pontos(a) > 0][:limite]


def cartao(a: dict) -> str:
    corta = lambda t, n: (t or "").strip()[:n]
    return (
        f"[{a['codigo']}] {corta(a['titulo'], 140)} ({a['ano']}) — {a['status']}\n"
        f"  por que ler: {corta(a.get('porQueLer'), 260)}\n"
        f"  como usar: {corta(a.get('comoUsar'), 220)}\n"
        f"  tipo de estudo: {corta(a.get('tipoEstudo'), 160)}\n"
        f"  procedência da referência: {corta(a.get('procedencia'), 80)}"
    )


def montar_contexto(tema: str, codigos: list[str], fichamento: str | None) -> tuple[str, list[str]]:
    teto = int(CFG["CONTEXTO_MAX_CHARS"])
    fontes = escolher_fontes(carregar_inventario(), tema, codigos, int(CFG["MAX_CARTOES"]))
    partes = [cartao(a) for a in fontes]
    if fichamento:
        texto = Path(fichamento).read_text(encoding="utf-8")
        texto = re.sub(r"\n{3,}", "\n\n", re.sub(r"^---.*?---", "", texto, flags=re.S))  # tira frontmatter
        partes.append("TRECHO DE FICHAMENTO (conferido pelo pesquisador):\n" + texto)
    ctx = "\n\n".join(partes)
    if len(ctx) > teto:
        ctx = ctx[:teto] + "\n[contexto cortado no teto de caracteres]"
    return ctx, [a["codigo"] for a in fontes]


# ------------------------------------------------------------ saídas
class Flashcard(BaseModel):
    pergunta: str
    resposta: str = Field(description="curta, até 2 frases")
    fonte: str = Field(description="código entre colchetes, ex. [50], ou NÃO CONFIRMADO")


class Baralho(BaseModel):
    cards: list[Flashcard]


def gravar_flashcards(tema: str, cards: list[dict]) -> None:
    atuais = []
    if FLASHCARDS_JS.exists():
        t = FLASHCARDS_JS.read_text(encoding="utf-8")
        atuais = json.loads(t[t.index("["): t.rindex("]") + 1])
    vistos = {c["pergunta"] for c in atuais}
    hoje = datetime.now().date().isoformat()
    atuais += [{**c, "tema": tema, "data": hoje} for c in cards if c["pergunta"] not in vistos]
    FLASHCARDS_JS.write_text(
        "// Gerado por agentes_crewai/estudo_crew.py — revise antes de usar na tese.\n"
        "window.DADOS_FLASHCARDS = " + json.dumps(atuais, ensure_ascii=False, indent=1) + ";\n",
        encoding="utf-8",
    )


def registrar_uso(tema: str, uso: dict, do_cache: bool) -> None:
    SAIDAS.mkdir(exist_ok=True)
    arq = SAIDAS / "uso_tokens.csv"
    novo = not arq.exists()
    with arq.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if novo:
            w.writerow(["data", "tema", "prompt_tokens", "completion_tokens", "total_tokens", "cache"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), tema,
                    uso.get("prompt_tokens", 0), uso.get("completion_tokens", 0),
                    uso.get("total_tokens", 0), "sim" if do_cache else "não"])


# ------------------------------------------------------------ equipe
def criar_llm(modelo: str, max_tokens: int):
    from crewai import LLM
    extra = {}
    if CFG["LLM_BASE_URL"]:
        extra["base_url"] = CFG["LLM_BASE_URL"]  # ex.: gateway local compatível com OpenAI
    if CFG["LLM_API_KEY"]:
        extra["api_key"] = CFG["LLM_API_KEY"]
    return LLM(model=modelo, temperature=0.2, max_tokens=max_tokens, **extra)


def rodar(tema: str, contexto: str) -> dict:
    from crewai import Agent, Crew, Process, Task

    forte = criar_llm(CFG["MODELO_TUTOR"], int(CFG["MAX_TOKENS_TUTOR"]))
    barato = criar_llm(CFG["MODELO_BARATO"], int(CFG["MAX_TOKENS_BARATO"]))
    comum = dict(allow_delegation=False, max_iter=2, memory=False, verbose=False, respect_context_window=True)

    tutor = Agent(role="Tutor", goal="Ensinar o tema com precisão e clareza",
                  backstory="Professor de fisiologia felina e comportamento. " + REGRAS, llm=forte, **comum)
    examinador = Agent(role="Examinador", goal="Criar flashcards fiéis à explicação",
                       backstory="Faz perguntas curtas de revisão ativa. " + REGRAS, llm=barato, **comum)
    revisor = Agent(role="Revisor de rastreabilidade", goal="Achar afirmações sem fonte",
                    backstory="Confere cada frase contra os cartões. " + REGRAS, llm=barato, **comum)

    t_explicar = Task(
        description=f"Tema: {tema}\n\nCARTÕES DO ACERVO:\n{contexto}\n\n"
                    "Explique o tema em até 250 palavras (nível acadêmico) e depois em até 100 palavras "
                    "para um leigo. Termine com 'O que ainda falta ler:' listando códigos relevantes.",
        expected_output="Markdown com as seções: Explicação acadêmica · Versão simples · O que ainda falta ler",
        agent=tutor,
    )
    t_cards = Task(
        description="A partir SÓ da explicação anterior, crie 5 flashcards de revisão ativa.",
        expected_output="JSON com a lista 'cards' (pergunta, resposta, fonte)",
        agent=examinador, context=[t_explicar], output_pydantic=Baralho,
    )
    t_revisar = Task(
        description=f"CARTÕES:\n{contexto}\n\nListe, em tópicos curtos, cada frase da explicação que não "
                    "se apoia nos cartões ou que cita código errado. Se estiver tudo certo, diga 'Sem problemas'.",
        expected_output="Lista curta em Markdown",
        agent=revisor, context=[t_explicar],
    )

    crew = Crew(agents=[tutor, examinador, revisor], tasks=[t_explicar, t_cards, t_revisar],
                process=Process.sequential, cache=True, memory=False)
    crew.kickoff()
    m = crew.usage_metrics
    return {
        "explicacao": t_explicar.output.raw,
        "cards": [c.model_dump() for c in t_cards.output.pydantic.cards] if t_cards.output.pydantic else [],
        "revisao": t_revisar.output.raw,
        "uso": {"prompt_tokens": m.prompt_tokens, "completion_tokens": m.completion_tokens, "total_tokens": m.total_tokens},
    }


# ------------------------------------------------------------ principal
def main() -> None:
    ap = argparse.ArgumentParser(description="Equipe de estudo CrewAI — Síndrome de Pandora")
    ap.add_argument("tema")
    ap.add_argument("--codigos", default="", help="códigos do inventário separados por vírgula (ex.: 50,51)")
    ap.add_argument("--fichamento", help="caminho de um fichamento .md para incluir (resumido)")
    ap.add_argument("--simular", action="store_true", help="mostra o contexto e a estimativa de tokens, sem chamar o modelo")
    ap.add_argument("--sem-cache", action="store_true")
    a = ap.parse_args()

    codigos = [c.strip() for c in a.codigos.split(",") if c.strip()]
    contexto, usados = montar_contexto(a.tema, codigos, a.fichamento)
    if not usados and not a.fichamento:
        sys.exit("Nenhuma fonte do inventário casou com o tema. Use --codigos ou outras palavras.")

    estimativa = len(contexto) // 4  # ~4 caracteres por token
    print(f"Fontes usadas: {', '.join(usados) or '—'} · contexto ≈ {estimativa} tokens")
    if a.simular:
        print("\n" + contexto)
        print(f"\nEstimativa da execução completa: ≈ {estimativa * 2 + 900} tokens de entrada "
              f"(o contexto vai para Tutor e Revisor) + até {int(CFG['MAX_TOKENS_TUTOR']) + 2 * int(CFG['MAX_TOKENS_BARATO'])} de saída.")
        return

    chave = hashlib.sha256(json.dumps([a.tema, contexto, CFG["MODELO_TUTOR"], CFG["MODELO_BARATO"]]).encode()).hexdigest()[:16]
    arq_cache = CACHE / f"{chave}.json"
    do_cache = arq_cache.exists() and not a.sem_cache
    if do_cache:
        res = json.loads(arq_cache.read_text(encoding="utf-8"))
        res["uso"] = {}
        print("(resposta do cache — 0 tokens)")
    else:
        res = rodar(a.tema, contexto)
        CACHE.mkdir(exist_ok=True)
        arq_cache.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")

    SAIDAS.mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", sem_acento(a.tema)).strip("-")[:50]
    saida = SAIDAS / f"{datetime.now():%Y-%m-%d}_{slug}.md"
    cards_md = "\n".join(f"- **{c['pergunta']}** — {c['resposta']} {c['fonte']}" for c in res["cards"])
    saida.write_text(
        f"# {a.tema}\n\nFontes do acervo usadas: {', '.join(usados)}\n\n{res['explicacao']}\n\n"
        f"## Flashcards\n{cards_md}\n\n## Revisão de rastreabilidade\n{res['revisao']}\n\n"
        "> Texto gerado por IA a partir dos cartões do inventário. Confira no PDF antes de usar na tese.\n",
        encoding="utf-8",
    )
    gravar_flashcards(a.tema, res["cards"])
    registrar_uso(a.tema, res["uso"], do_cache)
    print(f"Gravado: {saida.relative_to(AQUI)} · {len(res['cards'])} flashcards · tokens: {res['uso'].get('total_tokens', 0)}")


if __name__ == "__main__":
    main()
