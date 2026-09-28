"""Inclusão segura de uma nova fonte com PDF no acervo.

O PDF e a nota de fonte nascem juntos. A inclusão só permanece no cofre quando
o exportador transacional e o Guardião aprovam o conjunto inteiro.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import uuid
from pathlib import Path

import pymupdf

from guardiao_acervo import ler_json_js
from sincronizar_acervo import sincronizar


TRAVA_ADICAO = threading.Lock()
LIMITE_BYTES = 100 * 1024 * 1024
CODIGO = re.compile(r"^[A-Z]{0,3}\d{1,4}$")
INVALIDOS_WINDOWS = re.compile(r'[\\/:*?"<>|#^\[\]]')


class ErroAdicao(ValueError):
    def __init__(self, mensagem: str, status: int = 400):
        super().__init__(mensagem)
        self.status = status


def _campo(dados, nome: str) -> str:
    return str(dados.get(nome, "") or "").strip()


def _yaml(valor: str) -> str:
    return json.dumps(valor, ensure_ascii=False)


def _nome_seguro(nome: str, limite: int = 120) -> str:
    nome = Path(nome.replace("\\", "/")).name
    nome = INVALIDOS_WINDOWS.sub(" ", nome)
    nome = re.sub(r"\s+", " ", nome).strip(" .")
    return nome[:limite].rstrip(" .")


def _hash(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as entrada:
        for bloco in iter(lambda: entrada.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def _nota(codigo: str, titulo: str, ano: str, nucleo: str, fase: str,
          tema: str, tipo_documento: str, referencia: str, caminho_pdf: str) -> str:
    ref = (
        f"> {referencia}\n\n"
        "*Procedência:* informada no cadastro pelo painel — ⚠️ **A CONFERIR no artigo**."
        if referencia else
        "❌ **sem procedência** — montar somente depois da conferência no PDF original."
    )
    tag_nucleo = "nucleo/1" if nucleo == "Núcleo 1" else "nucleo/2" if nucleo == "Núcleo 2" else "nucleo/a-classificar"
    return f'''---
codigo: {_yaml(codigo)}
ano: {_yaml(ano or "NÃO CONFIRMADO")}
titulo: {_yaml(titulo)}
nucleo: {_yaml(nucleo)}
fase: {_yaml(fase)}
status: "arquivo obtido"
tema: {_yaml(tema or "A classificar")}
tipo_documento: {_yaml(tipo_documento)}
tipo_de_estudo: "NÃO CONFIRMADO"
origem_do_registro: "adicionado pelo painel"
tags:
  - fonte
  - {tag_nucleo}
  - status/arquivo-obtido
---
# {titulo}

> [!info] Identificação
> **Código:** {codigo} · **Ano:** {ano or "NÃO CONFIRMADO"} · **Núcleo:** {nucleo} · **Fase:** {fase}
> **Tipo de documento:** {tipo_documento} · **Status:** arquivo obtido

## Arquivo
- **PDF:** [[{caminho_pdf}]]
- **Fichamento:** ainda não realizado

## Referência (ABNT)
{ref}

## Por que ler
NÃO CONFIRMADO — classificar após a leitura do PDF.

## Como usar na tese
NÃO CONFIRMADO — definir após a leitura do PDF.

## Cautelas
PDF incluído pelo painel; conteúdo, método e referência ainda precisam ser conferidos no documento original.

## Tipo de estudo
NÃO CONFIRMADO.

## Minhas notas de leitura
<!-- Regra do acervo: nada de número, página ou resultado sem conferir no PDF. -->

## Ligações
- Núcleo e fila: classificar após a primeira leitura.
'''


class AdicionadorPDF:
    def __init__(self, cofre: Path, painel: Path, sincronizar_fn=sincronizar):
        self.cofre = Path(cofre)
        self.painel = Path(painel)
        self.sincronizar = sincronizar_fn

    def _validar_dados(self, arquivo, dados) -> dict[str, str]:
        if arquivo is None or not getattr(arquivo, "filename", ""):
            raise ErroAdicao("Selecione um arquivo PDF.")
        nome = _nome_seguro(arquivo.filename)
        if not nome or Path(nome).suffix.casefold() != ".pdf":
            raise ErroAdicao("O arquivo precisa ter extensão .pdf.")
        codigo = _campo(dados, "codigo").upper().removeprefix("#")
        if not CODIGO.fullmatch(codigo):
            raise ErroAdicao("Código inválido. Use número ou prefixo com número, como 68, N46 ou S12.")
        titulo = _campo(dados, "titulo")
        if len(titulo) < 5:
            raise ErroAdicao("Informe o título completo da fonte.")
        ano = _campo(dados, "ano")
        if ano and not re.fullmatch(r"\d{4}", ano):
            raise ErroAdicao("O ano deve ter quatro dígitos ou ficar vazio como NÃO CONFIRMADO.")
        nucleo = _campo(dados, "nucleo") or "A classificar"
        if nucleo not in {"Núcleo 1", "Núcleo 2", "A classificar"}:
            raise ErroAdicao("Núcleo inválido.")
        fase = _campo(dados, "fase") or "A classificar"
        if fase not in {"Ler primeiro", "Ler depois", "A classificar"}:
            raise ErroAdicao("Fase inválida.")
        tipo = _campo(dados, "tipo_documento") or "Artigo"
        if tipo not in {"Artigo", "TCC"}:
            raise ErroAdicao("O Acervo aceita somente artigo ou TCC.")
        return {
            "nome": nome, "codigo": codigo, "titulo": titulo, "ano": ano,
            "nucleo": nucleo, "fase": fase, "tipo_documento": tipo,
            "tema": _campo(dados, "tema"), "referencia": _campo(dados, "referencia"),
        }

    def _validar_pdf(self, caminho: Path) -> None:
        tamanho = caminho.stat().st_size
        if tamanho == 0 or tamanho > LIMITE_BYTES:
            raise ErroAdicao("PDF vazio ou maior que 100 MB.")
        with caminho.open("rb") as entrada:
            cabecalho = entrada.read(5)
        if cabecalho != b"%PDF-":
            raise ErroAdicao("O arquivo enviado não possui cabeçalho de PDF válido.")
        try:
            with pymupdf.open(caminho) as doc:
                if doc.page_count < 1:
                    raise ErroAdicao("O PDF não contém páginas.")
        except ErroAdicao:
            raise
        except Exception as exc:
            raise ErroAdicao(f"O PDF está corrompido ou não pôde ser aberto: {exc}") from exc

    def _checar_duplicatas(self, codigo: str, temporario: Path) -> None:
        for nota in (self.cofre / "Fontes").glob("*.md"):
            texto = nota.read_text(encoding="utf-8", errors="replace")
            if re.search(rf'^codigo:\s*["\']?{re.escape(codigo)}["\']?\s*$', texto, re.M | re.I):
                raise ErroAdicao(f"O código {codigo} já existe no acervo.", 409)
        novo_hash = _hash(temporario)
        for existente in (self.cofre / "PDF").rglob("*.pdf"):
            if existente.is_file() and existente.stat().st_size == temporario.stat().st_size:
                if _hash(existente) == novo_hash:
                    rel = existente.relative_to(self.cofre).as_posix()
                    raise ErroAdicao(f"Este PDF já existe no acervo: {rel}", 409)

    def adicionar(self, arquivo, dados, origem_movel: Path | None = None) -> dict:
        valores = self._validar_dados(arquivo, dados)
        destino_dir = self.cofre / "PDF" / "A_classificar"
        fontes_dir = self.cofre / "Fontes"
        if not fontes_dir.is_dir():
            raise ErroAdicao("O cofre Obsidian não está disponível no computador.", 503)
        destino_dir.mkdir(parents=True, exist_ok=True)
        destino_pdf = destino_dir / valores["nome"]
        titulo_nota = _nome_seguro(f'{valores["codigo"]} {valores["titulo"]}', 68)
        destino_nota = fontes_dir / f"{titulo_nota}.md"
        temporario = destino_dir / f".upload-{uuid.uuid4().hex}.tmp"

        with TRAVA_ADICAO:
            if destino_pdf.exists() or destino_nota.exists():
                raise ErroAdicao("Já existe um PDF ou uma nota com esse nome. Nada foi sobrescrito.", 409)
            origem_movel = Path(origem_movel).resolve() if origem_movel else None
            if origem_movel:
                origem_movel.replace(temporario)
            else:
                arquivo.save(temporario)
            criou_pdf = criou_nota = False
            try:
                self._validar_pdf(temporario)
                self._checar_duplicatas(valores["codigo"], temporario)
                rel_pdf = destino_pdf.relative_to(self.cofre).as_posix()
                conteudo_nota = _nota(caminho_pdf=rel_pdf, **{k: valores[k] for k in (
                    "codigo", "titulo", "ano", "nucleo", "fase", "tema", "tipo_documento", "referencia")})
                with destino_nota.open("x", encoding="utf-8") as saida:
                    saida.write(conteudo_nota)
                criou_nota = True
                temporario.replace(destino_pdf)
                criou_pdf = True
                if self.sincronizar(self.cofre, self.painel, True) != 0:
                    raise ErroAdicao("O Guardião recusou a inclusão; nenhuma fonte foi adicionada.", 422)
            except Exception:
                if criou_nota and destino_nota.exists():
                    destino_nota.unlink()
                if criou_pdf and destino_pdf.exists():
                    if origem_movel:
                        destino_pdf.replace(origem_movel)
                    else:
                        destino_pdf.unlink()
                elif origem_movel and temporario.exists():
                    temporario.replace(origem_movel)
                raise
            finally:
                temporario.unlink(missing_ok=True)

        inventario = ler_json_js(self.painel / "dados_inventario.js", "DADOS_INVENTARIO")
        pdfs = ler_json_js(self.painel / "dados_pdfs.js", "DADOS_PDFS")
        item = next(a for a in inventario if str(a.get("codigo")) == valores["codigo"])
        pdf = next(p for p in pdfs if p.get("arquivo") == rel_pdf)
        return {"item": item, "pdf": pdf, "nota": destino_nota.name, "arquivo": rel_pdf}
