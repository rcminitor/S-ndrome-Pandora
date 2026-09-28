"""Confere, pela rede, se o GitHub Pages publicou um acervo coerente."""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen


ARQUIVOS = {
    "inventario": ("dados_inventario.js", "DADOS_INVENTARIO"),
    "pdfs": ("dados_pdfs.js", "DADOS_PDFS"),
    "fichamentos": ("dados_fichamentos.js", "DADOS_FICHAMENTOS"),
    "estado": ("dados_estadoarte.js", "ESTADO_ARTE"),
}


def extrair_js(texto: str, variavel: str):
    marcador = f"window.{variavel} ="
    if marcador not in texto:
        raise ValueError(f"variável {variavel} não encontrada")
    conteudo = texto.split(marcador, 1)[1].strip()
    if conteudo.endswith(";"):
        conteudo = conteudo[:-1]
    return json.loads(conteudo)


def validar_dados_publicados(inventario: list[dict], pdfs: list[dict],
                             fich_obj: dict, estado: dict) -> list[str]:
    erros: list[str] = []
    codigos = [str(item.get("codigo", "")).strip() for item in inventario]
    caminhos = [str(item.get("arquivo", "")).replace("\\", "/") for item in inventario]
    manifesto = [str(item.get("arquivo", "")).replace("\\", "/") for item in pdfs]
    codigos_ativos = set(codigos)

    if not inventario:
        erros.append("inventário público vazio")
    if len(codigos) != len(set(codigos)):
        erros.append("códigos duplicados no inventário público")
    if len(caminhos) != len({c.casefold() for c in caminhos}):
        erros.append("PDF usado por mais de uma fonte no inventário público")
    if any(not caminho.startswith("PDF/") for caminho in caminhos):
        erros.append("fonte publicada com arquivo fora de PDF/")
    if set(caminhos) != set(manifesto):
        erros.append("inventário e manifesto público de PDFs divergem")
    if len(inventario) != len(pdfs):
        erros.append("contagem pública de fontes difere da contagem de PDFs")

    fichamentos = fich_obj.get("fichamentos", []) if isinstance(fich_obj, dict) else []
    codigos_fichas = {str(item.get("codigo", "")).strip() for item in fichamentos}
    orfaos_fichas = sorted(codigos_fichas - codigos_ativos)
    if orfaos_fichas:
        erros.append("fichamentos sem PDF ativo: " + ", ".join(orfaos_fichas))

    fontes_estado = estado.get("fontes", []) if isinstance(estado, dict) else []
    codigos_estado = {str(item.get("codigo", "")).strip() for item in fontes_estado}
    orfaos_estado = sorted(codigos_estado - codigos_ativos)
    if orfaos_estado:
        erros.append("Estado da Arte com fontes sem PDF ativo: " + ", ".join(orfaos_estado))
    return erros


def _ler_texto(url: str, timeout: int = 20) -> str:
    req = Request(url, headers={"User-Agent": "guardiao-acervo/1.0", "Cache-Control": "no-cache"})
    with urlopen(req, timeout=timeout) as resposta:
        return resposta.read().decode("utf-8-sig")


def _pdf_disponivel(base: str, caminho: str) -> tuple[str, str | None]:
    url = urljoin(base, quote(caminho, safe="/"))
    req = Request(url, method="HEAD", headers={"User-Agent": "guardiao-acervo/1.0"})
    try:
        with urlopen(req, timeout=20) as resposta:
            if resposta.status != 200:
                return caminho, f"HTTP {resposta.status}"
            tipo = resposta.headers.get_content_type()
            if tipo not in {"application/pdf", "application/octet-stream"}:
                return caminho, f"tipo inesperado: {tipo}"
    except (HTTPError, URLError, TimeoutError) as exc:
        return caminho, str(exc)
    return caminho, None


def verificar(base: str) -> dict:
    base = base.rstrip("/") + "/"
    selo = str(int(time.time() * 1000))
    dados = {}
    for chave, (arquivo, variavel) in ARQUIVOS.items():
        texto = _ler_texto(urljoin(base, arquivo) + f"?v={selo}")
        dados[chave] = extrair_js(texto, variavel)

    erros = validar_dados_publicados(
        dados["inventario"], dados["pdfs"], dados["fichamentos"], dados["estado"]
    )
    caminhos = [str(item["arquivo"]).replace("\\", "/") for item in dados["pdfs"]]
    with ThreadPoolExecutor(max_workers=12) as executor:
        resultados = executor.map(lambda caminho: _pdf_disponivel(base, caminho), caminhos)
    indisponiveis = [f"{caminho} ({erro})" for caminho, erro in resultados if erro]
    if indisponiveis:
        erros.append("PDFs indisponíveis na rede: " + "; ".join(indisponiveis))
    return {
        "fontes": len(dados["inventario"]),
        "pdfs": len(dados["pdfs"]),
        "fichamentos": len(dados["fichamentos"].get("fichamentos", [])),
        "estado_da_arte": len(dados["estado"].get("fontes", [])),
        "erros": erros,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Valida o acervo servido pelo GitHub Pages")
    parser.add_argument("--url", required=True, help="URL base publicada pelo GitHub Pages")
    parser.add_argument("--tentativas", type=int, default=12)
    parser.add_argument("--intervalo", type=float, default=5)
    args = parser.parse_args(argv)

    ultimo_erro = ""
    for tentativa in range(1, max(1, args.tentativas) + 1):
        try:
            resultado = verificar(args.url)
            if not resultado["erros"]:
                print(
                    "Site publicado aprovado: "
                    f"{resultado['fontes']} fontes | {resultado['pdfs']} PDFs | "
                    f"{resultado['fichamentos']} fichamentos | "
                    f"{resultado['estado_da_arte']} no Estado da Arte"
                )
                return 0
            ultimo_erro = " | ".join(resultado["erros"])
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            ultimo_erro = str(exc)
        print(f"Tentativa {tentativa}/{args.tentativas}: {ultimo_erro}", file=sys.stderr)
        if tentativa < args.tentativas:
            time.sleep(max(0, args.intervalo))
    print(f"Site publicado reprovado: {ultimo_erro}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
