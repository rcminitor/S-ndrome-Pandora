"""Exportador transacional do cofre Obsidian para o painel.

Compatibilidade e deliberada: os registros publicados continuam sendo a linha de
base durante a migracao. Notas antigas com caminhos obsoletos nunca apagam um
registro valido. Uma fonte nova so entra quando sua nota aponta para um PDF real
dentro de PDF/. A escrita ocorre apenas depois da validacao integral.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from fichamentos import ler_fichamentos
from guardiao_acervo import ler_json_js, validar_dados


IGNORAR_PDF = {"_Versoes_a_comparar", "_Duplicatas_confirmadas", "IA"}


def _frontmatter(texto: str) -> dict[str, str]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", texto, re.S)
    if not m:
        return {}
    campos: dict[str, str] = {}
    for linha in m.group(1).splitlines():
        achou = re.match(r"^([\w_]+):\s*(.*?)\s*$", linha)
        if achou:
            campos[achou.group(1)] = achou.group(2).strip().strip('"').strip("'")
    return campos


def _secao(texto: str, titulo: str) -> str:
    m = re.search(rf"(?ims)^##\s+[^\n]*{re.escape(titulo)}[^\n]*\n(.*?)(?=^##\s+|\Z)", texto)
    if not m:
        return ""
    return re.sub(r"<!--.*?-->", "", m.group(1), flags=re.S).strip()


def _limpar_markdown(texto: str) -> str:
    linhas = []
    for linha in texto.splitlines():
        linha = re.sub(r"^\s*>\s?", "", linha)
        linha = re.sub(r"^\s*[-*]\s+", "", linha)
        linha = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", linha)
        linha = re.sub(r"\[\[([^\]]+)\]\]", r"\1", linha)
        linha = linha.replace("**", "").replace("__", "").strip()
        if linha and not linha.startswith("<!--"):
            linhas.append(linha)
    return " ".join(linhas)


def _referencia(texto: str) -> str:
    m = re.search(r"(?ims)^##\s+[^\n]*Refer[\u00eae]ncia[^\n]*\n(.*?)(?=^##\s+|\Z)", texto)
    secao = m.group(1).strip() if m else ""
    for linha in secao.splitlines():
        limpa = _limpar_markdown(linha)
        if limpa and not limpa.casefold().startswith("proced"):
            return limpa
    return ""


def _procedencia(texto: str) -> str:
    m = re.search(r"(?im)^\*?Proced[\u00eae]ncia:\*?\s*(.+)$", texto)
    return _limpar_markdown(m.group(1)) if m else "extraida da nota de fonte; conferir marca de procedencia"


def _pdf_da_nota(texto: str) -> str:
    m = re.search(r"\*\*PDF:\*\*\s*\[\[([^\]|#]+\.pdf)", texto, re.I)
    return m.group(1).strip().replace("\\", "/") if m else ""


def _normalizar_nucleo(valor: str) -> str:
    if "1" in valor:
        return "Núcleo 1"
    if "2" in valor:
        return "Núcleo 2"
    return valor or "A classificar"


def _caminho_pdf_valido(cofre: Path, caminho: str) -> str:
    if not caminho.startswith("PDF/"):
        return ""
    alvo = (cofre / Path(caminho)).resolve()
    raiz_pdf = (cofre / "PDF").resolve()
    try:
        alvo.relative_to(raiz_pdf)
    except ValueError:
        return ""
    return alvo.relative_to(cofre).as_posix() if alvo.is_file() else ""


def _notas(cofre: Path) -> tuple[dict[str, dict], dict[str, int]]:
    saida: dict[str, dict] = {}
    marcas: dict[str, int] = {}
    for arq in sorted((cofre / "Fontes").glob("*.md")):
        texto = arq.read_text(encoding="utf-8")
        fm = _frontmatter(texto)
        codigo = fm.get("codigo", "").strip()
        if not codigo:
            continue
        if codigo in saida:
            raise ValueError(f"codigo duplicado nas notas de fonte: {codigo}")
        saida[codigo] = {"arquivo_nota": arq, "texto": texto, "fm": fm, "pdf": _pdf_da_nota(texto)}
        marcas[str(arq)] = arq.stat().st_mtime_ns
    return saida, marcas


def _manifesto_pdfs(cofre: Path) -> tuple[list[dict], dict[str, int]]:
    raiz_pdf = cofre / "PDF"
    itens: list[dict] = []
    marcas: dict[str, int] = {}
    for arq in sorted(raiz_pdf.rglob("*.pdf"), key=lambda p: p.as_posix().casefold()):
        rel_local = arq.relative_to(raiz_pdf)
        if any(parte in IGNORAR_PDF for parte in rel_local.parts):
            continue
        rel = arq.relative_to(cofre).as_posix()
        itens.append({"pasta": Path(rel).parent.as_posix(), "nome": arq.stem,
                      "arquivo": rel, "kb": round(arq.stat().st_size / 1024)})
        marcas[str(arq)] = arq.stat().st_mtime_ns
    return itens, marcas


def _item_novo(codigo: str, nota: dict, fichamento: str) -> dict:
    fm, texto = nota["fm"], nota["texto"]
    return {
        "fase": fm.get("fase", "A classificar"),
        "fichamento": fichamento,
        "cautelas": _limpar_markdown(_secao(texto, "Cautelas")) or "NÃO CONFIRMADO",
        "codigo": codigo,
        "grupo": fm.get("tema", "NÃO CONFIRMADO"),
        "tipoEstudo": fm.get("tipo_de_estudo", "NÃO CONFIRMADO"),
        "procedencia": _procedencia(texto),
        "porQueLer": _limpar_markdown(_secao(texto, "Por que ler")) or "NÃO CONFIRMADO",
        "comoUsar": _limpar_markdown(_secao(texto, "Como usar")) or "NÃO CONFIRMADO",
        "arquivo": nota["pdf_valido"],
        "referencia": _referencia(texto) or "NÃO CONFIRMADO",
        "status": fm.get("status", "arquivo obtido"),
        "ano": fm.get("ano", "NÃO CONFIRMADO"),
        "titulo": fm.get("titulo", "NÃO CONFIRMADO"),
        "nucleo": _normalizar_nucleo(fm.get("nucleo", "")),
    }


def construir(cofre: Path, painel: Path) -> tuple[list[dict], list[dict], dict, list[str], dict[str, int]]:
    inventario = ler_json_js(painel / "dados_inventario.js", "DADOS_INVENTARIO")
    fich_atual = ler_json_js(painel / "dados_fichamentos.js", "DADOS_FICHAMENTOS")
    notas, marcas_notas = _notas(cofre)
    pdfs, marcas_pdfs = _manifesto_pdfs(cofre)
    fichamentos = ler_fichamentos(cofre)
    fich_por_codigo = {str(f["codigo"]): f["arquivo"] for f in fichamentos}
    avisos: list[str] = []
    for nota in notas.values():
        nota["pdf_valido"] = _caminho_pdf_valido(cofre, nota["pdf"])

    por_codigo = {str(a["codigo"]): dict(a) for a in inventario}
    ordem = [str(a["codigo"]) for a in inventario]
    for codigo in ordem:
        item = por_codigo[codigo]
        nota = notas.get(codigo)
        if nota:
            atual_valido = _caminho_pdf_valido(cofre, str(item.get("arquivo", "")))
            if not atual_valido and nota["pdf_valido"]:
                item["arquivo"] = nota["pdf_valido"]
            elif nota["pdf"] and nota["pdf_valido"] != atual_valido:
                avisos.append(f"{codigo}: link divergente na nota ignorado; mantido {item.get('arquivo')}")
        else:
            avisos.append(f"{codigo}: registro publicado ainda nao possui nota em Fontes/")
        if codigo in fich_por_codigo and not item.get("fichamento"):
            item["fichamento"] = fich_por_codigo[codigo]
        elif not item.get("fichamento"):
            item["fichamento"] = ""

    for codigo, nota in notas.items():
        if codigo in por_codigo:
            continue
        if not nota["pdf_valido"]:
            avisos.append(f"{codigo}: nao publicado porque nao possui PDF valido dentro de PDF/")
            continue
        por_codigo[codigo] = _item_novo(codigo, nota, fich_por_codigo.get(codigo, ""))
        ordem.append(codigo)
        avisos.append(f"{codigo}: nova fonte pronta para inclusao")

    inventario_novo = [por_codigo[c] for c in ordem]
    conteudo_fichas = {"atualizado": fich_atual.get("atualizado", ""), "fichamentos": fichamentos}
    if fichamentos != fich_atual.get("fichamentos", []):
        conteudo_fichas["atualizado"] = datetime.now().isoformat(timespec="minutes")
    return inventario_novo, pdfs, conteudo_fichas, avisos, {**marcas_notas, **marcas_pdfs}


def _js(variavel: str, valor, cabecalho: str = "", indent: int = 1) -> str:
    prefixo = (cabecalho.rstrip() + "\n") if cabecalho else ""
    return prefixo + f"window.{variavel} = " + json.dumps(valor, ensure_ascii=False, indent=indent) + ";\n"


def _hash_curto(conteudo: str) -> str:
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()[:10]


def _index_com_versoes(texto: str, conteudos: dict[str, str]) -> str:
    for nome in ("dados_pdfs.js", "dados_inventario.js", "dados_fichamentos.js"):
        versao = _hash_curto(conteudos[nome])
        texto = re.sub(rf'(<script\s+src="{re.escape(nome)})(?:\?v=[^"]*)?("\s*></script>)',
                       rf'\1?v={versao}\2', texto)
    return texto


def _mesmas_marcas(marcas: dict[str, int]) -> list[str]:
    mudaram = []
    for nome, marca in marcas.items():
        arq = Path(nome)
        if not arq.exists() or arq.stat().st_mtime_ns != marca:
            mudaram.append(nome)
    return mudaram


def sincronizar(cofre: Path, painel: Path, escrever: bool = False) -> int:
    cofre, painel = cofre.resolve(), painel.resolve()
    inventario, pdfs, fich_obj, avisos, marcas = construir(cofre, painel)
    caminhos_pdf = {p["arquivo"] for p in pdfs}

    def existe(caminho: str) -> bool:
        return caminho in caminhos_pdf and (cofre / caminho).is_file()

    def cabecalho(caminho: str) -> bytes:
        with (cofre / caminho).open("rb") as entrada:
            return entrada.read(5)

    rel = validar_dados(inventario, pdfs, fich_obj["fichamentos"], existe, cabecalho)
    rel.avisos.extend(avisos)
    print(rel.texto())
    if not rel.ok:
        print("Nenhum arquivo foi alterado.")
        return 1

    conteudos = {
        "dados_inventario.js": _js("DADOS_INVENTARIO", inventario, indent=4),
        "dados_pdfs.js": _js("DADOS_PDFS", pdfs, "// Gerado pelo exportador transacional do acervo"),
        "dados_fichamentos.js": _js("DADOS_FICHAMENTOS", fich_obj,
            "// Gerado pelo Painel de Estudo (painel_local/fichamentos.py) a partir de Fichamentos\\ do cofre."),
    }
    index_atual = (painel / "index.html").read_text(encoding="utf-8")
    conteudos["index.html"] = _index_com_versoes(index_atual, conteudos)
    alterados = [nome for nome, valor in conteudos.items()
                 if not (painel / nome).exists() or (painel / nome).read_text(encoding="utf-8-sig") != valor]
    faltam_pdf = [p["arquivo"] for p in pdfs if not (painel / p["arquivo"]).is_file() or
                  (painel / p["arquivo"]).stat().st_size != (cofre / p["arquivo"]).stat().st_size]
    print(f"Plano: {len(alterados)} arquivos de dados | {len(faltam_pdf)} PDFs para sincronizar")
    if not escrever:
        print("Modo de conferencia: nenhuma alteracao realizada. Use --write para aplicar.")
        return 0
    mudaram = _mesmas_marcas(marcas)
    if mudaram:
        print("BLOQUEADO: o OneDrive/cofre mudou durante a exportacao:")
        print("\n".join(f"  {m}" for m in mudaram[:10]))
        return 1

    with tempfile.TemporaryDirectory(prefix="pandora-export-", dir=painel) as tmp_nome:
        tmp = Path(tmp_nome)
        for nome, valor in conteudos.items():
            (tmp / nome).write_text(valor, encoding="utf-8")
        for caminho in faltam_pdf:
            destino_tmp = tmp / caminho
            destino_tmp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(cofre / caminho, destino_tmp)
        if _mesmas_marcas(marcas):
            print("BLOQUEADO: o cofre mudou antes da promocao final; nada foi substituido.")
            return 1
        for caminho in faltam_pdf:
            destino = painel / caminho
            destino.parent.mkdir(parents=True, exist_ok=True)
            os.replace(tmp / caminho, destino)
        for nome in alterados:
            os.replace(tmp / nome, painel / nome)
    print("Exportacao concluida de forma transacional.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sincroniza cofre e painel com validacao previa")
    parser.add_argument("--cofre", required=True, type=Path)
    parser.add_argument("--painel", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--write", action="store_true", help="aplica a exportacao aprovada")
    args = parser.parse_args(argv)
    return sincronizar(args.cofre, args.painel, args.write)


if __name__ == "__main__":
    raise SystemExit(main())
