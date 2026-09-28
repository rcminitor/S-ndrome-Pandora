"""Valida o acervo publicado sem alterar nenhum arquivo.

O Guardião trabalha com relações, não com contagens fixas: cada ficha precisa
ter uma fonte, cada fonte precisa apontar para um PDF publicado e os códigos e
caminhos precisam ser únicos. Erros retornam código de saída 1 e bloqueiam a
publicação; avisos registram situações legadas que não tornam o site inválido.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable


def ler_json_js(caminho: Path, variavel: str):
    texto = caminho.read_text(encoding="utf-8-sig")
    prefixo = f"window.{variavel} ="
    if prefixo not in texto:
        raise ValueError(f"{caminho.name}: variável {variavel} não encontrada")
    bruto = texto[texto.index(prefixo) + len(prefixo):].strip().removesuffix(";")
    return json.loads(bruto)


@dataclass
class Relatorio:
    erros: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    numeros: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.erros

    def texto(self) -> str:
        estado = "APROVADO" if self.ok else "BLOQUEADO"
        linhas = [f"Guardiao do acervo: {estado}"]
        if self.numeros:
            linhas.append("  " + " | ".join(f"{k}: {v}" for k, v in self.numeros.items()))
        linhas.extend(f"  ERRO: {e}" for e in self.erros)
        linhas.extend(f"  AVISO: {a}" for a in self.avisos)
        return "\n".join(linhas)


def _duplicados(valores: Iterable[str]) -> set[str]:
    vistos: set[str] = set()
    repetidos: set[str] = set()
    for valor in valores:
        chave = valor.casefold()
        if chave in vistos:
            repetidos.add(valor)
        vistos.add(chave)
    return repetidos


def _status_fichado(valor: object) -> bool:
    return "fichamento concluido" in str(valor or "").casefold()


def _titulo_normalizado(valor: object) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or "")).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def _doi(valor: object) -> str:
    achou = re.search(r"10\.\d{4,9}/\S+", str(valor or ""), re.I)
    if not achou:
        return ""
    doi = achou.group(0).rstrip(".,;)").casefold()
    return doi if len(doi.split("/", 1)[1]) >= 4 else ""


def validar_dados(
    inventario: list[dict],
    pdfs: list[dict],
    fichamentos: list[dict],
    existe: Callable[[str], bool],
    cabecalho_pdf: Callable[[str], bytes] | None = None,
    hash_pdf: Callable[[str], str] | None = None,
) -> Relatorio:
    r = Relatorio()
    codigos = [str(a.get("codigo", "")).strip() for a in inventario]
    caminhos = [str(a.get("arquivo", "")).replace("\\", "/").strip() for a in inventario]
    codigos_fichas = [str(f.get("codigo", "")).strip() for f in fichamentos]
    manifesto = {
        str(p.get("arquivo", "")).replace("\\", "/").strip()
        for p in pdfs if str(p.get("arquivo", "")).strip()
    }

    r.numeros = {
        "fontes": len(inventario),
        "pdfs_autorizados": sum(1 for p in manifesto if p.startswith("PDF/")),
        "fichamentos": len(fichamentos),
    }

    if not inventario:
        r.erros.append("inventario vazio")
    if "" in codigos:
        r.erros.append("ha fonte sem codigo")
    for codigo in sorted(_duplicados(codigos)):
        r.erros.append(f"codigo duplicado no inventario: {codigo}")
    for codigo in sorted(_duplicados(codigos_fichas)):
        r.erros.append(f"codigo duplicado nos fichamentos: {codigo}")
    for caminho in sorted(_duplicados(caminhos)):
        r.erros.append(f"PDF usado por mais de uma fonte: {caminho}")

    titulos_validos = [
        _titulo_normalizado(a.get("titulo"))
        for a in inventario
        if _titulo_normalizado(a.get("titulo")) not in {"", "nao confirmado"}
    ]
    for titulo in sorted(_duplicados(titulos_validos)):
        r.erros.append(f"titulo duplicado no inventario: {titulo}")
    dois = [_doi(a.get("referencia")) for a in inventario if _doi(a.get("referencia"))]
    for doi in sorted(_duplicados(dois)):
        r.erros.append(f"DOI duplicado no inventario: {doi}")

    codigos_set = set(codigos)
    fichas_set = set(codigos_fichas)
    for codigo in sorted(fichas_set - codigos_set):
        r.erros.append(f"fichamento orfao, sem fonte no inventario: {codigo}")
    for artigo in inventario:
        codigo = str(artigo.get("codigo", "")).strip()
        caminho = str(artigo.get("arquivo", "")).replace("\\", "/").strip()
        if not caminho.startswith("PDF/"):
            r.erros.append(f"{codigo}: caminho fora da pasta PDF/: {caminho or '(vazio)'}")
            continue
        if caminho not in manifesto:
            r.erros.append(f"{codigo}: PDF ausente do manifesto: {caminho}")
        if not existe(caminho):
            r.erros.append(f"{codigo}: arquivo inexistente: {caminho}")
        elif cabecalho_pdf and not cabecalho_pdf(caminho).startswith(b"%PDF"):
            r.erros.append(f"{codigo}: arquivo nao e um PDF valido: {caminho}")
        if _status_fichado(artigo.get("status")) and codigo not in fichas_set:
            r.erros.append(f"{codigo}: status concluido, mas o fichamento nao existe")

    for caminho in sorted(p for p in manifesto if not p.startswith("PDF/")):
        r.avisos.append(f"item legado fora de PDF/ ignorado pelo Acervo: {caminho}")
    caminhos_ativos = set(caminhos)
    for caminho in sorted(p for p in manifesto if p.startswith("PDF/") and p not in caminhos_ativos):
        r.erros.append(f"PDF sem fonte ativa no inventario: {caminho}")

    if hash_pdf:
        por_hash: dict[str, list[tuple[str, str]]] = {}
        for codigo, caminho in zip(codigos, caminhos):
            if caminho.startswith("PDF/") and existe(caminho):
                por_hash.setdefault(hash_pdf(caminho), []).append((codigo, caminho))
        for itens in por_hash.values():
            if len(itens) > 1:
                descr = ", ".join(f"{codigo} ({caminho})" for codigo, caminho in itens)
                r.erros.append(f"fontes distintas usam PDFs identicos: {descr}")
    return r


def validar_publicacao(raiz: Path) -> Relatorio:
    raiz = Path(raiz)
    try:
        inventario = ler_json_js(raiz / "dados_inventario.js", "DADOS_INVENTARIO")
        pdfs = ler_json_js(raiz / "dados_pdfs.js", "DADOS_PDFS")
        fich_obj = ler_json_js(raiz / "dados_fichamentos.js", "DADOS_FICHAMENTOS")
        fichamentos = fich_obj.get("fichamentos", [])
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return Relatorio(erros=[f"nao foi possivel ler os dados publicados: {exc}"])

    def existe(caminho: str) -> bool:
        return (raiz / Path(caminho)).is_file()

    def cabecalho(caminho: str) -> bytes:
        with (raiz / Path(caminho)).open("rb") as entrada:
            return entrada.read(5)

    def digest(caminho: str) -> str:
        h = hashlib.sha256()
        with (raiz / Path(caminho)).open("rb") as entrada:
            for bloco in iter(lambda: entrada.read(1024 * 1024), b""):
                h.update(bloco)
        return h.hexdigest()

    return validar_dados(inventario, pdfs, fichamentos, existe, cabecalho, digest)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Valida o acervo antes da publicacao")
    parser.add_argument("--raiz", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true", dest="como_json")
    args = parser.parse_args(argv)
    rel = validar_publicacao(args.raiz)
    if args.como_json:
        print(json.dumps({"ok": rel.ok, "numeros": rel.numeros, "erros": rel.erros,
                          "avisos": rel.avisos}, ensure_ascii=False, indent=2))
    else:
        print(rel.texto())
    return 0 if rel.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
