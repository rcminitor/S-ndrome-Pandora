"""Reaponta notas de fonte cujo PDF mudou de pasta dentro do cofre.

Para cada nota em ``Fontes/`` cuja linha ``**PDF:** [[PDF/...pdf]]`` aponta para
um arquivo que não existe mais, procura um PDF de mesmo nome em ``PDF/``. Só
reescreve quando há exatamente uma correspondência. Sem ``--write`` apenas
mostra o que mudaria. PDFs que não existem em lugar nenhum são apenas listados.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


LINHA_PDF = re.compile(r"(\*\*PDF:\*\*\s*\[\[)([^\]|#]+\.pdf)(\]\]|\||#)", re.I)


def remapear(cofre: Path, gravar: bool = False) -> tuple[list[tuple[str, str, str]], list[tuple[str, str]], list[tuple[str, str]]]:
    """Devolve (remapeados, ausentes, ambiguos); cada remapeado é (nota, antigo, novo)."""
    por_nome: dict[str, list[str]] = {}
    for pdf in (cofre / "PDF").rglob("*.pdf"):
        por_nome.setdefault(pdf.name.casefold(), []).append(pdf.relative_to(cofre).as_posix())

    remapeados: list[tuple[str, str, str]] = []
    ausentes: list[tuple[str, str]] = []
    ambiguos: list[tuple[str, str]] = []
    for nota in sorted((cofre / "Fontes").glob("*.md")):
        texto = nota.read_text(encoding="utf-8")
        achou = LINHA_PDF.search(texto)
        if not achou:
            continue
        antigo = achou.group(2).strip().replace("\\", "/")
        if (cofre / antigo).is_file():
            continue
        candidatos = por_nome.get(Path(antigo).name.casefold(), [])
        if len(candidatos) == 1:
            novo = candidatos[0]
            remapeados.append((nota.name, antigo, novo))
            if gravar:
                texto = texto[:achou.start(2)] + novo + texto[achou.end(2):]
                nota.write_text(texto, encoding="utf-8", newline="")
        elif candidatos:
            ambiguos.append((nota.name, antigo))
        else:
            ausentes.append((nota.name, antigo))
    return remapeados, ausentes, ambiguos


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reaponta notas de fonte para PDFs movidos")
    parser.add_argument("--cofre", required=True, type=Path)
    parser.add_argument("--write", action="store_true", help="grava as notas (padrão: só simula)")
    args = parser.parse_args(argv)
    if not (args.cofre / "Fontes").is_dir():
        print(f"ERRO: {args.cofre} não parece um cofre (sem Fontes/)")
        return 2
    remapeados, ausentes, ambiguos = remapear(args.cofre, args.write)
    verbo = "REMAPEADO" if args.write else "REMAPEARIA"
    for nota, antigo, novo in remapeados:
        print(f"{verbo}: {nota}\n    {antigo}\n -> {novo}")
    for nota, antigo in ambiguos:
        print(f"AMBIGUO (vários PDFs com esse nome): {nota} -> {antigo}")
    for nota, antigo in ausentes:
        print(f"AUSENTE (PDF não existe no cofre): {nota} -> {antigo}")
    print(f"\n{len(remapeados)} remapeado(s), {len(ambiguos)} ambíguo(s), {len(ausentes)} ausente(s).")
    if remapeados and not args.write:
        print("Nada foi alterado. Use --write para gravar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
