"""
Leitor de artigos — Síndrome de Pandora (Python + CrewAI)
=========================================================

Para cada PDF:
  1. Extrai o texto por parágrafo, com a página, e converte citações
     sobrescritas em marcadores [5,6] (sem IA, 0 token).
  2. Separa os trechos relevantes à tese: filtro por palavras-chave (0 token)
     + triagem opcional por IA (modelo barato, só IDs de volta).
  3. Traduz INTEGRALMENTE cada trecho relevante (sem resumir nem cortar).
     Confere se a tradução não ficou curta demais e marca possível omissão.
     Os trechos não traduzidos continuam no relatório, em inglês — nada some.
  4. Mostra quem o autor citou em cada trecho e monta a lista de referências.
  5. Localiza cada referência citada (DOI → Crossref/OpenAlex) e baixa o PDF
     SOMENTE quando existe versão legal de acesso aberto (OpenAlex/Unpaywall).
     Sem acesso aberto, indica o caminho: Portal CAPES / biblioteca da UFC.
  6. Repete o passo 4–5 nos artigos baixados até a --profundidade pedida
     (árvore de citações: artigo → quem ele citou → quem esse citou).

Uso (dentro de agentes_crewai):
    python leitor_artigos.py "C:\\...\\artigo.pdf"
    python leitor_artigos.py artigo.pdf --profundidade 2
    python leitor_artigos.py artigo.pdf --baixar todos      (todas as refs, não só as dos trechos relevantes)
    python leitor_artigos.py artigo.pdf --sem-traducao       (só citações e downloads, 0 token)
    python leitor_artigos.py artigo.pdf --simular            (mostra trechos e custo estimado, sem IA e sem rede)

Configuração: .env desta pasta (ver .env.exemplo).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

import pymupdf
from dotenv import dotenv_values
from pydantic import BaseModel

import ia

AQUI = Path(__file__).resolve().parent
CACHE = AQUI / ".cache"
SAIDAS = AQUI / "saidas"

CFG = {
    "MODELO_TRADUTOR": "anthropic/claude-haiku-4-5-20251001",
    "MODELO_BARATO": "anthropic/claude-haiku-4-5-20251001",
    "LLM_BASE_URL": "",
    "LLM_API_KEY": "",
    "RESERVA_API_KEY": "",
    "EMAIL_CONTATO": "",           # pedido educado das APIs Crossref/OpenAlex/Unpaywall
    "PASTA_ESTUDO": "",             # onde salvar os PDFs baixados (padrão: agentes_crewai/biblioteca)
    "MAX_DOWNLOADS": "15",
    "LOTE_CHARS": "3500",
    "MAX_TOKENS_TRADUTOR": "2500",
    **{k: v for k, v in dotenv_values(AQUI / ".env").items() if v is not None},
}

# Termos da tese (inglês, pois os artigos estão em inglês). Edite à vontade.
PALAVRAS_CHAVE = [
    "pandora", "idiopathic cystitis", "interstitial cystitis", "fic", "flutd", "lower urinary",
    "cystitis", "bladder", "urothel", "stress", "stressor", "cortisol", "acth", "adrenal",
    "hypothalam", "pituitar", "hpa", "sympathetic", "catecholamin", "norepinephrine",
    "neuroendocrin", "glucocorticoid", "multisystem", "comorbid", "environment", "enrichment",
    "indoor", "behaviour", "behavior", "welfare", "owner", "litter", "multi-cat", "conflict",
    "anxiety", "fear", "sickness behavio", "memo", "sensor", "monitor", "wearable", "accelerom",
    "iot", "internet of things", "machine learning", "artificial intelligence", "deep learning",
]


# ============================================================ 1. extração
@dataclass
class Trecho:
    id: int
    pagina: int
    texto: str
    pontos: int = 0
    citacoes: list[str] = field(default_factory=list)   # rótulos: "5", "Casey 2009"
    traducao: str = ""
    alerta: str = ""


def sem_acento(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


RE_TITULO_REFS = re.compile(r"^\s*(references|reference list|literature cited|bibliography|referências|referencias)\s*$", re.I)


def extrair(pdf: Path) -> tuple[list[Trecho], str]:
    """Devolve (parágrafos do corpo, texto bruto da seção de referências)."""
    doc = pymupdf.open(pdf)
    trechos: list[Trecho] = []
    refs: list[str] = []
    na_refs = False
    for num_pag, pag in enumerate(doc, start=1):
        for bloco in pag.get_text("dict")["blocks"]:
            if bloco.get("type") != 0:
                continue
            partes = []
            for linha in bloco["lines"]:
                for s in linha["spans"]:
                    t = unicodedata.normalize("NFKC", s["text"])        # ﬀ → ff, ﬁ → fi
                    t = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ue000-\uf8ff]", "⟨?⟩", t)   # símbolo ilegível (≤, ±, µ…)
                    sobrescrito = s["flags"] & 1 and re.fullmatch(r"\s*\d+(?:[,–\-]\s?\d+)*\s*", t)
                    partes.append(f"[{t.strip()}]" if sobrescrito else t)
                partes.append("\n")
            bruto_bloco = "".join(partes)
            texto = re.sub(r"-\n(?=[a-z])", "", bruto_bloco)            # junta palavras hifenizadas
            texto = re.sub(r"\s*\n\s*", " ", texto).strip()
            primeira, _, resto = bruto_bloco.strip().partition("\n")
            if not na_refs and RE_TITULO_REFS.match(primeira):          # título sozinho ou colado à 1ª referência
                na_refs = True
                if resto.strip():
                    refs.append(resto + "\n")
                continue
            if na_refs:
                refs.append("".join(p for p in partes))
            elif len(texto) >= 80:
                trechos.append(Trecho(id=len(trechos) + 1, pagina=num_pag, texto=texto))
    return trechos, "".join(refs)


# ============================================================ 2. referências
@dataclass
class Referencia:
    rotulo: str                 # "5" (numerada) ou "Casey 2009" (autor-ano)
    texto: str
    doi: str = ""
    doi_origem: str = ""        # "no PDF" | "busca Crossref — conferir"
    titulo: str = ""
    ano: str = ""
    acesso_aberto: bool | None = None
    url_pdf: str = ""
    arquivo: str = ""
    citada_em: list[int] = field(default_factory=list)
    filhos: list["Referencia"] = field(default_factory=list)


RE_DOI = re.compile(r"10\.\d{4,9}/[^\s\"<>]+", re.I)


def limpar_doi(d: str) -> str:
    return d.rstrip(".,;)]").lower()


def separar_referencias(bruto: str) -> list[Referencia]:
    bruto = re.sub(r"-\n(?=[a-z])", "", bruto)
    linhas = [l.strip() for l in bruto.splitlines() if l.strip()]
    juntas: list[str] = []                               # "95" numa linha + texto na seguinte → "95 texto"
    for l in linhas:
        if juntas and re.fullmatch(r"\[?\d{1,3}[\].]?", juntas[-1]) and not re.fullmatch(r"\[?\d{1,3}[\].]?", l):
            juntas[-1] += " " + l
        else:
            juntas.append(l)
    linhas = juntas
    inicios = {int(m.group(1)) for l in linhas if (m := re.match(r"^\[?(\d{1,3})[\].]?\s+[A-Z]", l))}
    numeradas = 3 if {1, 2, 3} <= inicios else 0
    itens: list[Referencia] = []
    if numeradas >= 3:                                   # estilo numerado
        atual = None
        for l in linhas:
            m = re.match(r"^\[?(\d{1,3})[\].]?\s+(.*)", l)
            if m and (atual is None or int(m.group(1)) == int(atual.rotulo) + 1):
                atual = Referencia(rotulo=m.group(1), texto=m.group(2))
                itens.append(atual)
            elif atual:
                atual.texto += " " + l
    else:                                                # estilo autor-ano
        inicio = re.compile(r"^[A-Z][A-Za-zÀ-ÿ'’\-]+(?: [A-Z][A-Za-zÀ-ÿ'’\-]+)?,? (?:[A-Z]\.|[A-Z]{1,3}\b)")
        atual = None
        for l in linhas:
            instituicao = re.match(r"^[A-Z][A-Za-z&.\- ]{1,60}(?:,| \()\s?(?:\(?(?:19|20)\d{2}|n\.d\.)", l)
            if (inicio.match(l) or instituicao) and (atual is None or re.search(r"[.)]$|\d$", atual.texto)):
                atual = Referencia(rotulo="", texto=l)
                itens.append(atual)
            elif atual:
                atual.texto += " " + l
        for r in itens:
            sob = re.match(r"([A-Za-zÀ-ÿ'’\-]+)", r.texto)
            ano = re.search(r"\b(19|20)\d{2}[a-z]?\b", r.texto)
            r.rotulo = f"{sob.group(1) if sob else '?'} {ano.group(0) if ano else 's.d.'}"
    for r in itens:
        r.texto = re.sub(r"\s+", " ", r.texto).strip()
        colado = re.sub(r"(https?://)\s+", r"\1", r.texto)
        colado = re.sub(r"(10\.\d{4,9}/\S*?[./\-])\s+(?=[\w(])", r"\1", colado)   # DOI quebrado na linha
        m = RE_DOI.search(colado)
        if m:
            r.doi, r.doi_origem = limpar_doi(m.group(0)), "no PDF"
        a = re.search(r"\b(19|20)\d{2}\b", r.texto)
        r.ano = a.group(0) if a else ""
    return itens


def achar_ref(rotulo: str, refs: list[Referencia]) -> Referencia | None:
    alvo = sem_acento(rotulo)
    for r in refs:
        if sem_acento(r.rotulo) == alvo:
            return r
    partes = rotulo.rsplit(" ", 1)
    if len(partes) == 2 and not rotulo.isdigit():             # sobrenome no início da referência + mesmo ano
        sob, ano = sem_acento(partes[0]), partes[1]
        for r in refs:
            if sob in sem_acento(r.texto[:80]) and re.search(r"\b" + re.escape(ano) + r"\b", r.texto):
                return r
    return None


def ligar_citacoes(trechos: list[Trecho], refs: list[Referencia]) -> None:
    numeradas = bool(refs) and refs[0].rotulo.isdigit()
    for t in trechos:
        rotulos: list[str] = []
        if numeradas:
            for grupo in re.findall(r"\[(\d+(?:\s?[,–\-]\s?\d+)*)\]", t.texto):
                for parte in re.split(r",\s?", grupo):
                    if re.search(r"[–\-]", parte):
                        a, b = map(int, re.split(r"\s?[–\-]\s?", parte))
                        rotulos += [str(n) for n in range(a, b + 1)] if 0 <= b - a < 30 else []
                    else:
                        rotulos.append(parte)
        else:
            pedacos = []
            for dentro in re.findall(r"\(([^()]*\d{4}[a-z]?[^()]*)\)", t.texto):
                pedacos += re.split(r";", dentro)
            pedacos += [f"{m.group(1)} {m.group(2)}" for m in
                        re.finditer(r"([A-Z][A-Za-zÀ-ÿ'’\-]+)(?: et al\.| and [A-Z][A-Za-zÀ-ÿ'’\-]+)? \(((?:19|20)\d{2}[a-z]?)\)", t.texto)]
            for c in pedacos:
                ano = re.findall(r"\b((?:19|20)\d{2}[a-z]?)\b", c)
                sob = re.search(r"(?:^|\s)((?:van |de |von |da )?[A-Z][A-Za-zÀ-ÿ'’\-]+)", c)
                if ano and sob:
                    for a in ano:                                  # "Casey, 2007, 2009" → dois rótulos
                        rotulos.append(f"{sob.group(1).split()[-1]} {a}")
        vistos: list[str] = []
        for r in rotulos:
            if r in vistos:
                continue
            vistos.append(r)
            alvo = achar_ref(r, refs)
            if alvo and t.id not in alvo.citada_em:
                alvo.citada_em.append(t.id)
        t.citacoes = vistos


# ============================================================ 3. relevância e tradução
def pontuar(trechos: list[Trecho]) -> None:
    for t in trechos:
        baixo = sem_acento(t.texto)
        t.pontos = sum(1 for k in PALAVRAS_CHAVE if re.search(r"\b" + re.escape(k), baixo))


class Selecao(BaseModel):
    ids: list[int]


class ItemTraduzido(BaseModel):
    id: int
    traducao: str


class Lote(BaseModel):
    itens: list[ItemTraduzido]


def _llm(papel: str, max_tokens: int):
    return ia.criar_llm(CFG, papel, max_tokens, temperature=0)


def _cache(chave: str, gerar):
    CACHE.mkdir(exist_ok=True)
    arq = CACHE / (hashlib.sha256(chave.encode()).hexdigest()[:20] + ".json")
    if arq.exists():
        return json.loads(arq.read_text(encoding="utf-8")), 0
    valor, tokens = gerar()
    arq.write_text(json.dumps(valor, ensure_ascii=False), encoding="utf-8")
    return valor, tokens


TRIADOR = ("Você é pesquisador da Síndrome de Pandora em felinos: cistite idiopática, estresse, eixo HHA, "
           "adrenais, ambiente, comportamento, enriquecimento, sensores/IoT e IA.")
TRADUTOR = ("Você é tradutor técnico de Medicina Veterinária. Traduz para o português do Brasil de forma INTEGRAL "
            "e fiel: não resume, não explica, não corta frases, mantém números, unidades, valores de p, siglas na "
            "primeira ocorrência e marcadores de citação como [5,6] ou (Casey et al., 2009) exatamente onde estão.")


def triagem_ia(cands: list[Trecho]) -> tuple[set[int], int]:
    lista = "\n".join(f"{t.id}: {t.texto[:350]}" for t in cands)
    pedido = (f"Trechos (id: início do texto):\n{lista}\n\nQuais ids têm conteúdo científico útil à tese "
              "(resultados, métodos, conceitos, discussão)? Exclua agradecimentos, financiamento, conflito de "
              'interesse e cabeçalhos. Formato: {"ids": [1, 2, 3]}')

    def gerar():
        obj, tok = ia.pedir_json(CFG, "barato", 1200, TRIADOR, pedido, Selecao)
        return obj.ids, tok

    ids, tokens = _cache("triagem|" + CFG["MODELO_BARATO"] + lista, lambda: ia.com_reserva(CFG, gerar, "triagem"))
    return set(ids), tokens


def traduzir(sel: list[Trecho]) -> int:
    teto, lotes, atual = int(CFG["LOTE_CHARS"]), [], []
    for t in sel:
        if atual and sum(len(x.texto) for x in atual) + len(t.texto) > teto:
            lotes.append(atual); atual = []
        atual.append(t)
    if atual:
        lotes.append(atual)

    total = 0
    for i, lote in enumerate(lotes, 1):
        corpo = "\n\n".join(f"<t id={t.id}>\n{t.texto}\n</t>" for t in lote)
        pedido = (f"Traduza cada trecho abaixo, inteiro, para o português do Brasil.\n\n{corpo}\n\n"
                  'Formato: {"itens": [{"id": 1, "traducao": "..."}]} com um item por trecho.')

        def gerar():
            obj, tok = ia.pedir_json(CFG, "tradutor", int(CFG["MAX_TOKENS_TRADUTOR"]), TRADUTOR, pedido, Lote)
            return {str(x.id): x.traducao for x in obj.itens}, tok

        try:
            mapa, tok = _cache("trad|" + CFG["MODELO_TRADUTOR"] + corpo, lambda: ia.com_reserva(CFG, gerar, f"tradução, lote {i}"))
        except Exception as e:
            print(f"  ⚠ lote {i}/{len(lotes)} não traduzido ({type(e).__name__}: {str(e)[:160]})")
            mapa, tok = {}, 0
        total += tok
        for t in lote:
            t.traducao = mapa.get(str(t.id), "")
            if not t.traducao:
                t.alerta = "TRADUÇÃO NÃO RETORNADA — use o original"
            elif len(t.traducao) < 0.75 * len(t.texto):
                t.alerta = "tradução bem mais curta que o original: possível omissão, conferir"
            elif t.citacoes and not all(c.split()[0] in t.traducao for c in t.citacoes if c[:1].isalpha()):
                t.alerta = "algum marcador de citação sumiu na tradução, conferir"
        print(f"  lote {i}/{len(lotes)} {'traduzido' if mapa else 'sem tradução'}")
    return total


# ============================================================ 4. localizar e baixar
class Rede:
    def __init__(self):
        import requests
        self.s = requests.Session()
        mail = CFG["EMAIL_CONTATO"]
        self.s.headers["User-Agent"] = f"leitor-pandora/1.0 (mailto:{mail})" if mail else "leitor-pandora/1.0"
        self.baixados = 0

    def _json(self, url: str, **params):
        if CFG["EMAIL_CONTATO"]:
            params.setdefault("mailto", CFG["EMAIL_CONTATO"])
        try:
            r = self.s.get(url, params=params, timeout=25)
            time.sleep(0.2)                                    # educação com as APIs
            return r.json() if r.ok else None
        except Exception:
            return None

    def achar_doi(self, ref: Referencia) -> None:
        if ref.doi:
            return
        j = self._json("https://api.crossref.org/works", **{"query.bibliographic": ref.texto[:300], "rows": 1})
        it = (j or {}).get("message", {}).get("items", [])
        if it and it[0].get("score", 0) >= 60:
            ano = str((it[0].get("issued", {}).get("date-parts") or [[None]])[0][0] or "")
            if not ref.ano or ano == ref.ano:
                ref.doi, ref.doi_origem = it[0]["DOI"].lower(), "busca Crossref — conferir"

    def detalhar(self, ref: Referencia) -> None:
        if not ref.doi:
            return
        j = self._json(f"https://api.openalex.org/works/doi:{ref.doi}")
        if j:
            ref.titulo = j.get("title") or ""
            ref.ano = str(j.get("publication_year") or ref.ano)
            oa = j.get("open_access") or {}
            ref.acesso_aberto = bool(oa.get("is_oa"))
            ref.url_pdf = (j.get("best_oa_location") or {}).get("pdf_url") or ""
        if not ref.url_pdf and CFG["EMAIL_CONTATO"]:
            u = self._json(f"https://api.unpaywall.org/v2/{ref.doi}", email=CFG["EMAIL_CONTATO"])
            loc = (u or {}).get("best_oa_location") or {}
            if loc.get("url_for_pdf"):
                ref.url_pdf, ref.acesso_aberto = loc["url_for_pdf"], True

    def baixar(self, ref: Referencia, pasta: Path) -> None:
        if not ref.url_pdf or self.baixados >= int(CFG["MAX_DOWNLOADS"]):
            return
        autor = re.sub(r"\W+", "", sem_acento(ref.rotulo.split()[0] if not ref.rotulo.isdigit() else ref.texto.split()[0]))
        nome = f"{ref.ano or 'sd'}_{autor[:20]}_{re.sub(r'[^a-z0-9]+', '-', sem_acento(ref.titulo or ref.texto))[:50].strip('-')}.pdf"
        destino = pasta / nome
        if destino.exists():
            ref.arquivo = str(destino); return
        try:
            r = self.s.get(ref.url_pdf, timeout=60)
            if r.ok and r.content[:4] == b"%PDF":
                pasta.mkdir(parents=True, exist_ok=True)
                destino.write_bytes(r.content)
                ref.arquivo = str(destino)
                self.baixados += 1
        except Exception:
            pass


def resolver(refs: list[Referencia], rede: Rede, pasta: Path, prof_restante: int, somente_citadas: bool) -> None:
    alvo = [r for r in refs if r.citada_em or not somente_citadas]
    for i, r in enumerate(alvo, 1):
        rede.achar_doi(r)
        rede.detalhar(r)
        rede.baixar(r, pasta)
        print(f"  ref {i}/{len(alvo)} {r.rotulo}: {'baixada' if r.arquivo else ('aberta' if r.acesso_aberto else 'sem acesso aberto' if r.doi else 'sem DOI')}")
        if r.arquivo and prof_restante > 0:                # desce na árvore: quem esse artigo citou
            _, bruto = extrair(Path(r.arquivo))
            r.filhos = separar_referencias(bruto)
            resolver(r.filhos, rede, pasta / "citados_de_citados", prof_restante - 1, somente_citadas=False)


# ============================================================ 5. relatório
def md_arvore(refs: list[Referencia], nivel: int = 0) -> str:
    out = []
    for r in refs:
        if nivel and not (r.arquivo or r.acesso_aberto):
            continue                                           # nos níveis de baixo, só o que tem acesso
        estado = ("📄 baixado" if r.arquivo else "🔓 aberto (não baixado)" if r.acesso_aberto
                  else "🔒 sem acesso aberto — Portal CAPES / biblioteca" if r.doi else "❓ DOI não localizado")
        doi = f" · DOI {r.doi}" + (f" ({r.doi_origem})" if r.doi_origem != "no PDF" else "") if r.doi else ""
        out.append(f"{'  ' * nivel}- **[{r.rotulo}]** {r.texto[:220]}{doi} · {estado}")
        if r.filhos:
            out.append(md_arvore(r.filhos, nivel + 1))
    return "\n".join(x for x in out if x)


def relatorio(pdf: Path, trechos: list[Trecho], sel_ids: set[int], refs: list[Referencia], tokens: int, prof: int,
              pasta_saida: Path | None = None) -> Path:
    destino = pasta_saida or SAIDAS
    destino.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", sem_acento(pdf.stem))[:60].strip("-")
    L = [f"# Leitura — {pdf.name}", "",
         f"Gerado em {datetime.now():%d/%m/%Y %H:%M} · {len(trechos)} parágrafos · {len(sel_ids)} relevantes · "
         f"{sum(1 for t in trechos if t.traducao)} traduzidos · "
         f"{len(refs)} referências · tokens: {tokens}", "",
         "> Tradução automática para estudo. Página = página do PDF. Antes de citar na tese, confira no original.",
         "> ⟨?⟩ = símbolo que o PDF não deixa ler (em geral <, ≤, ± ou µ): confira no PDF.", "",
         "## Trechos relevantes (original + tradução integral)", ""]
    for t in trechos:
        if t.id not in sel_ids:
            continue
        L += [f"### Trecho {t.id} — p. {t.pagina}", "", "> " + t.texto, "", t.traducao or "_(sem tradução)_", ""]
        if t.alerta:
            L += [f"⚠️ {t.alerta}", ""]
        if t.citacoes:
            L.append("**O autor cita aqui:**")
            for c in t.citacoes:
                r = achar_ref(c, refs)
                L.append(f"- [{c}] " + (f"{r.texto[:200]}" + (" · 📄 baixado" if r.arquivo else "") if r else "referência não localizada na lista — conferir"))
            L.append("")
    L += ["## Árvore de citações", "",
          f"Nível 0 = referências do artigo; abaixo, quem cada artigo baixado citou (profundidade {prof}).", "",
          md_arvore(refs) or "_Nenhuma referência extraída._", "",
          "## Trechos não traduzidos (mantidos no original — nada foi retirado)", ""]
    for t in trechos:
        if t.id not in sel_ids:
            L += [f"<details><summary>Trecho {t.id} — p. {t.pagina}</summary>", "", t.texto, "", "</details>", ""]
    base = f"{pdf.stem}.leitura" if pasta_saida else f"leitura_{slug}"
    saida = destino / f"{base}.md"
    saida.write_text("\n".join(L), encoding="utf-8")
    (destino / f"{base}.json").write_text(json.dumps(
        {"trechos": [asdict(t) for t in trechos], "relevantes": sorted(sel_ids), "referencias": [asdict(r) for r in refs]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    return saida


# ============================================================ principal
def main() -> None:
    ap = argparse.ArgumentParser(description="Lê, traduz o relevante e segue as citações de um artigo")
    ap.add_argument("pdf")
    ap.add_argument("--profundidade", type=int, default=1, help="0 = só o artigo; 1 = + quem ele citou; 2 = + quem esses citaram")
    ap.add_argument("--baixar", choices=["relevantes", "todos", "nenhum"], default="relevantes")
    ap.add_argument("--sem-traducao", action="store_true")
    ap.add_argument("--sem-triagem-ia", action="store_true", help="usa só palavras-chave (0 token)")
    ap.add_argument("--simular", action="store_true")
    ap.add_argument("--destino", help="pasta onde salvar os artigos citados baixados (substitui PASTA_ESTUDO)")
    ap.add_argument("--relatorio-dir", help="pasta do relatório; grava <nome do pdf>.leitura.md ao lado dele")
    a = ap.parse_args()

    pdf = Path(a.pdf)
    if not pdf.exists():
        sys.exit(f"Arquivo não encontrado: {pdf}")
    trechos, bruto = extrair(pdf)
    if not trechos:
        sys.exit("O PDF não tem camada de texto (é imagem). Faça OCR antes — não vou traduzir por suposição.")
    refs = separar_referencias(bruto)
    ligar_citacoes(trechos, refs)
    pontuar(trechos)
    cands = [t for t in trechos if t.pontos > 0]
    print(f"{pdf.name}: {len(trechos)} parágrafos, {len(cands)} com termos da tese, {len(refs)} referências, "
          f"{sum(1 for r in refs if r.citada_em)} citadas nesses parágrafos")

    tokens = 0
    if a.simular:
        chars = sum(len(t.texto) for t in cands)
        print(f"Estimativa: triagem ≈ {len(cands) * 100} tokens · tradução ≈ {chars // 4 * 2 + 400 * (chars // int(CFG['LOTE_CHARS']) + 1)} tokens")
        for t in cands[:8]:
            print(f"  [{t.id}] p.{t.pagina} ({t.pontos} termos) cita {t.citacoes[:6]}: {t.texto[:110]}…")
        for r in refs[:5]:
            print(f"  ref [{r.rotulo}] doi={r.doi or '—'} :: {r.texto[:90]}")
        return

    sel_ids = {t.id for t in cands}
    if not a.sem_traducao and not a.sem_triagem_ia and cands:
        try:
            ids, tok = triagem_ia(cands)
            tokens += tok
            sel_ids = ids & sel_ids or sel_ids
        except Exception as e:
            print(f"  ⚠ triagem por IA falhou ({type(e).__name__}); seguindo só com as palavras-chave da tese")
    if not a.sem_traducao:
        tokens += traduzir([t for t in trechos if t.id in sel_ids])

    if a.baixar != "nenhum" and a.profundidade > 0:
        if a.destino:
            pasta = Path(a.destino)
        else:
            pasta = Path(CFG["PASTA_ESTUDO"]) if CFG["PASTA_ESTUDO"] else AQUI / "biblioteca"
            pasta = pasta / re.sub(r"[^a-z0-9]+", "-", sem_acento(pdf.stem))[:50].strip("-")
        for r in refs:                                          # considera só citações nos trechos escolhidos
            r.citada_em = [i for i in r.citada_em if i in sel_ids]
        resolver(refs, Rede(), pasta, a.profundidade - 1, somente_citadas=a.baixar == "relevantes")
        print(f"PDFs de acesso aberto em: {pasta}")

    saida = relatorio(pdf, trechos, sel_ids, refs, tokens, a.profundidade,
                      Path(a.relatorio_dir) if a.relatorio_dir else None)
    print(f"Relatório: {saida} · tokens usados: {tokens}" + (" · ⚠ parte feita com a RESERVA PAGA" if ia.usando_reserva() else ""))


if __name__ == "__main__":
    main()
