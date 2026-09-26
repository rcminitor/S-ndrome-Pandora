"""
Estado da arte por critérios — a Tabela 3 da fundamentação teórica.

Fonte de verdade: dados_estadoarte.js (no site). Cada fonte recebe, para cada um dos
9 critérios, uma marca (✅ atende · ◐ em parte · ✗ não atende · NC não confirmado) e
a justificativa com a página do PDF. O painel grava:
  • dados_estadoarte.js — o site lê daqui (vai para o GitHub pelo Registro.publicar);
  • Notas\\Fundamentação — Estado da arte.md, trecho <!-- painel:estadoarte --> no cofre.

Regra do cofre: nada sem página. ✅ e ◐ só são aceitos com a página na justificativa;
quem confere no PDF é você — o painel não inventa nem sugere marca.
"""
from __future__ import annotations

import json
import re
import threading
from datetime import datetime
from pathlib import Path

MARCAS = ("✅", "◐", "✗", "NC")
CRITERIOS = [
    ("C1", "População: gatos com FIC/Pandora"),
    ("C2", "Estudo primário com dados próprios"),
    ("C3", "Dimensão temporal (acompanhamento longitudinal)"),
    ("C4", "Ambiente e estresse como variável"),
    ("C5", "Medida objetiva (não relato)"),
    ("C6", "Sensor, IoT ou IA"),
    ("C7", "Validação estatística"),
    ("C8", "Validação clínica"),
    ("C9", "Contexto domiciliar (casa do tutor)"),
]
NOTA = Path("Notas") / "Fundamentação — Estado da arte.md"
CABECALHO = "// Gerado pelo Painel de Estudo (painel_local/estadoarte.py). Edite pela aba Estado da Arte.\n"
TEM_PAGINA = re.compile(r"\bpp?\.\s*\d")


class EstadoArte:
    def __init__(self, raiz_site: Path, cofre=None):
        self.js = Path(raiz_site) / "dados_estadoarte.js"
        self.cofre = cofre                      # objeto Cofre (painel_local/cofre.py) ou None
        self.trava = threading.Lock()

    # ------------------------------------------------------------ leitura
    def ler(self) -> dict:
        if not self.js.exists():
            return {"criterios": [{"id": i, "nome": n} for i, n in CRITERIOS], "fontes": []}
        texto = self.js.read_text(encoding="utf-8")
        return json.loads(texto[texto.index("{"):texto.rindex("}") + 1])

    # ------------------------------------------------------------ validação
    @staticmethod
    def validar(fonte: dict) -> list[str]:
        erros = []
        cod = str(fonte.get("codigo", "")).strip()
        if not re.fullmatch(r"S?\d{1,3}", cod):
            erros.append("Código inválido (use o do inventário: 1–53 ou S1–S11).")
        if not str(fonte.get("titulo", "")).strip():
            erros.append("Falta o título curto da fonte.")
        marcas = fonte.get("marcas") or {}
        for cid, nome in CRITERIOS:
            m = marcas.get(cid) or {}
            if m.get("m") not in MARCAS:
                erros.append(f"{cid}: escolha ✅, ◐, ✗ ou NC.")
            elif m["m"] in ("✅", "◐") and not TEM_PAGINA.search(m.get("txt", "")):
                erros.append(f"{cid} ({nome}): {m['m']} precisa da página na justificativa (ex.: p. 68).")
        return erros

    # ------------------------------------------------------------ gravação
    def salvar(self, fonte: dict) -> list[str]:
        """Inclui ou substitui a fonte. Devolve a lista de erros (vazia = gravou)."""
        erros = self.validar(fonte)
        if erros:
            return erros
        limpa = {"codigo": str(fonte["codigo"]).strip(), "titulo": str(fonte["titulo"]).strip(),
                 "marcas": {cid: {"m": fonte["marcas"][cid]["m"], "txt": str(fonte["marcas"][cid].get("txt", "")).strip()}
                            for cid, _ in CRITERIOS},
                 "atualizado": datetime.now().isoformat(timespec="minutes")}
        with self.trava:
            dados = self.ler()
            fontes = [f for f in dados["fontes"] if f["codigo"] != limpa["codigo"]]
            fontes.append(limpa)
            dados["fontes"] = sorted(fontes, key=_ordem)
            dados["criterios"] = [{"id": i, "nome": n} for i, n in CRITERIOS]
            self._gravar(dados)
        self.escrever_cofre()
        return []

    def remover(self, codigo: str) -> bool:
        with self.trava:
            dados = self.ler()
            antes = len(dados["fontes"])
            dados["fontes"] = [f for f in dados["fontes"] if f["codigo"] != codigo]
            if len(dados["fontes"]) == antes:
                return False
            self._gravar(dados)
        self.escrever_cofre()
        return True

    def _gravar(self, dados: dict) -> None:
        dados["atualizado"] = datetime.now().isoformat(timespec="minutes")
        tmp = self.js.with_name(self.js.name + ".painel.tmp")
        tmp.write_text(CABECALHO + "window.ESTADO_ARTE = " + json.dumps(dados, ensure_ascii=False, indent=1) + ";\n",
                       encoding="utf-8")
        tmp.replace(self.js)

    def escrever_site(self) -> None:          # usado por Registro.extras: o arquivo já é a fonte de verdade
        if not self.js.exists():
            self._gravar(self.ler())

    # ------------------------------------------------------------ cofre (Obsidian)
    def tabela_markdown(self) -> str:
        dados = self.ler()
        fontes = dados["fontes"]
        cab = "| Critério (foco da tese) | " + " | ".join("#" + f["codigo"] if f["codigo"][0].isdigit()
                                                         else f["codigo"] for f in fontes) + " |"
        sep = "|---" * (len(fontes) + 1) + "|"
        linhas = []
        for cid, nome in CRITERIOS:
            cel = []
            for f in fontes:
                m = f["marcas"][cid]
                cel.append((m["m"] + (" " + m["txt"] if m["txt"] else "")).replace("|", "/"))
            linhas.append(f"| **{cid}.** {nome} | " + " | ".join(cel) + " |")
        return "\n".join([cab, sep, *linhas])

    def escrever_cofre(self) -> bool:
        if not self.cofre or not getattr(self.cofre, "ativo", False):
            return False
        arq = self.cofre.raiz / NOTA
        tabela = self.tabela_markdown()
        return self.cofre._alterar(arq, lambda t: self.cofre._bloco(t, "estadoarte", tabela))


def _ordem(f: dict):
    c = f["codigo"]
    return (1, int(c[1:])) if c.startswith("S") else (0, int(c))
