"""
O cofre como registro de verdade
================================

O status de cada artigo vale o que está na nota de Fontes\\ do cofre Obsidian.
O painel LÊ o status de lá e, quando algo acontece, ESCREVE lá:

  • IA terminou de ler   → nota da fonte ganha a linha 🤖 com link para o relatório guardado
  • você apertou "Eu li" → nota da fonte: status "leitura concluida" (nunca rebaixa um
                           fichamento), etiqueta status/…, linha 👤 com a sua nota;
                           MOC do núcleo: 📖lido; Fila de leitura: [x] + data;
                           00 Índice do cofre: bloco "Leituras registradas pelo painel"

Cuidados (regras do CLAUDE.md do cofre):
  • só mexe em trechos marcados <!-- painel:... --> ou em linhas específicas (status,
    etiqueta, marca na Fila e no MOC) — o que você escreveu fica intacto;
  • antes da primeira alteração do dia em cada nota, guarda uma cópia em
    Leitura\\_copias_antes_do_painel\\<data>\\;
  • guarda de data de modificação: se a nota mudou enquanto o painel trabalhava
    (você editando no Obsidian, OneDrive sincronizando), relê e tenta de novo.
"""
from __future__ import annotations

import re
import shutil
import threading
import time
import unicodedata
from datetime import date, datetime
from pathlib import Path

TRAVA = threading.Lock()

# ordem de avanço — o painel nunca volta um status para trás
ORDEM = ["ainda nao obtido", "arquivo obtido", "leitura em andamento", "leitura concluida",
         "fichamento incompleto", "fichamento concluido", "utilizado no texto"]


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", (t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn").strip()


def nivel(status: str) -> int:
    s = _norm(status)
    melhor = -1
    for i, nome in enumerate(ORDEM):
        if s.startswith(nome):
            melhor = i
    return melhor


