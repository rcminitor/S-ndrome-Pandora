"""Caixa de entrada não publicável para PDFs ainda não cadastrados.

O módulo apenas inspeciona arquivos em ``PDF/_Entrada``. Metadados extraídos
são sugestões para conferência humana e nunca viram referência confirmada.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import pymupdf


PASTA_ENTRADA = "_Entrada"
DOI = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)
ANO = re.compile(r"\b(?:19|20)\d{2}\b")
CODIGO = re.compile(r'^codigo:\s*["\']?([A-Z]{0,3}\d{1,4})["\']?\s*$', re.M | re.I)


def _hash(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


def _codigo_sugerido(cofre: Path) -> str:
    numeros: list[int] = []
    for nota in (cofre / "Fontes").glob("*.md"):
        achou = CODIGO.search(nota.read_text(encoding="utf-8", errors="replace"))
        if achou and achou.group(1).isdigit():
            numeros.append(int(achou.group(1)))
    return str(max(numeros, default=0) + 1)


def _pdfs_existentes(cofre: Path) -> dict[tuple[int, str], str]:
    entrada = (cofre / "PDF" / PASTA_ENTRADA).resolve()
    existentes: dict[tuple[int, str], str] = {}
    for pdf in (cofre / "PDF").rglob("*.pdf"):
        try:
            pdf.resolve().relative_to(entrada)
            continue
        except ValueError:
            pass
        try:
            existentes[(pdf.stat().st_size, _hash(pdf))] = pdf.relative_to(cofre).as_posix()
        except OSError:
            continue
    return existentes


def analisar_pdf(caminho: Path, duplicatas: dict[tuple[int, str], str]) -> dict:
    item = {
        "arquivo": caminho.name,
        "kb": round(caminho.stat().st_size / 1024),
        "valido": False,
        "paginas": 0,
        "titulo_sugerido": "",
        "autores_sugeridos": "",
        "ano_sugerido": "",
        "doi_sugerido": "",
        "duplicado_em": "",
        "aviso": "",
    }
    try:
        with caminho.open("rb") as arquivo:
            cabecalho = arquivo.read(5)
        if cabecalho != b"%PDF-":
            raise ValueError("cabeçalho de PDF inválido")
        digest = _hash(caminho)
        item["duplicado_em"] = duplicatas.get((caminho.stat().st_size, digest), "")
        with pymupdf.open(caminho) as documento:
            item["paginas"] = documento.page_count
            if documento.page_count < 1:
                raise ValueError("PDF sem páginas")
            meta = documento.metadata or {}
            texto = "\n".join(
                documento.load_page(i).get_text("text")
                for i in range(min(2, documento.page_count))
            )
        titulo = str(meta.get("title") or "").strip()
        if titulo and titulo.casefold() not in {caminho.stem.casefold(), "untitled"}:
            item["titulo_sugerido"] = titulo
        item["autores_sugeridos"] = str(meta.get("author") or "").strip()
        achou_doi = DOI.search(texto)
        if achou_doi:
            item["doi_sugerido"] = achou_doi.group(0).rstrip(".,;)")
        anos = ANO.findall(texto[:8000])
        if anos:
            item["ano_sugerido"] = anos[0]
        item["valido"] = True
        if item["duplicado_em"]:
            item["aviso"] = f"Conteúdo idêntico já existe em {item['duplicado_em']}"
    except Exception as exc:
        item["aviso"] = f"Não foi possível validar: {exc}"
    return item


def listar_entrada(cofre: Path) -> dict:
    cofre = Path(cofre)
    entrada = cofre / "PDF" / PASTA_ENTRADA
    entrada.mkdir(parents=True, exist_ok=True)
    duplicatas = _pdfs_existentes(cofre)
    itens = [
        analisar_pdf(pdf, duplicatas)
        for pdf in sorted(entrada.glob("*.pdf"), key=lambda p: p.name.casefold())
        if pdf.is_file()
    ]
    return {
        "pasta": str(entrada),
        "codigo_sugerido": _codigo_sugerido(cofre),
        "itens": itens,
        "aviso": "Metadados são sugestões e precisam ser conferidos no PDF original.",
    }


def caminho_seguro(cofre: Path, nome: str) -> Path:
    entrada = (Path(cofre) / "PDF" / PASTA_ENTRADA).resolve()
    caminho = (entrada / Path(str(nome).replace("\\", "/")).name).resolve()
    if caminho.parent != entrada or not caminho.is_file() or caminho.suffix.casefold() != ".pdf":
        raise ValueError("PDF não encontrado na Caixa de entrada.")
    return caminho


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lista PDFs aguardando cadastro em PDF/_Entrada")
    parser.add_argument("--cofre", required=True, type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(listar_entrada(args.cofre), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
