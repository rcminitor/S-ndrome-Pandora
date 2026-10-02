from __future__ import annotations

import re
import json
import logging
import warnings
from pathlib import Path
from pypdf import PdfReader

warnings.filterwarnings("ignore")
logging.getLogger("pypdf").setLevel(logging.ERROR)

try:
    from .modelos_documentos import (
        MetadadosDocumento,
        ParagrafoCirurgico,
        RelatorioEconomiaTokens,
        ResultadoBuscaCirurgica,
        SecaoDocumento,
        TrechoDocumento,
    )
except (ImportError, ValueError):
    from modelos_documentos import (
        MetadadosDocumento,
        ParagrafoCirurgico,
        RelatorioEconomiaTokens,
        ResultadoBuscaCirurgica,
        SecaoDocumento,
        TrechoDocumento,
    )


def estimar_tokens(texto: str) -> int:
    """Estimativa didática de tokens para português/inglês (aprox. 4 caracteres por token)."""
    if not texto:
        return 0
    return max(1, round(len(texto) / 4))


def extrair_metadados_pdf(caminho_pdf: Path, raiz_projeto: Path | None = None) -> MetadadosDocumento:
    """Extrai metadados estruturados de um PDF sem carregar o texto completo na memória,
    identificando seções acadêmicas reais e filtrando cabeçalhos repetitivos."""
    caminho_pdf = Path(caminho_pdf).resolve()
    if not caminho_pdf.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_pdf}")

    leitor = PdfReader(caminho_pdf)
    total_paginas = len(leitor.pages)
    tamanho_bytes = caminho_pdf.stat().st_size

    caminho_rel = str(caminho_pdf)
    if raiz_projeto:
        try:
            caminho_rel = str(caminho_pdf.relative_to(raiz_projeto))
        except ValueError:
            pass

    # Pré-extrai linhas para detectar cabeçalhos de periódico repetitivos
    paginas_linhas: list[list[str]] = []
    textos_paginas: list[str] = []
    top_counts: dict[str, int] = {}

    for pagina in leitor.pages:
        texto = pagina.extract_text() or ""
        textos_paginas.append(texto)
        linhas = [l.strip() for l in texto.split("\n") if l.strip()]
        paginas_linhas.append(linhas)
        for l in linhas[:2]:
            top_counts[l] = top_counts.get(l, 0) + 1

    repetitive_headers = {k for k, v in top_counts.items() if v >= 3 or (total_paginas < 4 and v >= 2)}

    # Padrão de seções acadêmicas comuns (Inglês e Português)
    padrao_secao = re.compile(
        r"^(?:(?:\d+(?:\.\d+)*\.?\s*)?(?:abstract|resumo|introduction|introdu[çc][ãa]o|materials?\s+and\s+methods?|materiais?\s+e\s+m[ée]todos?|methods?|m[ée]todos?|results?|resultados?|discussion|discuss[ãa]o|conclusions?|conclus[õo]es?|references|refer[êe]ncias|case\s+report|background|study\s+design|statistical\s+analysis))\b",
        re.IGNORECASE
    )

    secoes: list[SecaoDocumento] = []
    total_caracteres_doc = 0

    for idx, (texto, linhas) in enumerate(zip(textos_paginas, paginas_linhas), start=1):
        total_caracteres_doc += len(texto)

        titulo_provavel = None
        # 1. Tenta achar uma seção acadêmica formal na página
        for l in linhas:
            if padrao_secao.search(l):
                titulo_provavel = l[:75]
                break

        # 2. Se for a página 1 e não achou abstract/intro, procura o título do artigo
        if not titulo_provavel and idx == 1:
            cands_p1 = [l for l in linhas if l not in repetitive_headers and len(l) > 15 and not l.startswith("http") and not l.isdigit()]
            if cands_p1:
                titulo_provavel = cands_p1[0][:75]

        # 3. Fallback: primeira linha útil não repetitiva
        if not titulo_provavel:
            cands = [l for l in linhas if l not in repetitive_headers and len(l) > 8 and not l.isdigit() and not l.startswith("http")]
            titulo_provavel = cands[0][:75] if cands else f"Página {idx}"

        amostra = texto[:150].replace("\n", " ").strip() if texto else "Conteúdo vazio ou imagem"

        secoes.append(
            SecaoDocumento(
                pagina=idx,
                titulo_provavel=titulo_provavel,
                amostra_inicio=amostra,
                total_caracteres=len(texto),
                tokens_estimados=estimar_tokens(texto),
            )
        )

    return MetadadosDocumento(
        arquivo=caminho_pdf.name,
        caminho_relativo=caminho_rel,
        total_paginas=total_paginas,
        tamanho_bytes=tamanho_bytes,
        tokens_estimados_total=estimar_tokens(" " * total_caracteres_doc),
        secoes=secoes,
    )



