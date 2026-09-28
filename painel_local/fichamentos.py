"""
Fichamentos no site — copia os fichamentos em markdown do cofre (Fichamentos\\) para
dados_fichamentos.js, que a aba "Fichamentos" do site lê.

Só leitura no cofre: nada é alterado lá. O arquivo do site é refeito sempre que o
painel publica (Registro.extras), então um fichamento novo aparece no site sozinho.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from acervo_ativo import codigos_ativos

CABECALHO = "// Gerado pelo Painel de Estudo (painel_local/fichamentos.py) a partir de Fichamentos\\ do cofre.\n"


def _frontmatter(texto: str) -> tuple[dict, str]:
    if not texto.startswith("---"):
        return {}, texto
    fim = texto.find("\n---", 3)
    if fim < 0:
        return {}, texto
    meta = {}
    for linha in texto[3:fim].splitlines():
        m = re.match(r'^(\w+):\s*"?(.*?)"?\s*$', linha)
        if m:
            meta[m.group(1)] = m.group(2)
    return meta, texto[fim + 4:].lstrip("\n")


def ler_fichamentos(cofre_dir: Path) -> list[dict]:
    pasta = Path(cofre_dir) / "Fichamentos"
    saida = []
    for arq in sorted(pasta.glob("*.md")):
        if arq.name.startswith("00 "):
            continue
        bruto = arq.read_text(encoding="utf-8")
        meta, corpo = _frontmatter(bruto)
        topo = bruto[:600]
        codigo = meta.get("codigo") or arq.name.split(" ")[0]
        titulo = re.sub(r"^\S+ — Fichamento — ", "", arq.stem)
        nucleo = "1" if "nucleo/1" in topo else ("2" if "nucleo/2" in topo else "")
        saida.append({"codigo": codigo, "titulo": titulo, "arquivo": arq.name,
                      "data": meta.get("data_do_fichamento", ""), "paginas": meta.get("paginas_lidas", ""),
                      "nucleo": nucleo, "md": corpo})
    return saida


class Fichamentos:
    def __init__(self, raiz_site: Path, cofre_dir: Path | None):
        self.js = Path(raiz_site) / "dados_fichamentos.js"
        self.cofre_dir = cofre_dir

    def escrever_site(self) -> None:
        if not self.cofre_dir or not (Path(self.cofre_dir) / "Fichamentos").exists():
            return
        ativos = codigos_ativos(self.js.parent)
        fichamentos = [
            ficha for ficha in ler_fichamentos(self.cofre_dir)
            if str(ficha.get("codigo", "")) in ativos
        ]
        dados = {"atualizado": datetime.now().isoformat(timespec="minutes"),
                 "fichamentos": fichamentos}
        novo = CABECALHO + "window.DADOS_FICHAMENTOS = " + json.dumps(dados, ensure_ascii=False, indent=1) + ";\n"
        antigo = self.js.read_text(encoding="utf-8") if self.js.exists() else ""
        if re.sub(r'"atualizado": "[^"]*"', "", novo) == re.sub(r'"atualizado": "[^"]*"', "", antigo):
            return                                   # nada mudou: não gera commit à toa
        tmp = self.js.with_name(self.js.name + ".painel.tmp")
        tmp.write_text(novo, encoding="utf-8")
        tmp.replace(self.js)
