"""
Matriz de síntese e rastreabilidade da escrita
==============================================

Duas coisas, feitas SEM IA (só leitura do que está no cofre — nada é deduzido):

1. MATRIZ DE SÍNTESE  (Notas\\Matriz de síntese.md + Leitura\\matriz_de_sintese.csv)
   Uma linha por fichamento de Fichamentos\\, com as colunas da skill do acervo:
   Fonte · Tema · Objetivo · Método · Principais resultados · Limitações ·
   Contribuição para a tese · Núcleo · Seção sugerida · No texto.
   Cada célula é copiada (resumida) da seção correspondente do fichamento. Seção
   que não existe fica "— não consta no fichamento", nunca preenchida por dedução.

2. RASTREABILIDADE DA ESCRITA  (Notas\\Rastreabilidade da escrita.md + painel)
   Para cada parágrafo das seções de Notas\\Tese, acha as fontes citadas —
   ABNT "(STELLA; LORD; BUFFINGTON, 2011)", narrativa "Stella et al. (2011)",
   #código ou [[nota da fonte]] — e aponta:
     ⛔ citação que não casa com nenhuma fonte do cofre (fora do inventário)
     ⚠️ fonte citada que você ainda não leu (status abaixo de "leitura concluida")
     ⚠️ fonte cuja referência ainda não foi conferida (procedência ≠ ✔️)
     ⚠️ citação indireta (apud) — a regra do cofre pede a fonte primária
     ⚠️ parágrafo com dado (%, n =, p <, número de animais/semanas…) sem citação
     ❓ citação ambígua (mais de uma fonte com o mesmo sobrenome e ano)
   E, no conjunto: fontes fichadas que ainda não aparecem no texto, e fontes
   fichadas já citadas (candidatas a status "utilizado no texto" — o painel NÃO
   muda o status sozinho: a correspondência sobrenome+ano pode errar).

O casamento de citação usa o PRIMEIRO sobrenome citado + o ano contra o primeiro
autor da referência ABNT da nota da fonte (## Referência (ABNT)).
"""
from __future__ import annotations

import csv
import re
import unicodedata
from datetime import date
from pathlib import Path

from cofre import ORDEM, TRAVA, nivel

LIDO = ORDEM.index("leitura concluida")
FICHADO = ORDEM.index("fichamento concluido")
VAZIO = "— não consta no fichamento"
NAO_SOBRENOME = {"et", "al", "apud", "cf", "ver", "and", "p", "pp", "in", "e", "op", "cit", "idem", "ibidem"}

# coluna da matriz → trechos de título de seção do fichamento que a alimentam (sem acento, minúsculo)
COLUNAS = [
    ("Tema", ("tema", "conceitos importantes")),
    ("Objetivo", ("objetivo",)),
    ("Método", ("metodolog", "tipo de estudo", "populacao", "amostra")),
    ("Principais resultados", ("resultado",)),
    ("Limitações", ("limitac",)),
    ("Contribuição para a tese", ("contribui", "relacao com a sindrome", "onde entra")),
    ("Seção sugerida", ("secao sugerida",)),
]

RE_DADO = re.compile(
    r"\d+(?:[.,]\d+)?\s*%|\bp\s*[<>=≤]\s*0|\bn\s*=\s*\d|\bIC\s*\d|\b\d+(?:[.,]\d+)?\s*(?:gatos|animais|felinos|semanas|"
    r"dias|meses|anos|vezes)\b|\b(?:estudos|pesquisas|autores|trabalhos)\s+(?:mostram|demonstram|indicam|apontam|"
    r"revelam|sugerem)", re.I)