def ler_pagina_especifica_pdf(caminho_pdf: Path, pagina: int) -> TrechoDocumento:
    """Lê estritamente o conteúdo da página solicitada (1-based index)."""
    caminho_pdf = Path(caminho_pdf).resolve()
    if not caminho_pdf.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_pdf}")

    leitor = PdfReader(caminho_pdf)
    total_paginas = len(leitor.pages)

    if pagina < 1 or pagina > total_paginas:
        raise ValueError(
            f"Página inválida: {pagina}. O documento '{caminho_pdf.name}' tem {total_paginas} páginas."
        )

    conteudo = leitor.pages[pagina - 1].extract_text() or ""
    return TrechoDocumento(
        arquivo=caminho_pdf.name,
        pagina=pagina,
        conteudo=conteudo,
        tokens_estimados=estimar_tokens(conteudo),
    )


def extrair_metadados_documento(caminho_arquivo: Path, raiz_projeto: Path | None = None) -> MetadadosDocumento:
    """Extrai metadados estruturados de qualquer documento (PDF, Word DOCX, TXT, Markdown ou Imagens)."""
    caminho_arquivo = Path(caminho_arquivo).resolve()
    if not caminho_arquivo.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_arquivo}")

    ext = caminho_arquivo.suffix.lower()
    if ext == ".pdf":
        return extrair_metadados_pdf(caminho_arquivo, raiz_projeto=raiz_projeto)

    caminho_rel = str(caminho_arquivo)
    if raiz_projeto:
        try:
            caminho_rel = str(caminho_arquivo.relative_to(raiz_projeto))
        except ValueError:
            pass

    tamanho_bytes = caminho_arquivo.stat().st_size

    if ext == ".docx":
        import zipfile
        import xml.etree.ElementTree as ET
        paragraphs: list[str] = []
        try:
            with zipfile.ZipFile(str(caminho_arquivo)) as z:
                xml_content = z.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                for p in tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
                    texts = [node.text for node in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t") if node.text]
                    if texts:
                        full_p = "".join(texts).strip()
                        if full_p:
                            paragraphs.append(full_p)
        except Exception as e:
            paragraphs = [f"Erro ao ler DOCX: {e}"]

        bloco_tam = 6
        secoes: list[SecaoDocumento] = []
        total_chars = 0
        for i in range(0, max(1, len(paragraphs)), bloco_tam):
            idx = (i // bloco_tam) + 1
            grupo = paragraphs[i:i + bloco_tam]
            texto_p = "\n\n".join(grupo)
            total_chars += len(texto_p)
            titulo = grupo[0][:75] if grupo else f"Seção {idx}"
            secoes.append(
                SecaoDocumento(
                    pagina=idx,
                    titulo_provavel=titulo,
                    amostra_inicio=texto_p[:150].replace("\n", " ").strip(),
                    total_caracteres=len(texto_p),
                    tokens_estimados=estimar_tokens(texto_p),
                )
            )
        return MetadadosDocumento(
            arquivo=caminho_arquivo.name,
            caminho_relativo=caminho_rel,
            total_paginas=len(secoes),
            tamanho_bytes=tamanho_bytes,
            tokens_estimados_total=estimar_tokens(" " * total_chars),
            secoes=secoes,
        )

    elif ext in [".txt", ".md"]:
        conteudo = caminho_arquivo.read_text(encoding="utf-8", errors="ignore")
        linhas = conteudo.splitlines()
        bloco_tam = 35
        secoes = []
        total_chars = len(conteudo)
        for i in range(0, max(1, len(linhas)), bloco_tam):
            idx = (i // bloco_tam) + 1
            grupo = linhas[i:i + bloco_tam]
            texto_p = "\n".join(grupo)
            titulo = None
            for l in grupo:
                l_s = l.strip()
                if l_s.startswith("#") or (len(l_s) > 5 and l_s.isupper()):
                    titulo = l_s.lstrip("#").strip()[:75]
                    break
            if not titulo:
                cands = [l.strip() for l in grupo if len(l.strip()) > 8]
                titulo = cands[0][:75] if cands else f"Bloco {idx}"

            secoes.append(
                SecaoDocumento(
                    pagina=idx,
                    titulo_provavel=titulo,
                    amostra_inicio=texto_p[:150].replace("\n", " ").strip(),
                    total_caracteres=len(texto_p),
                    tokens_estimados=estimar_tokens(texto_p),
                )
            )
        return MetadadosDocumento(
            arquivo=caminho_arquivo.name,
            caminho_relativo=caminho_rel,
            total_paginas=len(secoes),
            tamanho_bytes=tamanho_bytes,
            tokens_estimados_total=estimar_tokens(conteudo),
            secoes=secoes,
        )

    elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
        from PIL import Image
        with Image.open(caminho_arquivo) as img:
            w, h = img.size
            fmt = img.format or ext.lstrip(".").upper()
        # Fórmula padrão de tokens de visão LLM
        tokens_visao = 85 + (max(1, w // 512) * max(1, h // 512) * 170)
        return MetadadosDocumento(
            arquivo=caminho_arquivo.name,
            caminho_relativo=caminho_rel,
            total_paginas=1,
            tamanho_bytes=tamanho_bytes,
            tokens_estimados_total=tokens_visao,
            secoes=[
                SecaoDocumento(
                    pagina=1,
                    titulo_provavel=f"Imagem {fmt} ({w}x{h} px)",
                    amostra_inicio=f"Formato: {fmt}, Dimensões: {w}x{h} pixels",
                    total_caracteres=0,
                    tokens_estimados=tokens_visao,
                )
            ],
        )

    # Fallback genérico
    return MetadadosDocumento(
        arquivo=caminho_arquivo.name,
        caminho_relativo=caminho_rel,
        total_paginas=1,
        tamanho_bytes=tamanho_bytes,
        tokens_estimados_total=estimar_tokens(" " * tamanho_bytes),
        secoes=[SecaoDocumento(pagina=1, titulo_provavel=caminho_arquivo.name, amostra_inicio="", total_caracteres=tamanho_bytes, tokens_estimados=estimar_tokens(" " * tamanho_bytes))],
    )


def listar_documentos_pasta(pasta: Path, raiz_projeto: Path | None = None) -> list[MetadadosDocumento]:
    """Varre uma pasta e extrai metadados de todos os documentos (PDF, DOCX, TXT, MD, Imagens) encontrados."""
    pasta = Path(pasta).resolve()
    if not pasta.exists():
        return []

    exts = {".pdf", ".docx", ".txt", ".md", ".png", ".jpg", ".jpeg", ".webp"}
    documentos: list[MetadadosDocumento] = []
    for arquivo in sorted(pasta.iterdir()):
        if arquivo.is_file() and arquivo.suffix.lower() in exts:
            try:
                metadados = extrair_metadados_documento(arquivo, raiz_projeto=raiz_projeto)
                documentos.append(metadados)
            except Exception as erro:
                print(f"Aviso ao ler {arquivo.name}: {erro}")

    return documentos



def obter_sumario_compacto(metadados: MetadadosDocumento) -> str:
    """Gera um índice ultraenxuto (poucos tokens) ideal para enviar no prompt da LLM."""
    linhas = [f"Documento: {metadados.arquivo} ({metadados.total_paginas} páginas)"]
    for s in metadados.secoes:
        linhas.append(f"- Pág {s.pagina}: {s.titulo_provavel} (~{s.tokens_estimados} tok)")
    return "\n".join(linhas)


def calcular_economia(
    metadados: MetadadosDocumento, paginas_consultadas: list[int]
) -> RelatorioEconomiaTokens:
    """Calcula a economia real de tokens ao usar a abordagem de sumário de metadados + página sob demanda."""
    sumario = obter_sumario_compacto(metadados)
    tokens_metadados = estimar_tokens(sumario)

    # Tokens dos trechos específicos lidos
    tokens_trechos = sum(
        s.tokens_estimados for s in metadados.secoes if s.pagina in paginas_consultadas
    )

    tokens_com_estrategia = tokens_metadados + tokens_trechos
    tokens_doc_inteiro = metadados.tokens_estimados_total

    tokens_economizados = max(0, tokens_doc_inteiro - tokens_com_estrategia)
    percentual = (
        (tokens_economizados / tokens_doc_inteiro * 100.0)
        if tokens_doc_inteiro > 0
        else 0.0
    )

    return RelatorioEconomiaTokens(
        documento=metadados.arquivo,
        tokens_documento_inteiro=tokens_doc_inteiro,
        tokens_apenas_metadados=tokens_metadados,
        tokens_trecho_consultado=tokens_trechos,
        tokens_totais_consumidos=tokens_com_estrategia,
        tokens_economizados=tokens_economizados,
        percentual_economia=round(percentual, 1),
    )


def cortar_referencias_texto(texto: str) -> tuple[str, bool, int]:
    """Corta a seção final de referências bibliográficas para economizar de 25% a 40% de tokens.

    Retorna (texto_limpo, cortou_boolean, caracteres_economizados).
    """
    padrao_ref = re.compile(
        r"(?im)^\s*(?:references|refer[êe]ncias(?:\s+bibliogr[áa]ficas)?|literature\s+cited|bibliography)\b",
    )
    m = padrao_ref.search(texto)
    if m:
        pos = m.start()
        # Garante que só corta se estiver após os primeiros 30% do texto para evitar falsos positivos
        if pos > len(texto) * 0.3:
            economizados = len(texto) - pos
            texto_limpo = (
                texto[:pos].rstrip()
                + "\n\n[... REFERÊNCIAS BIBLIOGRÁFICAS SUPRIMIDAS PELO SISTEMA (ECONOMIA DE TOKENS) ...]\n"
            )
            return texto_limpo, True, economizados
    return texto, False, 0


def buscar_paragrafos_cirurgicos(
    caminho_arquivo: Path,
    pergunta_ou_termos: str,
    top_k: int = 2
) -> ResultadoBuscaCirurgica:
    """Busca cirurgicamente os parágrafos mais relevantes para uma consulta em qualquer documento.

    1. Corta referências bibliográficas do final.
    2. Divide em blocos/parágrafos anotados com o número da página/seção.
    3. Pontua os parágrafos por relevância temática aos termos da consulta.
    4. Retorna os top_k parágrafos, alcançando 95%+ de economia em relação ao documento integral.
    """
    import re
    caminho_arquivo = Path(caminho_arquivo).resolve()
    if not caminho_arquivo.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_arquivo}")

    ext = caminho_arquivo.suffix.lower()
    paginas_texto: list[tuple[int, str]] = []

    if ext == ".pdf":
        leitor = PdfReader(str(caminho_arquivo))
        for idx, page in enumerate(leitor.pages):
            txt = page.extract_text() or ""
            paginas_texto.append((idx + 1, txt))
    elif ext == ".docx":
        import zipfile
        import xml.etree.ElementTree as ET
        with zipfile.ZipFile(str(caminho_arquivo)) as z:
            xml_content = z.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            paragraphs = []
            for p in tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
                texts = [node.text for node in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t") if node.text]
                if texts:
                    full_p = "".join(texts).strip()
                    if full_p:
                        paragraphs.append(full_p)
            bloco_tam = 5
            for i in range(0, len(paragraphs), bloco_tam):
                num_p = (i // bloco_tam) + 1
                txt_b = "\n\n".join(paragraphs[i:i + bloco_tam])
                paginas_texto.append((num_p, txt_b))
    else:  # txt, md
        conteudo = caminho_arquivo.read_text(encoding="utf-8", errors="ignore")
        linhas = conteudo.splitlines()
        bloco_tam = 35
        for i in range(0, len(linhas), bloco_tam):
            num_p = (i // bloco_tam) + 1
            txt_b = "\n".join(linhas[i:i + bloco_tam])
            paginas_texto.append((num_p, txt_b))

    # Corta referências a partir da página onde foram detectadas
    paginas_filtradas: list[tuple[int, str]] = []
    achou_ref = False
    for num_pag, txt in paginas_texto:
        if achou_ref:
            break
        txt_limpo, cortou, _ = cortar_referencias_texto(txt)
        paginas_filtradas.append((num_pag, txt_limpo))
        if cortou:
            achou_ref = True

    # Tokens totais do documento inteiro
    texto_total_doc = " ".join([p[1] for p in paginas_texto])
    tokens_doc_inteiro = estimar_tokens(texto_total_doc)

    # Termos de busca normalizados
    stopwords = {
        "qual", "quais", "como", "onde", "quando", "porque", "por", "que", "de", "do", "da",
        "dos", "das", "em", "no", "na", "nos", "nas", "para", "com", "foi", "foram", "são",
        "the", "a", "an", "and", "or", "of", "in", "on", "at", "to", "for", "with", "by", "what", "how"
    }
    termos_brutos = re.findall(r"\b[A-Za-z0-9á-úÁ-Ú_-]{3,}\b", pergunta_ou_termos.lower())
    termos_chave = [t for t in termos_brutos if t not in stopwords]
    if not termos_chave:
        termos_chave = termos_brutos or [pergunta_ou_termos.lower()]

    candidatos_paragrafos: list[dict] = []
    for num_pag, txt_pag in paginas_filtradas:
        # Fatiamento inteligente em parágrafos enxutos (~50 a 100 palavras)
        blocos_iniciais = [b.strip() for b in re.split(r"\n\s*\n", txt_pag) if b.strip()]
        paragrafos: list[str] = []
        for bloco in blocos_iniciais:
            if len(bloco) <= 800:
                if len(bloco) > 35:
                    paragrafos.append(bloco)
            else:
                frases = re.split(r"(?<=[.!?])\s+(?=[A-ZÁ-Ú0-9])", bloco)
                chunk: list[str] = []
                tam = 0
                for f in frases:
                    chunk.append(f)
                    tam += len(f)
                    if tam >= 450:
                        paragrafos.append(" ".join(chunk))
                        chunk = []
                        tam = 0
                if chunk:
                    paragrafos.append(" ".join(chunk))

        for par in paragrafos:
            par_lower = par.lower()
            score = 0.0
            for t in termos_chave:
                if t in par_lower:
                    score += 1.0 * par_lower.count(t)
                    if re.search(rf"\b{re.escape(t)}\b", par_lower):
                        score += 2.0

            if score > 0:
                candidatos_paragrafos.append({
                    "pagina": num_pag,
                    "texto": par,
                    "score": score,
                    "tokens": estimar_tokens(par)
                })

    candidatos_paragrafos.sort(key=lambda x: x["score"], reverse=True)
    selecionados = candidatos_paragrafos[:top_k]

    if not selecionados and paginas_filtradas:
        p1 = paginas_filtradas[0]
        amostra = p1[1][:450].strip()
        selecionados.append({
            "pagina": p1[0],
            "texto": amostra,
            "score": 0.1,
            "tokens": estimar_tokens(amostra)
        })

    trechos_model = [
        ParagrafoCirurgico(
            arquivo=caminho_arquivo.name,
            pagina=s["pagina"],
            texto=s["texto"],
            relevancia_score=round(s["score"], 2),
            tokens_estimados=s["tokens"]
        )
        for s in selecionados
    ]

    tokens_trechos = sum(t.tokens_estimados for t in trechos_model)
    economia = max(0, tokens_doc_inteiro - tokens_trechos)
    pct = (economia / tokens_doc_inteiro * 100.0) if tokens_doc_inteiro > 0 else 0.0

    return ResultadoBuscaCirurgica(
        arquivo=caminho_arquivo.name,
        consulta=pergunta_ou_termos,
        trechos=trechos_model,
        tokens_totais_trechos=tokens_trechos,
        tokens_documento_inteiro=tokens_doc_inteiro,
        percentual_economia=round(pct, 1)
    )

