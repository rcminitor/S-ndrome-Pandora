"""Auditoria e correção conservadora do acervo da tese.

``diagnosticar`` nunca escreve. ``corrigir`` regenera somente arquivos derivados
do painel. Os PDFs ficam só no cofre e nunca são copiados para o site. Nenhum PDF, nota ou
fichamento do cofre é apagado ou criado por esta rotina.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from guardiao_acervo import ler_json_js, validar_publicacao
from publicar_acervo import ErroPublicacao, PublicadorAcervo
from sincronizar_acervo import IGNORAR_PDF, _caminho_pdf_valido, _notas, construir, sincronizar


ARQUIVOS_DERIVADOS = ["dados_inventario.js", "dados_pdfs.js", "dados_fichamentos.js", "index.html"]


@dataclass
class Achado:
    tipo: str
    mensagem: str
    corrigivel: bool = False
    gravidade: str = "aviso"


def _hash(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


def _normalizado(valor) -> str:
    return json.dumps(valor, ensure_ascii=False, sort_keys=True)


def auditar(cofre: Path, painel: Path) -> dict:
    cofre, painel = Path(cofre).resolve(), Path(painel).resolve()
    achados: list[Achado] = []
    inventario_esperado, pdfs_esperados, fichas_esperadas, _avisos, _ = construir(cofre, painel)
    inventario_atual = ler_json_js(painel / "dados_inventario.js", "DADOS_INVENTARIO")
    pdfs_atuais = ler_json_js(painel / "dados_pdfs.js", "DADOS_PDFS")
    fichas_atuais = ler_json_js(painel / "dados_fichamentos.js", "DADOS_FICHAMENTOS")

    comparacoes = (
        ("inventário", inventario_atual, inventario_esperado),
        ("manifesto de PDFs", pdfs_atuais, pdfs_esperados),
        ("fichamentos publicados", fichas_atuais.get("fichamentos", []), fichas_esperadas.get("fichamentos", [])),
    )
    for nome, atual, esperado in comparacoes:
        if _normalizado(atual) != _normalizado(esperado):
            achados.append(Achado("derivado_desatualizado", f"{nome} difere do estado canônico do cofre", True))

    notas, _ = _notas(cofre)
    ativos = {str(item["codigo"]): item for item in inventario_esperado}
    caminhos_ativos = {str(item["arquivo"]).replace("\\", "/") for item in inventario_esperado}
    for codigo, item in ativos.items():
        nota = notas.get(codigo)
        if not nota:
            achados.append(Achado(
                "fonte_sem_nota", f"{codigo}: fonte ativa ainda não possui nota em Fontes/", False, "pendencia",
            ))
            continue
        valido = _caminho_pdf_valido(cofre, nota["pdf"])
        canonico = str(item["arquivo"]).replace("\\", "/")
        if valido != canonico:
            achados.append(Achado(
                "link_nota_divergente",
                f"{codigo}: link da nota deve apontar para {canonico}",
                True,
            ))

    hashes: dict[str, list[str]] = {}
    raiz_pdf = cofre / "PDF"
    for pdf in raiz_pdf.rglob("*.pdf"):
        rel_pdf = pdf.relative_to(raiz_pdf)
        if any(parte in IGNORAR_PDF for parte in rel_pdf.parts):
            continue
        rel = pdf.relative_to(cofre).as_posix()
        if rel in caminhos_ativos:
            hashes.setdefault(_hash(pdf), []).append(rel)
    for caminhos in hashes.values():
        if len(caminhos) > 1:
            achados.append(Achado(
                "pdf_duplicado", "PDFs com conteúdo idêntico: " + ", ".join(sorted(caminhos)),
                False, "pendencia",
            ))

    # Os PDFs ficam só no cofre. Se algum aparecer dentro do site, é um vazamento.
    if (painel / "PDF").is_dir():
        expostos = sorted(p.relative_to(painel).as_posix() for p in (painel / "PDF").rglob("*") if p.is_file())
        if expostos:
            achados.append(Achado(
                "pdf_no_site", f"{len(expostos)} arquivo(s) dentro de PDF/ do site; PDFs devem ficar só no cofre",
                False, "erro",
            ))

    guardiao = validar_publicacao(painel, cofre)
    for erro in guardiao.erros:
        achados.append(Achado("guardiao", erro, True, "erro"))
    extras = sorted(
        pdf.relative_to(cofre).as_posix()
        for pdf in raiz_pdf.rglob("*.pdf")
        if not any(parte in IGNORAR_PDF for parte in pdf.relative_to(raiz_pdf).parts)
        and pdf.relative_to(cofre).as_posix() not in caminhos_ativos
    )
    if extras:
        amostra = ", ".join(extras[:8])
        sufixo = f" e mais {len(extras) - 8}" if len(extras) > 8 else ""
        achados.append(Achado(
            "pdf_sem_fonte", f"{len(extras)} PDF(s) não vinculados a fonte ativa: {amostra}{sufixo}",
            False, "pendencia",
        ))

    return {
        "ok": not any(a.gravidade == "erro" for a in achados),
        "numeros": {
            "fontes": len(inventario_esperado),
            "pdfs_autorizados": len(pdfs_esperados),
            "fichamentos": len(fichas_esperadas.get("fichamentos", [])),
            "notas_rastreabilidade": sum(codigo not in ativos for codigo in notas),
            "achados": len(achados),
            "corrigiveis": sum(a.corrigivel for a in achados),
            "pendencias_humanas": sum(not a.corrigivel for a in achados),
        },
        "achados": [asdict(a) for a in achados],
    }


def _texto(relatorio: dict) -> str:
    n = relatorio["numeros"]
    linhas = [
        "Auditoria do acervo",
        "  " + " | ".join(f"{k}: {v}" for k, v in n.items()),
    ]
    if not relatorio["achados"]:
        linhas.append("  Nenhuma inconsistência encontrada.")
    for item in relatorio["achados"]:
        marca = "CORRIGÍVEL" if item["corrigivel"] else item["gravidade"].upper()
        linhas.append(f"  {marca}: {item['mensagem']}")
    return "\n".join(linhas)


def _corrigir_links_notas(cofre: Path, painel: Path) -> list[Path]:
    inventario, _pdfs, _fichas, _avisos, _marcas = construir(cofre, painel)
    notas, _ = _notas(cofre)
    alteradas: list[Path] = []
    for item in inventario:
        codigo = str(item["codigo"])
        nota = notas.get(codigo)
        canonico = str(item["arquivo"]).replace("\\", "/")
        if not nota or not _caminho_pdf_valido(cofre, canonico):
            continue
        if _caminho_pdf_valido(cofre, nota["pdf"]) == canonico:
            continue
        caminho = Path(nota["arquivo_nota"])
        texto = nota["texto"]
        linha = f"- **PDF:** [[{canonico}]]"
        novo, trocas = re.subn(r"(?im)^\s*(?:[-*]\s+)?\*\*PDF:\*\*.*$", linha, texto, count=1)
        if not trocas:
            novo, trocas = re.subn(r"(?im)^(##\s+Arquivo\s*)$", rf"\1\n{linha}", texto, count=1)
        if trocas and novo != texto:
            caminho.write_text(novo, encoding="utf-8")
            alteradas.append(caminho)
    return alteradas


def corrigir(cofre: Path, painel: Path, publicar: bool = True) -> dict:
    cofre, painel = Path(cofre).resolve(), Path(painel).resolve()
    antes = auditar(cofre, painel)
    notas_alteradas = _corrigir_links_notas(cofre, painel)
    if sincronizar(cofre, painel, True) != 0:
        raise RuntimeError("O exportador recusou a correção; nenhum derivado foi promovido.")
    depois = auditar(cofre, painel)
    if any(a["gravidade"] == "erro" for a in depois["achados"]):
        raise RuntimeError("A correção não passou na auditoria final.")
    publicacao = None
    if publicar:
        caminhos = list(ARQUIVOS_DERIVADOS)
        publicacao = PublicadorAcervo(cofre, painel).publicar_auditoria(notas_alteradas, caminhos)
    return {
        "antes": antes, "depois": depois, "publicacao": publicacao,
        "notas_corrigidas": [p.name for p in notas_alteradas],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audita e corrige derivados seguros do acervo")
    parser.add_argument("acao", choices=("diagnosticar", "corrigir"))
    parser.add_argument("--cofre", type=Path, default=Path(
        r"C:\Users\rcmin\OneDrive\Documents\Pos-Graduacao\Doutorado UFC\Síndrome de Pandora"
    ))
    parser.add_argument("--painel", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--sem-publicar", action="store_true", help="corrige e testa localmente, sem commit/push")
    args = parser.parse_args(argv)
    try:
        if args.acao == "diagnosticar":
            resultado = auditar(args.cofre, args.painel)
            print(json.dumps(resultado, ensure_ascii=False, indent=2) if args.json else _texto(resultado))
        else:
            resultado = corrigir(args.cofre, args.painel, publicar=not args.sem_publicar)
            if args.json:
                print(json.dumps(resultado, ensure_ascii=False, indent=2))
            else:
                print("Antes da correção:\n" + _texto(resultado["antes"]))
                print("\nDepois da correção:\n" + _texto(resultado["depois"]))
                if resultado["publicacao"]:
                    print(f"\nPublicado no commit {resultado['publicacao']['painel']['commit']}.")
        return 0
    except (OSError, ValueError, RuntimeError, ErroPublicacao) as exc:
        print(f"BLOQUEADO: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
