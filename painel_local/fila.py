"""
Fila de leitura inteligente — qual artigo ler agora, e por quê
==============================================================

Ordena as fontes do cofre que você ainda NÃO leu (status abaixo de "leitura
concluida") somando sinais que já existem no cofre e no painel. Cada ponto vem
com o motivo escrito, para você conferir e discordar — a ordem final é sua.

  Sinal                                                     Pontos
  ─────────────────────────────────────────────────────────────────
  fase "Ler primeiro" (frontmatter da nota da fonte)         +40
  outra fase (exceto consulta/descartar/opcional)            +15
  citada no texto da tese (Notas\\Tese) sem ter sido lida     +35
  leitura já começada ("leitura em andamento")               +20
  citada nos trechos RELEVANTES de artigos lidos pela IA     +12 por artigo  (teto 48)
  citada só na lista de referências desses artigos           +5 por artigo   (teto 48, somado ao de cima)
  mencionada em fichamentos / outras notas de Fontes\\        +6 por nota     (teto 30)
  núcleo menos coberto (proporção lida no núcleo)            até +15
  a IA já leu (relatório pronto para acompanhar a leitura)   +8

• Citações cruzadas vêm dos .leitura.json que o agente leitor grava junto de cada
  PDF (campo "acervo" de cada referência; se faltar, casa por DOI ou título).
• Menções no cofre: [[nome da nota]] ou #código em Fichamentos\\ e Fontes\\ (a nota
  da própria fonte não conta).
• Fonte sem PDF encontrado vai para "Buscar o PDF" (mesma ordem), porque não dá
  para ler o que não se tem.

Saídas: aba "Próxima leitura" no painel e um bloco no topo de
Notas\\Fila de leitura.md (trecho <!-- painel:sugestao --> — o resto da nota fica
intacto). Nada vai para o site.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

from cofre import ORDEM, TRAVA, _norm, nivel

PESOS = {"ler_primeiro": 40, "outra_fase": 15, "na_tese": 35, "andamento": 20,
         "citada_relevante": 12, "citada_lista": 5, "teto_citacoes": 48,
         "mencao": 6, "teto_mencoes": 30, "nucleo": 15, "ia_leu": 8}
FASES_BAIXAS = ("consulta", "descart", "opcional", "se sobrar", "complementar")
LIDO = ORDEM.index("leitura concluida")


def _sem_blocos_painel(t: str) -> str:
    return re.sub(r"<!-- painel:[^>]*inicio.*?<!-- painel:[^>]*fim -->", " ", t, flags=re.S)


def _mencoes(texto: str, fonte: dict) -> bool:
    if f"[[{fonte['stem']}" in texto:
        return True
    cod = fonte["codigo"]
    return bool(cod) and re.search(rf"(?<![\w/])#{re.escape(cod)}(?![\w/])", texto) is not None


class Fila:
    def __init__(self, cofre, registro, tese: Path, pastas: dict[str, Path], casar=None):
        """pastas: {"ler": PARA_LER, "acervo": ACERVO, "lido": LIDO} — onde procurar PDFs e leituras.
        casar(texto_ref, doi) → fonte do cofre ou None (contexto_cofre.no_acervo)."""
        self.cofre, self.reg, self.tese, self.pastas, self.casar = cofre, registro, tese, pastas, casar

    # ------------------------------------------------------------ sinais
    def _pdfs(self) -> dict[str, str]:
        """nome do pdf (minúsculo) → id do painel. "Para ler" tem preferência sobre o acervo."""
        ids: dict[str, str] = {}
        for rotulo in ("ler", "acervo"):
            raiz = self.pastas.get(rotulo)
            if raiz and raiz.exists():
                for p in raiz.rglob("*.pdf"):
                    ids.setdefault(p.name.lower(), f"{rotulo}:{p.relative_to(raiz).as_posix()}")
        return ids

    def _citacoes(self, por_codigo: dict[str, dict]) -> dict[str, dict[str, set]]:
        """código → {"relevante": {artigos que citam nos trechos relevantes}, "lista": {só na lista}}."""
        cit: dict[str, dict[str, set]] = defaultdict(lambda: {"relevante": set(), "lista": set()})
        for rotulo in ("ler", "lido", "acervo"):
            raiz = self.pastas.get(rotulo)
            if not raiz or not raiz.exists():
                continue
            for js in raiz.rglob("*.leitura.json"):
                artigo = js.name[: -len(".leitura.json")]
                if " - citados" in str(js.parent):          # leituras de citados de citados não contam duas vezes
                    continue
                try:
                    d = json.loads(js.read_text(encoding="utf-8"))
                except Exception:
                    continue
                proprio = (self.cofre.fonte_do_pdf(artigo + ".pdf") or {}).get("codigo")
                for r in d.get("referencias", []):
                    m = re.match(r"#(\S+)", r.get("acervo") or "")
                    cod = m.group(1) if m else None
                    if not cod and self.casar:
                        try:
                            f = self.casar(r.get("texto", ""), r.get("doi", ""))
                            cod = f["codigo"] if f else None
                        except Exception:
                            cod = None
                    if not cod or cod == proprio or cod not in por_codigo:
                        continue
                    cit[cod]["relevante" if r.get("citada_em") else "lista"].add(artigo)
        return cit

    def _mencoes_no_cofre(self, fontes: list[dict]) -> dict[str, set]:
        """código → nomes das notas (fichamentos e outras fontes) que o mencionam."""
        men: dict[str, set] = defaultdict(set)
        raiz = self.cofre.raiz
        arquivos = list((raiz / "Fichamentos").glob("*.md")) if (raiz / "Fichamentos").is_dir() else []
        arquivos += [f["nota"] for f in fontes]
        for arq in arquivos:
            try:
                t = _sem_blocos_painel(arq.read_text(encoding="utf-8"))
            except Exception:
                continue
            t = re.sub(r"^---\n.*?\n---\n", "", t, count=1, flags=re.S)
            for f in fontes:
                if arq == f["nota"] or arq.stem.startswith(f"{f['codigo']} ") or arq.stem == f["codigo"]:
                    continue                                   # a nota/fichamento da própria fonte
                if _mencoes(t, f):
                    men[f["codigo"]].add(arq.stem)
        return men

    uso_no_texto = None          # opcional: função → {código: [seções]} (rastreio.py, que entende citação ABNT)

    def _na_tese(self, fontes: list[dict]) -> dict[str, list[str]]:
        if self.uso_no_texto:
            try:
                return self.uso_no_texto()
            except Exception:
                pass
        saida: dict[str, list[str]] = defaultdict(list)
        if not self.tese or not self.tese.is_dir():
            return saida
        for arq in sorted(self.tese.glob("*.md")):
            t = _sem_blocos_painel(arq.read_text(encoding="utf-8"))
            for f in fontes:
                if _mencoes(t, f):
                    saida[f["codigo"]].append(arq.stem)
        return saida

    # ------------------------------------------------------------ ordem
    def calcular(self) -> dict:
        if not self.cofre or not self.cofre.ativo:
            return {"ativo": False, "sugeridas": [], "sem_pdf": [], "nucleos": []}
        fontes = [f for f in self.cofre.todas() if f["codigo"]]
        por_codigo = {f["codigo"]: f for f in fontes}
        pdfs = self._pdfs()
        cit = self._citacoes(por_codigo)
        men = self._mencoes_no_cofre(fontes)
        tese = self._na_tese(fontes)
        reg = self.reg.carregar() if self.reg else {}

        # cobertura por núcleo: fração já lida
        tot, lidas = defaultdict(int), defaultdict(int)
        for f in fontes:
            tot[f["nucleo"]] += 1
            lidas[f["nucleo"]] += nivel(f["status"]) >= LIDO
        frac = {n: lidas[n] / tot[n] for n in tot}
        nucleos = [{"nucleo": n or "(sem núcleo)", "total": tot[n], "lidas": lidas[n]} for n in sorted(tot)]

        itens = []
        for f in fontes:
            nv = nivel(f["status"])
            if nv >= LIDO:
                continue
            pontos, motivos = 0, []
            fase = _norm(f["fase"])
            if "primeiro" in fase:
                pontos += PESOS["ler_primeiro"]; motivos.append("fase “Ler primeiro”")
            elif fase and not any(b in fase for b in FASES_BAIXAS):
                pontos += PESOS["outra_fase"]; motivos.append(f"fase “{f['fase']}”")
            if f["codigo"] in tese:
                pontos += PESOS["na_tese"]
                motivos.append("já aparece no seu texto (" + ", ".join(tese[f["codigo"]][:2]) + ") sem ter sido lida")
            if nv == ORDEM.index("leitura em andamento"):
                pontos += PESOS["andamento"]; motivos.append("leitura já começada")
            c = cit.get(f["codigo"])
            if c:
                rel, lst = c["relevante"], c["lista"] - c["relevante"]
                p = min(PESOS["teto_citacoes"], PESOS["citada_relevante"] * len(rel) + PESOS["citada_lista"] * len(lst))
                pontos += p
                if rel:
                    motivos.append(f"citada em trechos relevantes de {len(rel)} artigo(s) já lido(s) pela IA ("
                                   + "; ".join(sorted(rel)[:2])[:120] + ")")
                if lst:
                    motivos.append(f"nas referências de {'mais ' if rel else ''}{len(lst)} artigo(s) lido(s) pela IA")
            m = men.get(f["codigo"])
            if m:
                pontos += min(PESOS["teto_mencoes"], PESOS["mencao"] * len(m))
                motivos.append(f"mencionada em {len(m)} nota(s) do cofre (" + "; ".join(sorted(m)[:2])[:100] + ")")
            if len(frac) > 1:
                bonus = round(PESOS["nucleo"] * (1 - frac.get(f["nucleo"], 0)))
                if bonus:
                    pontos += bonus
                    motivos.append(f"núcleo com {round(100 * frac.get(f['nucleo'], 0))}% lido")
            stem_pdf = Path(f["pdf"]).stem if f["pdf"] else ""
            if stem_pdf and any(x.get("status") == "ok" for x in (reg.get(stem_pdf) or {}).get("ia", [])):
                pontos += PESOS["ia_leu"]; motivos.append("a IA já leu (relatório pronto)")
            pid = pdfs.get(f["pdf"].lower()) if f["pdf"] else None
            itens.append({"codigo": f["codigo"], "stem": f["stem"], "titulo": f["titulo"], "ano": f.get("ano", ""),
                          "nucleo": f["nucleo"], "fase": f["fase"], "status": f["status"],
                          "pontos": pontos, "motivos": motivos, "id": pid,
                          "onde": "Para ler" if pid and pid.startswith("ler:") else "acervo" if pid else ""})

        itens.sort(key=lambda i: (-i["pontos"], i["codigo"]))
        return {"ativo": True, "atualizado": date.today().isoformat(), "nucleos": nucleos,
                "sugeridas": [i for i in itens if i["id"]], "sem_pdf": [i for i in itens if not i["id"]]}

    # ------------------------------------------------------------ Obsidian
    def escrever_obsidian(self, dados: dict | None = None, n: int = 10, n_buscar: int = 5) -> bool:
        if not self.cofre or not self.cofre.ativo or not self.cofre.fila.exists():
            return False
        d = dados or self.calcular()

        def linha(i, pos=None):
            ini = f"{pos}. " if pos else "- "
            ano = f" ({i['ano']})" if i["ano"] else ""
            return (f"{ini}[[{i['stem']}|#{i['codigo']}]] {i['titulo'][:90]}{ano} — **{i['pontos']} pts** · "
                    + ("; ".join(i["motivos"]) or "sem sinais além do status"))

        partes = ["## 🧭 Próximas leituras sugeridas pelo painel",
                  f"*Calculado em {date.today():%d/%m/%Y} a partir do cofre (fase, citações cruzadas, menções, "
                  "texto da tese, núcleo menos coberto). É sugestão — a ordem é sua. Pesos em painel_local/fila.py.*", ""]
        partes += [linha(i, k) for k, i in enumerate(d["sugeridas"][:n], 1)] or ["- (nenhuma fonte com PDF pendente)"]
        if d["sem_pdf"]:
            partes += ["", "**Buscar o PDF primeiro** (sem arquivo no acervo):"]
            partes += [linha(i) for i in d["sem_pdf"][:n_buscar]]
        conteudo = "\n".join(partes)

        def mudar(texto: str) -> str:
            m = re.search(r"^## ", texto, re.M)
            antes = None
            if m and "painel:sugestao" not in texto:
                antes = texto[m.start():].split("\n", 1)[0]
            return self.cofre._bloco(texto, "sugestao", conteudo, antes_de=antes)

        with TRAVA:
            return self.cofre._alterar(self.cofre.fila, mudar)
