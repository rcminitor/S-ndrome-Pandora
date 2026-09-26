"""
Registro de leituras — o que a IA leu, o que você leu, e o que vai para o site
=============================================================================

• registro_leituras.json (na pasta Leitura do cofre, PRIVADO): tudo, inclusive
  as suas notas e cada execução da IA.
• Historico_IA\\<artigo>\\<data_hora>\\ : cópia de TODA leitura feita pela IA
  (relatório .md, dados .json e o registro da execução). Nada é sobrescrito.
• dados_leituras.js (no repositório do site, PÚBLICO): só título, datas e
  contagens — sem tradução, sem PDF, sem as suas notas. É enviado ao GitHub
  sozinho (git commit + push) a cada início/fim de leitura e a cada "Eu li".
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
from datetime import datetime
from pathlib import Path

TRAVA = threading.Lock()
TRAVA_SITE = threading.Lock()
SITE = {"ok": None, "quando": "", "erro": "", "enviando": False}
COFRE_ST = {"ok": None, "quando": "", "erro": ""}


class Registro:
    def __init__(self, biblioteca: Path, raiz_site: Path, publicar: bool = True, cofre=None):
        self.cofre = cofre if cofre is not None and cofre.ativo else None
        self.extras: list[tuple[str, callable]] = []     # outros arquivos do site (ex.: dados_revisao.js)
        self._timer: threading.Timer | None = None
        self.biblioteca = biblioteca
        self.arq = biblioteca / "registro_leituras.json"
        self.hist = biblioteca / "Historico_IA"
        self.site_js = raiz_site / "dados_leituras.js"
        self.raiz_site = raiz_site
        self.publicar_ativo = publicar

    # ------------------------------------------------------------ base
    def carregar(self) -> dict:
        if self.arq.exists():
            try:
                return json.loads(self.arq.read_text(encoding="utf-8"))
            except Exception:
                shutil.copy2(self.arq, self.arq.with_suffix(".json.bak"))   # nunca perde o antigo
        return {}

    def _salvar(self, reg: dict) -> None:
        self.arq.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.arq.with_suffix(".tmp")
        tmp.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.arq)

    @staticmethod
    def agora() -> str:
        return datetime.now().isoformat(timespec="minutes")

    def _entrada(self, reg: dict, pdf: Path) -> dict:
        return reg.setdefault(pdf.stem, {"titulo": pdf.stem, "ia": [], "humano": None})

    def resumo(self, stem: str) -> dict | None:
        e = self.carregar().get(stem)
        if not e:
            return None
        ult = e["ia"][-1] if e["ia"] else None
        return {"ia_vezes": len(e["ia"]), "ia_ultima": ult, "humano": e["humano"]}

    # ------------------------------------------------------------ eventos
    def ia_inicio(self, pdf: Path, opcoes: dict) -> None:
        with TRAVA:
            reg = self.carregar()
            e = self._entrada(reg, pdf)
            e["ia"].append({"inicio": self.agora(), "fim": "", "status": "lendo", "opcoes": opcoes})
            self._salvar(reg)
        self.publicar(f"IA começou a ler {pdf.stem}")

    def ia_fim(self, pdf: Path, ok: bool, log: list[str]) -> str:
        """Guarda a versão no histórico e as contagens. Devolve a pasta da versão."""
        md = pdf.with_name(pdf.stem + ".leitura.md")
        js = pdf.with_name(pdf.stem + ".leitura.json")
        texto_log = "\n".join(log)
        with TRAVA:
            reg = self.carregar()
            e = self._entrada(reg, pdf)
            if not e["ia"] or e["ia"][-1]["status"] != "lendo":
                e["ia"].append({"inicio": self.agora(), "opcoes": {}})
            ex = e["ia"][-1]
            versao = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            pasta = self.hist / pdf.stem[:80] / versao
            pasta.mkdir(parents=True, exist_ok=True)
            for arq in (md, js):
                if arq.exists():
                    shutil.copy2(arq, pasta / arq.name)
            (pasta / "registro_da_execucao.txt").write_text(texto_log, encoding="utf-8")
            ex.update({"fim": self.agora(), "status": "ok" if ok else "erro", "versao": versao,
                       "reserva_paga": "RESERVA PAGA" in texto_log})
            m = re.search(r"tokens usados: (\d+)", texto_log)
            ex["tokens"] = int(m.group(1)) if m else None
            if ok and js.exists():
                ex.update(self._contagens(js))
            self._salvar(reg)
        self._no_cofre(pdf)
        self.publicar(f"IA terminou de ler {pdf.stem}")
        return str(pasta)

    @staticmethod
    def _contagens(js: Path) -> dict:
        try:
            d = json.loads(js.read_text(encoding="utf-8"))
        except Exception:
            return {}
        refs = d.get("referencias", [])
        return {
            "paragrafos": len(d.get("trechos", [])),
            "relevantes": len(d.get("relevantes", [])),
            "traduzidos": sum(1 for t in d.get("trechos", []) if t.get("traducao")),
            "referencias": len(refs),
            "citadas": sum(1 for r in refs if r.get("citada_em")),
            "baixadas": sum(1 for r in refs if r.get("arquivo")),
        }

    def humano_li(self, pdf: Path, nota: str) -> None:
        with TRAVA:
            reg = self.carregar()
            e = self._entrada(reg, pdf)
            e["humano"] = {"data": self.agora(), "nota": nota.strip(), "paginas": self._paginas(pdf)}
            self._salvar(reg)
        self._no_cofre(pdf)
        self.publicar(f"Romulo leu {pdf.stem}")

    @staticmethod
    def _paginas(pdf: Path) -> int:
        """Tamanho do PDF (para o 'páginas lidas' do acompanhamento)."""
        try:
            import pymupdf
            with pymupdf.open(pdf) as d:
                return d.page_count
        except Exception:
            js = pdf.with_name(pdf.stem + ".leitura.json")
            try:
                return max(t["pagina"] for t in json.loads(js.read_text(encoding="utf-8"))["trechos"])
            except Exception:
                return 0

    def _no_cofre(self, pdf: Path) -> None:
        """Leva o evento para as notas do cofre (fonte, MOC, Fila, Índice). Falha aqui não
        derruba o painel: fica registrada e aparece na tela."""
        if not self.cofre:
            return
        try:
            reg = self.carregar()
            fonte = self.cofre.fonte_do_pdf(pdf.name)
            if fonte:
                rel_hist = self.hist.relative_to(self.cofre.raiz).as_posix() if self.hist.is_relative_to(self.cofre.raiz) else "Historico_IA"
                self.cofre.atualizar_fonte(fonte, reg[pdf.stem], rel_hist)
            self.cofre.atualizar_indice(reg)
            COFRE_ST.update(ok=True, quando=self.agora(), erro="")
        except Exception as e:
            COFRE_ST.update(ok=False, quando=self.agora(), erro=f"{type(e).__name__}: {e}")

    def versoes(self, stem: str) -> list[str]:
        p = self.hist / stem[:80]
        return sorted((v.name for v in p.iterdir() if v.is_dir()), reverse=True) if p.exists() else []

    def arquivo_versao(self, stem: str, versao: str) -> Path | None:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}_\d{6}", versao):
            return None
        md = self.hist / stem[:80] / versao / f"{stem}.leitura.md"
        return md if md.exists() else None

    # ------------------------------------------------------------ site
    def dados_publicos(self) -> list[dict]:
        saida = []
        por_stem = {k.rsplit(".", 1)[0]: v for k, v in self.cofre.fontes_por_pdf().items()} if self.cofre else {}
        for e in self.carregar().values():
            ult = e["ia"][-1] if e["ia"] else {}
            f = por_stem.get(e["titulo"].lower()) or {}
            saida.append({
                "titulo": f.get("titulo") or e["titulo"],
                "codigo": f.get("codigo", ""),
                "status_cofre": f.get("status", ""),
                "ia_vezes": len(e["ia"]),
                "ia_inicio": ult.get("inicio", ""),
                "ia_fim": ult.get("fim", ""),
                "ia_status": ult.get("status", ""),
                **{k: ult.get(k) for k in ("relevantes", "traduzidos", "referencias", "citadas", "baixadas")},
                "eu_li": (e["humano"] or {}).get("data", ""),          # a nota NÃO vai para o site
            })
        return sorted(saida, key=lambda x: x["eu_li"] or x["ia_inicio"], reverse=True)

    def sincronizar_inventario_site(self) -> bool:
        """dados_inventario.js do site passa a mostrar o status das notas do cofre."""
        inv = self.raiz_site / "dados_inventario.js"
        if not self.cofre or not inv.exists():
            return False
        bruto = inv.read_text(encoding="utf-8-sig")
        itens = json.loads(bruto[bruto.index("["): bruto.rindex("]") + 1])
        status = self.cofre.status_por_codigo()
        mudou = False
        for it in itens:
            novo = status.get(str(it.get("codigo")))
            if novo and it.get("status") != novo:
                it["status"] = novo
                mudou = True
        if mudou:
            inv.write_text("window.DADOS_INVENTARIO = " + json.dumps(itens, ensure_ascii=False, indent=4) + ";\n",
                           encoding="utf-8")
        return mudou

    def escrever_site(self) -> None:
        for _, escrever in self.extras:
            try:
                escrever()
            except Exception:
                pass
        self.sincronizar_inventario_site()
        self.site_js.write_text(
            "// Gerado pelo Painel de Estudo (painel_local/registro.py). Só títulos, datas e contagens.\n"
            "window.DADOS_LEITURAS = " + json.dumps(self.dados_publicos(), ensure_ascii=False, indent=1) + ";\n",
            encoding="utf-8")

    def publicar_depois(self, motivo: str, segundos: int = 120) -> None:
        """Junta vários eventos seguidos (ex.: uma sessão de revisão) num envio só."""
        if self._timer and self._timer.is_alive():
            return
        self._timer = threading.Timer(segundos, self.publicar, args=(motivo,))
        self._timer.daemon = True
        self._timer.start()

    def publicar(self, motivo: str) -> None:
        if self.publicar_ativo:
            threading.Thread(target=self._publicar, args=(motivo,), daemon=True).start()
        else:
            self.escrever_site()

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(self.raiz_site), *args], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=180,
                              env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})

    def _publicar(self, motivo: str) -> None:
        with TRAVA_SITE:
            SITE["enviando"] = True
            try:
                p = self._git("pull", "--rebase", "--autostash", "-q")
                if p.returncode != 0:
                    raise RuntimeError("git pull: " + (p.stderr or p.stdout).strip()[:200])
                self.escrever_site()
                arqs = ["dados_leituras.js", "dados_inventario.js"] + [n for n, _ in self.extras
                                                                      if (self.raiz_site / n).exists()]
                self._git("add", *arqs)
                if self._git("diff", "--cached", "--quiet", "--", *arqs).returncode == 0:
                    SITE.update(ok=True, quando=self.agora(), erro="")
                    return
                c = self._git("commit", "-q", "-m", f"Registro de leituras: {motivo}", "--", *arqs)
                if c.returncode != 0:
                    raise RuntimeError("git commit: " + (c.stderr or c.stdout).strip()[:200])
                s = self._git("push", "-q")
                if s.returncode != 0:
                    raise RuntimeError("git push: " + (s.stderr or s.stdout).strip()[:200])
                SITE.update(ok=True, quando=self.agora(), erro="")
            except Exception as e:
                SITE.update(ok=False, quando=self.agora(), erro=str(e))
            finally:
                SITE["enviando"] = False
