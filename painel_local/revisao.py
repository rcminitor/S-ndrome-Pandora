"""
Revisão espaçada — medir o que você LEMBRA, não só o que leu
============================================================

• Cartões gerados de uma leitura da IA (trechos relevantes, com página) ou de um
  fichamento seu do cofre (conferido no PDF). A IA só pode usar o texto recebido.
• Agenda fixa: acertou → sobe um degrau (1, 3, 7, 21, 60 dias); errou → volta ao
  início e reaparece amanhã. "Firme" = acertou no degrau de 7 dias ou acima.
• Tudo fica no cofre (Leitura\\revisao_cartoes.json, privado). Uma nota do Obsidian
  (Notas\\Revisão de cartões.md) mostra o resumo e o que revisar hoje. O site recebe
  só números (dados_revisao.js).
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

from pydantic import BaseModel

INTERVALOS = [1, 3, 7, 21, 60]          # dias até a próxima revisão, por degrau
FIRME = 3                               # degrau a partir do qual o cartão conta como firme
TRAVA = threading.Lock()


class Cartao(BaseModel):
    pergunta: str
    resposta: str
    pagina: str = ""


class Lote(BaseModel):
    cartoes: list[Cartao]


GERADOR = ("Você cria cartões de revisão ativa para um doutorando em Medicina Veterinária (Síndrome de Pandora "
           "em felinos). Regras: use SOMENTE o texto recebido; não acrescente nada de fora; cada cartão testa UMA "
           "ideia importante (conceito, achado, método, número que importa); pergunta direta; resposta curta (até "
           "2 frases), fiel ao texto; informe a página do trecho usado. Escreva em português.")


class Revisao:
    def __init__(self, biblioteca: Path, cofre=None, raiz_site: Path | None = None):
        self.arq = biblioteca / "revisao_cartoes.json"
        self.cofre = cofre if cofre is not None and getattr(cofre, "ativo", False) else None
        self.site_js = raiz_site / "dados_revisao.js" if raiz_site else None

    # ------------------------------------------------------------ base
    def carregar(self) -> list[dict]:
        if self.arq.exists():
            try:
                return json.loads(self.arq.read_text(encoding="utf-8"))
            except Exception:
                self.arq.replace(self.arq.with_suffix(".json.bak"))
        return []

    def _salvar(self, cartoes: list[dict]) -> None:
        self.arq.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.arq.with_suffix(".tmp")
        tmp.write_text(json.dumps(cartoes, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.arq)

    # ------------------------------------------------------------ gerar
    @staticmethod
    def texto_da_leitura(json_leitura: Path, teto: int = 6000) -> str:
        """Trechos relevantes com página; usa a tradução quando existe."""
        d = json.loads(json_leitura.read_text(encoding="utf-8"))
        rel = set(d.get("relevantes", []))
        partes, total = [], 0
        for t in d.get("trechos", []):
            if t["id"] not in rel:
                continue
            bloco = f"[p. {t['pagina']}] {t.get('traducao') or t['texto']}"
            if total + len(bloco) > teto:
                break
            partes.append(bloco)
            total += len(bloco)
        return "\n\n".join(partes)

    def gerar(self, cfg: dict, ia, artigo: str, codigo: str, texto: str, origem: str, n: int = 8) -> tuple[int, int]:
        """Pede os cartões à IA e guarda os novos. Devolve (quantos novos, tokens)."""
        if not texto.strip():
            raise ValueError("não há texto para gerar cartões (a leitura não tem trechos relevantes?)")
        pedido = (f"TEXTO ({origem}):\n{texto}\n\nCrie até {n} cartões. "
                  'Formato: {"cartoes": [{"pergunta": "...", "resposta": "...", "pagina": "12"}]}')
        lote, tokens = ia.com_reserva(cfg, lambda: ia.pedir_json(cfg, "barato", 2500, GERADOR, pedido, Lote), "cartões")
        with TRAVA:
            cartoes = self.carregar()
            existentes = {c["id"] for c in cartoes}
            novos = 0
            for c in lote.cartoes[:n]:
                cid = hashlib.sha1(f"{artigo}|{c.pergunta.strip().lower()}".encode()).hexdigest()[:12]
                if cid in existentes or not c.pergunta.strip() or not c.resposta.strip():
                    continue
                cartoes.append({"id": cid, "artigo": artigo, "codigo": codigo, "pergunta": " ".join(c.pergunta.split()),
                                "resposta": " ".join(c.resposta.split()), "pagina": str(c.pagina or "").strip(),
                                "origem": origem, "criado": date.today().isoformat(), "degrau": -1,
                                "proxima": date.today().isoformat(), "historico": []})
                existentes.add(cid)
                novos += 1
            self._salvar(cartoes)
        return novos, tokens

    # ------------------------------------------------------------ revisar
    def fila_hoje(self, artigo: str | None = None) -> list[dict]:
        hoje = date.today().isoformat()
        cs = [c for c in self.carregar() if c["proxima"] <= hoje and (not artigo or c["artigo"] == artigo)]
        return sorted(cs, key=lambda c: (c["degrau"] >= 0, c["proxima"], c["degrau"]))   # erros e atrasados antes

    def responder(self, cid: str, lembrou: bool) -> dict:
        with TRAVA:
            cartoes = self.carregar()
            c = next((x for x in cartoes if x["id"] == cid), None)
            if not c:
                raise KeyError(cid)
            c["degrau"] = min(c["degrau"] + 1, len(INTERVALOS) - 1) if lembrou else 0
            dias = INTERVALOS[c["degrau"]] if lembrou else 1
            c["proxima"] = (date.today() + timedelta(days=dias)).isoformat()
            c["historico"].append({"data": datetime.now().isoformat(timespec="minutes"), "lembrou": lembrou})
            self._salvar(cartoes)
            return c

    # ------------------------------------------------------------ resumo
    @staticmethod
    def estado(c: dict) -> str:
        return "novo" if not c["historico"] else "firme" if c["degrau"] >= FIRME else "aprendendo"

    def resumo(self) -> dict:
        cs = self.carregar()
        hoje = date.today().isoformat()
        por_art: dict[str, dict] = {}
        for c in cs:
            a = por_art.setdefault(c["artigo"], {"artigo": c["artigo"], "codigo": c["codigo"], "total": 0,
                                                 "firmes": 0, "hoje": 0, "acertos": 0, "respostas": 0})
            a["total"] += 1
            a["firmes"] += self.estado(c) == "firme"
            a["hoje"] += c["proxima"] <= hoje
            a["acertos"] += sum(h["lembrou"] for h in c["historico"])
            a["respostas"] += len(c["historico"])
        resp = [h for c in cs for h in c["historico"]]
        semana = (date.today() - timedelta(days=7)).isoformat()
        resp7 = [h for h in resp if h["data"][:10] >= semana]
        return {
            "total": len(cs),
            "hoje": sum(c["proxima"] <= hoje for c in cs),
            "novos": sum(self.estado(c) == "novo" for c in cs),
            "aprendendo": sum(self.estado(c) == "aprendendo" for c in cs),
            "firmes": sum(self.estado(c) == "firme" for c in cs),
            "acerto_7d": round(100 * sum(h["lembrou"] for h in resp7) / len(resp7)) if resp7 else None,
            "revisoes_7d": len(resp7),
            "por_artigo": sorted(por_art.values(), key=lambda a: -a["total"]),
        }

    # ------------------------------------------------------------ cofre e site
    def escrever_obsidian(self) -> None:
        if not self.cofre:
            return
        r = self.resumo()
        nota = self.cofre.notas / "Revisão de cartões.md"
        if not nota.exists():
            nota.write_text("---\ntags:\n  - moc\n---\n\n# Revisão de cartões\n\n"
                            "Cartões de revisão espaçada gerados no Painel de Estudo (aba **Revisão**). "
                            "Os cartões ficam em `Leitura/revisao_cartoes.json`; esta nota mostra o resumo.\n",
                            encoding="utf-8")
        linhas = [f"*Atualizado em {datetime.now():%d/%m/%Y %H:%M}.*", "",
                  "| | |", "|---|---|",
                  f"| Cartões | {r['total']} |", f"| Para revisar hoje | {r['hoje']} |",
                  f"| Novos · aprendendo · firmes | {r['novos']} · {r['aprendendo']} · {r['firmes']} |",
                  f"| Acerto nos últimos 7 dias | {str(r['acerto_7d']) + '%' if r['acerto_7d'] is not None else '—'} "
                  f"({r['revisoes_7d']} respostas) |", "", "**Por artigo:**"]
        por_stem = {k.rsplit(".", 1)[0]: v for k, v in self.cofre.fontes_por_pdf().items()}
        for a in r["por_artigo"]:
            f = por_stem.get(a["artigo"].lower())
            nome = f"[[{f['stem']}|#{f['codigo']}]] {f['titulo'][:60]}" if f else a["artigo"][:60]
            linhas.append(f"- {nome} — {a['firmes']}/{a['total']} firmes" + (f" · {a['hoje']} para hoje" if a["hoje"] else ""))
        fracos = [c for c in self.carregar() if c["historico"] and not c["historico"][-1]["lembrou"]][:10]
        if fracos:
            linhas += ["", "**Errados na última vez (voltar ao texto):**"]
            linhas += [f"- {' '.join(c['pergunta'].split())} *(p. {c['pagina'] or '?'} — {c['artigo'][:40]})*" for c in fracos]
        self.cofre._alterar(nota, lambda t: self.cofre._bloco(t, "revisao", "\n".join(linhas)))

    def escrever_site(self) -> None:
        if not self.site_js:
            return
        r = self.resumo()
        por_stem = {k.rsplit(".", 1)[0]: v for k, v in self.cofre.fontes_por_pdf().items()} if self.cofre else {}
        publico = {**{k: r[k] for k in ("total", "hoje", "novos", "aprendendo", "firmes", "acerto_7d", "revisoes_7d")},
                   "atualizado": datetime.now().isoformat(timespec="minutes"),
                   "por_artigo": [{"titulo": (por_stem.get(a["artigo"].lower()) or {}).get("titulo") or a["artigo"],
                                   "codigo": a["codigo"], "total": a["total"], "firmes": a["firmes"]}
                                  for a in r["por_artigo"]]}          # perguntas e respostas NÃO vão para o site
        self.site_js.write_text("// Gerado pelo Painel de Estudo (painel_local/revisao.py). Só números.\n"
                                "window.DADOS_REVISAO = " + json.dumps(publico, ensure_ascii=False, indent=1) + ";\n",
                                encoding="utf-8")
