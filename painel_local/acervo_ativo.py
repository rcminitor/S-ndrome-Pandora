"""Leitura única do conjunto publicável: fonte + manifesto + PDF físico."""
from __future__ import annotations

from pathlib import Path

from guardiao_acervo import ler_json_js


def itens_ativos(painel: Path) -> list[dict]:
    painel = Path(painel).resolve()
    inventario = ler_json_js(painel / "dados_inventario.js", "DADOS_INVENTARIO")
    manifesto = ler_json_js(painel / "dados_pdfs.js", "DADOS_PDFS")
    autorizados = {
        str(item.get("arquivo", "")).replace("\\", "/")
        for item in manifesto
        if str(item.get("arquivo", "")).replace("\\", "/").startswith("PDF/")
    }
    ativos = []
    for item in inventario:
        arquivo = str(item.get("arquivo", "")).replace("\\", "/")
        caminho = (painel / arquivo).resolve()
        if arquivo in autorizados and caminho.is_relative_to(painel) and caminho.is_file():
            ativos.append(item)
    return ativos


def codigos_ativos(painel: Path) -> set[str]:
    return {str(item.get("codigo", "")).strip() for item in itens_ativos(painel)}