def _n(t: str) -> str:
    t = unicodedata.normalize("NFD", (t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _celula(t: str, teto: int = 240) -> str:
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    t = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", t)
    t = re.sub(r"^\s*(?:>\s*)?(?:\[![^\]]*\]\s*)?[-*]?\s*", "", t, flags=re.M)
    t = " ".join(t.replace("|", "/").split())
    return (t[: teto - 1] + "…") if len(t) > teto else t


def _secoes_md(texto: str) -> list[tuple[str, str]]:
    """[(título normalizado, corpo)] para cada cabeçalho # … ###### do markdown."""
    texto = re.sub(r"^---\n.*?\n---\n", "", texto, count=1, flags=re.S)
    partes = re.split(r"^(#{1,6})\s+(.*)$", texto, flags=re.M)
    saida = []
    for i in range(1, len(partes) - 2, 3):
        saida.append((_n(partes[i + 1]), partes[i + 2].strip()))
    return saida


def _frontmatter(texto: str, campo: str) -> str:
    m = re.match(r"^---\n(.*?)\n---\n", texto, re.S)
    if not m:
        return ""
    c = re.search(rf'^{campo}:\s*"?(.*?)"?\s*$', m.group(1), re.M)
    return c.group(1).strip() if c else ""


class Rastreio:
    def __init__(self, cofre, tese: Path, biblioteca: Path):
        self.cofre, self.tese = cofre, tese
        self.csv = biblioteca / "matriz_de_sintese.csv"

    @property
    def ativo(self) -> bool:
        return bool(self.cofre and self.cofre.ativo)

    # ------------------------------------------------------------ fontes com autores
    def _fontes(self) -> list[dict]:
        saida = []
        for f in self.cofre.todas():
            if not f["codigo"]:
                continue
            try:
                t = f["nota"].read_text(encoding="utf-8")
            except Exception:
                continue
            abnt = re.search(r"## Referência \(ABNT\)\s*\n>\s*(.+)", t)
            ref = abnt.group(1).strip() if abnt else ""
            autores = ref.split(". ", 1)[0] if ref else ""
            # "STELLA, J. L.; LORD, L. K.; BUFFINGTON, C. A. T" → ["stella", "lord", "buffington"]
            sobrenomes = [_n(a.split(",")[0]).strip() for a in autores.split(";") if a.strip()]
            sobrenomes = [s.split()[-1] if " " in s else s for s in sobrenomes if s]
            proc = ""
            for linha in t.split("\n"):
                if "roced" in linha or "A CONFERIR" in linha:
                    proc = ("✔️" if "✔" in linha else "🟡" if "🟡" in linha else "⚠️" if ("⚠" in linha or "A CONFERIR" in linha)
                            else "❌" if "❌" in linha else proc)
                    if proc:
                        break
            ano = re.sub(r"\D", "", f.get("ano", ""))[:4]
            saida.append({**f, "sobrenomes": sobrenomes, "ano4": ano, "procedencia": proc, "abnt": ref})
        return saida

    # ------------------------------------------------------------ citações num parágrafo
    @staticmethod
    def _citacoes(par: str) -> list[dict]:
        """[{'autores': [...], 'ano': '2011', 'bruto': '…', 'apud': bool}] + #código/[[nota]]."""
        cits = []
        for m in re.finditer(r"\(([^()]*?\b(?:1[89]|20)\d{2}[a-z]?[^()]*)\)", par):   # parentética ABNT
            dentro, inicio = m.group(1), 0
            apud = "apud" in _n(dentro)
            for a in re.finditer(r"\b((?:1[89]|20)\d{2})[a-z]?\b", dentro):
                seg = dentro[inicio:a.start()]
                inicio = a.end()
                nomes = [w for w in re.findall(r"[A-Za-zÀ-ÿ'-]{2,}", seg) if _n(w) not in NAO_SOBRENOME]
                if nomes:
                    cits.append({"autores": [_n(w) for w in nomes], "ano": a.group(1), "bruto": m.group(0), "apud": apud})
        for m in re.finditer(r"([A-ZÀ-Ý][\wÀ-ÿ'-]+(?:\s*(?:,|e|and|&|et al\.?)\s*[A-ZÀ-Ý]?[\wÀ-ÿ'.-]*)*)\s*\(((?:1[89]|20)\d{2})[a-z]?"
                             r"(?:,\s*p\.[^)]*)?\)", par):                                     # narrativa
            nomes = [w for w in re.findall(r"[A-Za-zÀ-ÿ'-]{2,}", m.group(1)) if _n(w) not in NAO_SOBRENOME]
            if nomes and not re.match(r"(?:Segundo|Conforme|Para|De acordo|Como|Em|No|Na)$", nomes[0]):
                cits.append({"autores": [_n(w) for w in nomes], "ano": m.group(2), "bruto": m.group(0),
                             "apud": "apud" in _n(par[m.start():m.end() + 40])})
        return cits

    def _casar(self, cit: dict, fontes: list[dict]) -> list[dict]:
        primeiro = cit["autores"][0]
        return [f for f in fontes if f["ano4"] == cit["ano"] and f["sobrenomes"] and f["sobrenomes"][0] == primeiro]

    def conferir_texto(self, texto: str, fontes: list[dict] | None = None) -> list[dict]:
        """Um item por parágrafo: fontes citadas e alertas."""
        fontes = fontes if fontes is not None else self._fontes()
        texto = re.sub(r"^---\n.*?\n---\n", "", texto, count=1, flags=re.S)
        texto = re.sub(r"<!--.*?-->", " ", texto, flags=re.S)
        saida = []
        for k, par in enumerate(p.strip() for p in re.split(r"\n\s*\n", texto)):
            if not par or par.startswith("#") or par == "---":
                continue
            achadas, alertas = {}, []
            for f in fontes:                                         # #código e [[nota]]
                if f"[[{f['stem']}" in par or re.search(rf"(?<![\w/])#{re.escape(f['codigo'])}(?![\w/])", par):
                    achadas[f["codigo"]] = f
            cits = self._citacoes(par)
            for c in cits:
                cand = self._casar(c, fontes)
                if not cand:
                    alertas.append(("⛔", f"{c['bruto']} não corresponde a nenhuma fonte do cofre (fora do inventário ou ano/autor diferente)"))
                elif len(cand) > 1:
                    alertas.append(("❓", f"{c['bruto']} é ambígua: " + ", ".join("#" + f["codigo"] for f in cand)))
                else:
                    achadas[cand[0]["codigo"]] = cand[0]
                if c["apud"]:
                    alertas.append(("⚠️", f"citação indireta em {c['bruto']} — consulte a fonte primária antes de manter"))
            for f in achadas.values():
                if nivel(f["status"]) < LIDO:
                    alertas.append(("⚠️", f"#{f['codigo']} citada mas ainda não lida (status: {f['status'] or '—'})"))
                if f["procedencia"] and f["procedencia"] != "✔️":
                    alertas.append(("⚠️", f"#{f['codigo']}: referência ainda não conferida ({f['procedencia']})"))
            if not achadas and not cits and RE_DADO.search(par):
                alertas.append(("⚠️", "tem dado ou afirmação sobre estudos, mas nenhuma citação"))
            saida.append({"n": len(saida) + 1, "inicio": _celula(par, 90), "fontes": sorted(achadas),
                          "citacoes": len(cits) + len(achadas), "alertas": [f"{s} {t}" for s, t in dict.fromkeys(alertas)]})
        return saida

    def conferir_secao(self, nome: str) -> dict:
        arq = self.tese / f"{nome}.md"
        if not self.ativo or not arq.exists():
            return {"ativo": self.ativo, "paragrafos": []}
        pars = self.conferir_texto(arq.read_text(encoding="utf-8"))
        return {"ativo": True, "paragrafos": pars,
                "com_fonte": sum(1 for p in pars if p["fontes"]), "alertas": sum(len(p["alertas"]) for p in pars)}

    @staticmethod
    def alertas_em_texto(res: dict, teto: int = 1500) -> str:
        """Resumo curto para o orientador."""
        linhas = [f"§{p['n']} “{p['inicio'][:50]}”: " + "; ".join(p["alertas"]) for p in res.get("paragrafos", []) if p["alertas"]]
        return "\n".join(linhas)[:teto]

    # ------------------------------------------------------------ matriz
    @staticmethod
    def autor_data(f: dict) -> str:
        """Chamada ABNT: até 3 autores por extenso, 4 ou mais com et al."""
        s = [x.upper() for x in f.get("sobrenomes") or []] or ["?"]
        nomes = "; ".join(s) if len(s) <= 3 else f"{s[0]} et al."
        return f"{nomes}, {f.get('ano4') or '?'}"

    def matriz(self, fontes: list[dict] | None = None, no_texto: dict | None = None) -> list[dict]:
        fontes = fontes if fontes is not None else self._fontes()
        por_codigo = {f["codigo"]: f for f in fontes}
        no_texto = no_texto or {}
        pasta = self.cofre.raiz / "Fichamentos"
        linhas = []
        for arq in sorted(pasta.glob("*— Fichamento —*.md")) if pasta.is_dir() else []:
            t = arq.read_text(encoding="utf-8")
            cod = arq.stem.split(" ", 1)[0]
            f = por_codigo.get(cod, {})
            secoes = _secoes_md(t)
            linha = {"Código": cod, "Fonte": self.autor_data(f) if f else arq.stem,
                     "stem": f.get("stem", ""), "fichamento": arq.stem}
            for col, chaves in COLUNAS:
                corpo = " ".join(c for tit, c in secoes if any(k in tit for k in chaves) and c)
                if col == "Tema" and not corpo:
                    corpo = _frontmatter(t, "tema") or f.get("tema", "")
                if col == "Limitações":                      # as identificadas por você vêm marcadas
                    corpo = " ".join((("[interpretação] " if "identific" in tit or "voce" in tit else "") + c)
                                     for tit, c in secoes if any(k in tit for k in chaves) and c)
                linha[col] = _celula(corpo) if corpo else VAZIO
            linha["Núcleo"] = f.get("nucleo") or VAZIO
            linha["No texto"] = ", ".join(no_texto.get(cod, [])) or "ainda não"
            linhas.append(linha)
        return linhas

    # ------------------------------------------------------------ notas do Obsidian
    def _uso_no_texto(self, fontes: list[dict]) -> tuple[dict, dict]:
        """(código → seções que o citam, seção → resultado da conferência)."""
        uso, por_secao = {}, {}
        if self.tese and self.tese.is_dir():
            for arq in sorted(self.tese.glob("*.md")):
                pars = self.conferir_texto(arq.read_text(encoding="utf-8"), fontes)
                por_secao[arq.stem] = pars
                for p in pars:
                    for c in p["fontes"]:
                        uso.setdefault(c, [])
                        if arq.stem not in uso[c]:
                            uso[c].append(arq.stem)
        return uso, por_secao

    def _escrever(self, arq: Path, titulo: str, conteudo: str) -> bool:
        if not arq.exists():
            arq.parent.mkdir(parents=True, exist_ok=True)
            arq.write_text(f"# {titulo}\n\n", encoding="utf-8")
        with TRAVA:
            return self.cofre._alterar(arq, lambda t: self.cofre._bloco(t, "gerado", conteudo))

    def escrever_obsidian(self) -> dict:
        if not self.ativo:
            return {}
        fontes = self._fontes()
        uso, por_secao = self._uso_no_texto(fontes)
        linhas = self.matriz(fontes, uso)
        cols = ["Fonte"] + [c for c, _ in COLUNAS] + ["Núcleo", "No texto"]
        hoje = f"{date.today():%d/%m/%Y}"

        # --- matriz
        tab = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        for l in linhas:
            fonte = f"[[{l['fichamento']}\\|#{l['Código']}]] {l['Fonte']}"
            tab.append("| " + " | ".join([fonte] + [l[c] for c in cols[1:]]) + " |")
        matriz_md = (f"*Gerada em {hoje} pelo painel a partir de Fichamentos\\ — {len(linhas)} fichamento(s). Cada célula é "
                     f"um resumo da seção correspondente do fichamento; “{VAZIO}” quer dizer que a seção não existe lá "
                     "(nada foi deduzido). O agrupamento por núcleo é proposto, não declarado pelos autores. "
                     "Para editar, mude o fichamento — esta tabela é refeita.*\n\n" + "\n".join(tab)
                     + "\n\nEspelho para Excel: `Leitura\\matriz_de_sintese.csv`.")
        self._escrever(self.cofre.notas / "Matriz de síntese.md", "Matriz de síntese", matriz_md)
        try:
            self.csv.parent.mkdir(parents=True, exist_ok=True)
            with self.csv.open("w", encoding="utf-8-sig", newline="") as fh:        # utf-8-sig: Excel abre com acento
                w = csv.writer(fh, delimiter=";")
                w.writerow(["Código"] + cols)
                for l in linhas:
                    w.writerow([l["Código"]] + [l[c] for c in cols])
        except PermissionError:
            pass                                                                     # CSV aberto no Excel

        # --- rastreabilidade
        todos = [p for ps in por_secao.values() for p in ps]
        fichadas = [f for f in fontes if nivel(f["status"]) >= FICHADO]
        nao_usadas = [f for f in fichadas if f["codigo"] not in uso]
        candidatas = [f for f in fichadas if f["codigo"] in uso and nivel(f["status"]) < ORDEM.index("utilizado no texto")]
        R = [f"*Conferido em {hoje} pelo painel, sem IA: casa citações ABNT (primeiro sobrenome + ano), #código e "
             "[[nota]] com as notas de Fontes\\. Pode errar em sobrenomes compostos — confira os ⛔ antes de corrigir.*", "",
             "| | |", "|---|---|",
             f"| Parágrafos | {len(todos)} |",
             f"| Parágrafos com fonte identificada | {sum(1 for p in todos if p['fontes'])} |",
             f"| Alertas | {sum(len(p['alertas']) for p in todos)} |",
             f"| Fontes citadas no texto | {len(uso)} |",
             f"| Fichadas e ainda fora do texto | {len(nao_usadas)} |", ""]
        for sec, pars in por_secao.items():
            com = [p for p in pars if p["alertas"]]
            R.append(f"### [[{sec}]] — {len(pars)} parágrafo(s), {len(com)} com alerta")
            for p in com:
                R.append(f"- §{p['n']} “{p['inicio']}”")
                R += [f"    - {a}" for a in p["alertas"]]
            if not com:
                R.append("- sem alertas ✔")
            R.append("")
        if candidatas:
            R += ["### Fichadas e já citadas no texto", "Podem passar para o status “utilizado no texto” — o painel não muda "
                  "isso sozinho; confira a correspondência e ajuste a nota da fonte:"]
            R += [f"- [[{f['stem']}|#{f['codigo']}]] — em {', '.join(uso[f['codigo']])}" for f in candidatas] + [""]
        if nao_usadas:
            R += ["### Fichadas e ainda fora do texto"]
            R += [f"- [[{f['stem']}|#{f['codigo']}]] {f['titulo'][:80]}" for f in nao_usadas]
        self._escrever(self.cofre.notas / "Rastreabilidade da escrita.md", "Rastreabilidade da escrita", "\n".join(R))
        return {"fichamentos": len(linhas), "paragrafos": len(todos), "citadas": len(uso)}
