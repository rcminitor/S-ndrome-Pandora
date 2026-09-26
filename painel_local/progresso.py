"""
Progresso automático — números da semana sem digitar nada
=========================================================

Junta, por semana (segunda a domingo), o que já acontece no painel e no cofre:

  artigosLidos / paginasLidas  ← seus "Eu li" (páginas = tamanho do PDF)
  fichamentos                  ← Fichamentos\\ do cofre (campo data_do_fichamento)
  pagTese / pagArtigo          ← palavras escritas nas seções de Notas\\Tese
                                  (seção cujo nome começa com "Artigo" conta para a
                                  qualificação; as demais, para a tese).
                                  1 página = PALAVRAS_POR_PAGINA (padrão 300).
  leiturasIA, revisoes, acerto, conversas ← leituras da IA, cartões respondidos,
                                  debates com o orientador

As palavras são fotografadas a cada salvamento e ao ligar o painel
(Leitura\\progresso_escrita.json), então o que você escrever direto no Obsidian
também conta. O site recebe só números (dados_progresso.js). Horas de estudo e
tarefas do IoT continuam manuais no Registro Semanal do site.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path


def segunda(d: date) -> date:
    return d - timedelta(days=d.weekday())


def contar_palavras(texto: str) -> int:
    texto = re.sub(r"^---\n.*?\n---\n", "", texto, count=1, flags=re.S)       # frontmatter
    texto = re.sub(r"<!--.*?-->", " ", texto, flags=re.S)                     # comentários
    texto = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", texto)             # wikilinks
    texto = re.sub(r"[#*_>`|\[\]()-]", " ", texto)
    return len(re.findall(r"\w+", texto))


class Progresso:
    def __init__(self, biblioteca: Path, tese: Path, cofre, registro, revisao, raiz_site: Path, cfg: dict):
        self.arq = biblioteca / "progresso_escrita.json"
        self.tese, self.cofre, self.reg, self.rev = tese, cofre, registro, revisao
        self.site_js = raiz_site / "dados_progresso.js"
        self.ppp = int(cfg.get("PALAVRAS_POR_PAGINA") or 300)

    # ------------------------------------------------------------ escrita
    def _secoes(self) -> dict[str, int]:
        return {p.stem: contar_palavras(p.read_text(encoding="utf-8")) for p in sorted(self.tese.glob("*.md"))}

    def fotografar(self) -> dict[str, int]:
        """Guarda a contagem de palavras de hoje (a última do dia vale)."""
        atual = self._secoes()
        hist = json.loads(self.arq.read_text(encoding="utf-8")) if self.arq.exists() else {}
        hoje = date.today().isoformat()
        if hist.get(hoje) != atual:
            hist[hoje] = atual
            self.arq.parent.mkdir(parents=True, exist_ok=True)
            self.arq.write_text(json.dumps(hist, ensure_ascii=False, indent=1), encoding="utf-8")
        return atual

    @staticmethod
    def _tipo(secao: str) -> str:
        return "artigo" if secao.lower().startswith("artigo") else "tese"

    def _palavras_por_semana(self) -> dict[str, dict[str, int]]:
        """{segunda-feira: {'tese': palavras no fim da semana, 'artigo': ...}}"""
        hist = json.loads(self.arq.read_text(encoding="utf-8")) if self.arq.exists() else {}
        fim_semana: dict[str, dict] = {}
        for dia in sorted(hist):
            fim_semana[segunda(date.fromisoformat(dia)).isoformat()] = hist[dia]   # o último dia da semana prevalece
        saida = {}
        for sem, secoes in fim_semana.items():
            t = {"tese": 0, "artigo": 0}
            for nome, n in secoes.items():
                t[self._tipo(nome)] += n
            saida[sem] = t
        return saida

    # ------------------------------------------------------------ semanas
    def semanas(self) -> list[dict]:
        S: dict[str, dict] = {}

        def sem(iso: str) -> dict:
            k = segunda(date.fromisoformat(iso[:10])).isoformat()
            return S.setdefault(k, {"semana": k, "artigosLidos": 0, "paginasLidas": 0, "fichamentos": 0,
                                    "pagTese": 0.0, "pagArtigo": 0.0, "leiturasIA": 0, "revisoes": 0,
                                    "acertos": 0, "conversas": 0})

        for e in self.reg.carregar().values():
            h = e.get("humano")
            if h:
                s = sem(h["data"])
                s["artigosLidos"] += 1
                s["paginasLidas"] += int(h.get("paginas") or 0)
            for ex in e.get("ia", []):
                if ex.get("status") == "ok" and ex.get("fim"):
                    sem(ex["fim"])["leiturasIA"] += 1

        if self.cofre and (self.cofre.raiz / "Fichamentos").is_dir():
            for f in (self.cofre.raiz / "Fichamentos").glob("*— Fichamento —*.md"):
                m = re.search(r"^data_do_fichamento:\s*\"?(\d{4}-\d{2}-\d{2})", f.read_text(encoding="utf-8"), re.M)
                if m:
                    sem(m.group(1))["fichamentos"] += 1

        for c in self.rev.carregar():
            for h in c["historico"]:
                s = sem(h["data"])
                s["revisoes"] += 1
                s["acertos"] += bool(h["lembrou"])

        debates = self.tese / "Debates"
        if debates.is_dir():
            for f in debates.glob("*.md"):
                for d, m, a in re.findall(r"^## (\d{2})/(\d{2})/(\d{4})", f.read_text(encoding="utf-8"), re.M):
                    sem(f"{a}-{m}-{d}")["conversas"] += 1

        anterior = {"tese": 0, "artigo": 0}
        for k, t in sorted(self._palavras_por_semana().items()):
            s = sem(k)
            s["pagTese"] = round(max(0, t["tese"] - anterior["tese"]) / self.ppp, 1)
            s["pagArtigo"] = round(max(0, t["artigo"] - anterior["artigo"]) / self.ppp, 1)
            anterior = t

        saida = []
        for k in sorted(S):
            s = S[k]
            s["acerto"] = round(100 * s["acertos"] / s["revisoes"]) if s["revisoes"] else None
            del s["acertos"]
            if any(v for kk, v in s.items() if kk not in ("semana", "acerto")):
                saida.append(s)
        return saida

    # ------------------------------------------------------------ site
    def escrever_site(self) -> None:
        atual = self.fotografar()
        tot = {"tese": 0, "artigo": 0}
        for nome, n in atual.items():
            tot[self._tipo(nome)] += n
        dados = {
            "atualizado": datetime.now().isoformat(timespec="minutes"),
            "palavras_por_pagina": self.ppp,
            "escrita_atual": {"tese_palavras": tot["tese"], "artigo_palavras": tot["artigo"],
                              "tese_paginas": round(tot["tese"] / self.ppp, 1),
                              "artigo_paginas": round(tot["artigo"] / self.ppp, 1),
                              "secoes": len(atual)},
            "semanas": self.semanas(),
        }
        self.site_js.write_text("// Gerado pelo Painel de Estudo (painel_local/progresso.py). Só números.\n"
                                "window.DADOS_PROGRESSO = " + json.dumps(dados, ensure_ascii=False, indent=1) + ";\n",
                                encoding="utf-8")