def data_br(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return iso


class Cofre:
    def __init__(self, raiz: Path, pasta_leitura: Path):
        self.raiz = raiz
        self.fontes = raiz / "Fontes"
        self.notas = raiz / "Notas"
        self.indice = raiz / "00 Índice do cofre.md"
        self.fila = self.notas / "Fila de leitura.md"
        self.leitura = pasta_leitura
        self.copias = pasta_leitura / "_copias_antes_do_painel"
        self._cache: tuple[float, dict] | None = None

    @property
    def ativo(self) -> bool:
        return self.fontes.is_dir()

    # ------------------------------------------------------------ leitura das notas
    def _ler_fonte(self, arq: Path) -> dict | None:
        texto = arq.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n", texto, re.S)
        if not m:
            return None
        fm = m.group(1)

        def campo(nome):
            c = re.search(rf'^{nome}:\s*"?(.*?)"?\s*$', fm, re.M)
            return c.group(1) if c else ""

        pdf = re.search(r"\*\*PDF:\*\*\s*\[\[([^\]|#]+\.pdf)", texto, re.I)
        return {"nota": arq, "stem": arq.stem, "codigo": campo("codigo"), "titulo": campo("titulo"),
                "status": campo("status"), "nucleo": campo("nucleo"), "fase": campo("fase"),
                "pdf": Path(pdf.group(1)).name if pdf else ""}

    def todas(self) -> list[dict]:
        """Todas as notas de Fontes\\ (relê só se alguma mudou)."""
        if not self.ativo:
            return []
        arqs = list(self.fontes.glob("*.md"))
        marca = (len(arqs), max((p.stat().st_mtime for p in arqs), default=0))
        if self._cache and self._cache[0] == marca:
            return self._cache[1]
        notas = []
        for arq in arqs:
            try:
                d = self._ler_fonte(arq)
            except Exception:
                continue
            if d:
                notas.append(d)
        self._cache = (marca, notas)
        return notas

    def fontes_por_pdf(self) -> dict[str, dict]:
        return {d["pdf"].lower(): d for d in self.todas() if d["pdf"]}

    def fonte_do_pdf(self, nome_pdf: str) -> dict | None:
        return self.fontes_por_pdf().get(nome_pdf.lower())

    def status_por_codigo(self) -> dict[str, str]:
        return {d["codigo"]: d["status"] for d in self.todas() if d["codigo"]}

    # ------------------------------------------------------------ escrita segura
    def _alterar(self, arq: Path, transformar) -> bool:
        """Lê, transforma e grava com guarda de data de modificação e cópia de segurança."""
        if not arq.exists():
            return False
        for _ in range(3):
            antes = arq.stat().st_mtime
            texto = arq.read_text(encoding="utf-8")
            novo = transformar(texto)
            if novo == texto:
                return False
            copia = self.copias / date.today().isoformat() / arq.relative_to(self.raiz)
            if not copia.exists():
                copia.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(arq, copia)
            if arq.stat().st_mtime != antes:          # alguém mexeu enquanto isso: relê
                time.sleep(0.5)
                continue
            tmp = arq.with_name(arq.name + ".painel.tmp")
            tmp.write_text(novo, encoding="utf-8")
            tmp.replace(arq)
            return True
        return False

    @staticmethod
    def _bloco(texto: str, nome: str, conteudo: str, antes_de: str | None = None) -> str:
        """Substitui (ou cria) o trecho <!-- painel:nome:inicio --> … <!-- painel:nome:fim -->."""
        ini, fim = f"<!-- painel:{nome}:inicio — escrito pelo Painel de Estudo -->", f"<!-- painel:{nome}:fim -->"
        bloco = f"{ini}\n{conteudo.rstrip()}\n{fim}"
        padrao = re.compile(re.escape(ini.split(" —")[0]) + r".*?" + re.escape(fim), re.S)
        if padrao.search(texto):
            return padrao.sub(lambda _: bloco, texto)
        if antes_de and antes_de in texto:
            return texto.replace(antes_de, bloco + "\n\n" + antes_de, 1)
        return texto.rstrip() + "\n\n" + bloco + "\n"

    # ------------------------------------------------------------ eventos
    def atualizar_fonte(self, fonte: dict, entrada: dict, pasta_hist: str) -> None:
        """Reescreve o bloco de leituras da nota e, se você leu, avança o status."""
        linhas = []
        for ex in entrada.get("ia", []):
            if ex.get("status") != "ok":
                continue
            v = ex.get("versao", "")
            rel = f"{pasta_hist}/{entrada['titulo'][:80]}/{v}/{entrada['titulo']}.leitura"
            conta = ", ".join(f"{ex[k]} {r}" for k, r in (("relevantes", "trechos relevantes"),
                              ("citadas", "citações"), ("baixadas", "baixados")) if ex.get(k) is not None)
            linhas.append(f"- 🤖 {data_br(ex.get('fim', ''))} — IA leu ({conta}) → [[{rel}|relatório]]")
        h = entrada.get("humano")
        if h:
            nota = " ".join((h.get("nota") or "").split())          # nota em uma linha só
            linhas.append(f"- 👤 {data_br(h['data'])} — **Romulo leu**" + (f". Nota: {nota}" if nota else ""))
        conteudo = "## Leituras registradas no painel\n" + ("\n".join(linhas) or "- (nenhuma ainda)")

        def mudar(texto: str) -> str:
            texto = self._bloco(texto, "leituras", conteudo, antes_de="## Ligações")
            if h and nivel(fonte["status"]) < ORDEM.index("leitura concluida"):
                texto = re.sub(r'^status:.*$', 'status: "leitura concluida"', texto, count=1, flags=re.M)
                texto = re.sub(r"^(\s*-\s*)status/[\w\-]+\s*$", r"\1status/leitura-concluida", texto, count=1, flags=re.M)
                texto = re.sub(r"(\*\*Status:\*\*)[^\n]*", r"\1 leitura concluída (registrada no painel)", texto, count=1)
            return texto

        with TRAVA:
            self._alterar(fonte["nota"], mudar)
            if h:
                self._marcar_moc(fonte)
                self._marcar_fila(fonte, h["data"])

    def _marcar_moc(self, fonte: dict) -> None:
        for moc in self.notas.glob("MOC — *.md"):
            def mudar(texto: str) -> str:
                linhas = texto.split("\n")
                for i, l in enumerate(linhas):
                    if f"[[{fonte['stem']}" in l and "📖lido" not in l and "✅fichado" not in l:
                        linhas[i] = l.rstrip() + " 📖lido"
                return "\n".join(linhas)
            self._alterar(moc, mudar)

    def _marcar_fila(self, fonte: dict, quando: str) -> None:
        def mudar(texto: str) -> str:
            linhas = texto.split("\n")
            for i, l in enumerate(linhas):
                if f"[[{fonte['stem']}" in l and l.lstrip().startswith("- [ ]"):
                    l = l.replace("- [ ]", "- [x]", 1)
                    if "📖" not in l:
                        l = l.rstrip() + f" · 📖 lido em {data_br(quando)[:10]}"
                    linhas[i] = l
            return "\n".join(linhas)
        self._alterar(self.fila, mudar)

    def atualizar_indice(self, registro: dict) -> None:
        mapa = self.fontes_por_pdf()
        por_stem = {k.rsplit(".", 1)[0]: v for k, v in mapa.items()}
        ia = [e for e in registro.values() if any(x.get("status") == "ok" for x in e["ia"])]
        eu = [e for e in registro.values() if e.get("humano")]
        fora = sorted(e["titulo"] for e in eu if e["titulo"].lower() not in por_stem)
        recentes = sorted(eu, key=lambda e: e["humano"]["data"], reverse=True)[:5]

        def nome(e):
            f = por_stem.get(e["titulo"].lower())
            return f"[[{f['stem']}|{f['codigo']}]] {f['titulo'][:60]}" if f else f"{e['titulo'][:60]} *(fora do inventário)*"

        conteudo = (
            f"### Leituras registradas pelo painel\n"
            f"*Atualizado em {datetime.now():%d/%m/%Y %H:%M}.*\n\n"
            f"| | |\n|---|---|\n"
            f"| Artigos lidos por você | {len(eu)} |\n"
            f"| Artigos lidos pela IA | {len(ia)} |\n"
            f"| Lidos por você fora do inventário | {len(fora)} |\n\n"
            + ("**Últimas leituras suas:**\n" + "\n".join(f"- {data_br(e['humano']['data'])[:10]} — {nome(e)}" for e in recentes)
               if recentes else "")
        )
        with TRAVA:
            self._alterar(self.indice, lambda t: self._bloco(t, "numeros", conteudo, antes_de="## Espinha dorsal"))
