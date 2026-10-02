# -*- coding: utf-8 -*-
"""
Script de Triagem, Deduplicação, Mapeamento e Movimentação Segura Multiformato.
Cofre Síndrome de Pandora (UFC - Romulo) — Custo de IA: ZERO tokens.

Formatos Suportados:
- Documentos PDF (.pdf)
- Documentos Word (.docx)
- Arquivos de Texto (.txt, .md)
- Imagens / Figuras (.png, .jpg, .jpeg, .webp, .tiff, .bmp)

Fluxo Completo de Ingestão:
1. Novos arquivos entram na pasta raiz: PDF/
2. Extração local de metadados específicos de cada formato (sem gastar tokens de IA):
   - PDF: páginas, DOI, ano provável, alerta OCR, sumário de seções
   - Word: parágrafos, palavras, estimativa de tokens, títulos/seções, DOI
   - Texto: linhas, palavras, tokens, seções markdown (#)
   - Imagem: dimensões (LxA px), formato, modo de cor, tokens de visão LLM
3. Deduplicação inteligente no acervo:
   - Hash SHA-256 binário idêntico (100% igual)
   - DOI idêntico (se houver)
   - Similaridade Fuzzy de Título (difflib >= 88%)
   - Se for duplicata: move com segurança para 'PDF/_Lixeira_Duplicatas/'
4. Para documentos inéditos:
   - Cria nota de metadados em Fontes/ adaptada para o formato (com preview se for imagem)
   - Insere automaticamente em 'Notas/Fila de leitura.md'
   - O arquivo original aguarda na pasta raiz PDF/
5. Movimentação pós-fichamento:
   - SÓ MOVE para a respectiva pasta de destino após o fichamento estar concluído em Fichamentos/:
     * PDF -> PDF/PDF_python/
     * Word -> PDF/Word_python/
     * Texto -> PDF/Texto_python/
     * Imagem -> PDF/Imagens_python/
   - Atualiza wikilinks na Fonte e executa a sincronização do cofre.
"""

import os
import re
import sys
import shutil
import hashlib
import difflib
import zipfile
import logging
import warnings
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")
logging.getLogger("pypdf").setLevel(logging.ERROR)

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

VAULT = Path(r"C:\Users\rcmin\OneDrive\Documents\Pos-Graduacao\Doutorado UFC\Síndrome de Pandora")
ORIGEM_DIR = VAULT / "PDF"
LIXEIRA_DIR = VAULT / "PDF" / "_Lixeira_Duplicatas"
FONTES_DIR = VAULT / "Fontes"
FICHAMENTOS_DIR = VAULT / "Fichamentos"
FILA_LEITURA_PATH = VAULT / "Notas" / "Fila de leitura.md"

EXTENSOES_SUPORTADAS = {
    "pdf": [".pdf"],
    "word": [".docx"],
    "texto": [".txt", ".md"],
    "imagem": [".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp"]
}

TODAS_EXTENSOES = [ext for lista in EXTENSOES_SUPORTADAS.values() for ext in lista]


def obter_pasta_destino(extensao: str) -> Path:
    """Retorna a subpasta apropriada para o tipo de arquivo fichado."""
    ext = extensao.lower()
    if ext in EXTENSOES_SUPORTADAS["pdf"]:
        return VAULT / "PDF" / "PDF_python"
    elif ext in EXTENSOES_SUPORTADAS["word"]:
        return VAULT / "PDF" / "Word_python"
    elif ext in EXTENSOES_SUPORTADAS["texto"]:
        return VAULT / "PDF" / "Texto_python"
    elif ext in EXTENSOES_SUPORTADAS["imagem"]:
        return VAULT / "PDF" / "Imagens_python"
    return VAULT / "PDF" / "Outros_python"


def calcular_sha256(caminho_arquivo: Path) -> str:
    """Calcula o hash SHA-256 para comparação binária exata."""
    h = hashlib.sha256()
    with open(caminho_arquivo, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def normalizar_texto_titulo(texto: str) -> str:
    """Normaliza título para comparação fuzzy precisa."""
    t = texto.lower()
    t = re.sub(r"\.(pdf|docx|txt|md|png|jpg|jpeg|webp)$", "", t)
    t = re.sub(r"[^a-zá-ú0-9\s]", " ", t)
    stopwords = {
        "the", "a", "an", "and", "or", "of", "in", "on", "at", "to", "for", "with", "by",
        "o", "a", "os", "as", "um", "uma", "de", "do", "da", "dos", "das", "em", "no", "na",
        "nos", "nas", "para", "com", "por", "sobre", "feline", "cats", "cat", "gatos", "gato"
    }
    palavras = [p for p in t.split() if p not in stopwords and len(p) > 2]
    return " ".join(palavras)


def calcular_similaridade(t1: str, t2: str) -> float:
    """Calcula similaridade entre dois títulos (0.0 a 1.0)."""
    n1 = normalizar_texto_titulo(t1)
    n2 = normalizar_texto_titulo(t2)
    if not n1 or not n2:
        return 0.0
    return difflib.SequenceMatcher(None, n1, n2).ratio()


# =====================================================================
# EXTRATORES DE METADADOS POR TIPO DE ARQUIVO
# =====================================================================

def extrair_metadados_pdf(pdf_path: Path) -> dict:
    dados = {
        "tipo": "PDF",
        "hash": calcular_sha256(pdf_path),
        "total_paginas": 0,
        "titulo_sugerido": pdf_path.stem.replace("_", " ").replace("-", " "),
        "ano_sugerido": "A CONFERIR",
        "doi": None,
        "necessita_ocr": False,
        "secoes": [],
        "detalhes": {}
    }
    if not pypdf:
        return dados

    try:
        reader = pypdf.PdfReader(str(pdf_path))
        dados["total_paginas"] = len(reader.pages)

        if reader.metadata and reader.metadata.title:
            t = str(reader.metadata.title).strip()
            if len(t) > 6 and not t.lower().endswith(".pdf") and not t.lower().startswith("untitled"):
                dados["titulo_sugerido"] = t

        amostra = ""
        for i in range(min(len(reader.pages), 3)):
            amostra += (reader.pages[i].extract_text() or "") + "\n"

        if dados["total_paginas"] > 0 and len(amostra.strip()) < 80:
            dados["necessita_ocr"] = True

        m_doi = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", amostra)
        if m_doi:
            dados["doi"] = m_doi.group(0).rstrip(".,;)")

        m_ano = re.findall(r"\b(20[0-2][0-9]|19[8-9][0-9])\b", amostra)
        if m_ano:
            from collections import Counter
            dados["ano_sugerido"] = Counter(m_ano).most_common(1)[0][0]

        # Mapeamento de seções
        if not dados["necessita_ocr"]:
            padroes = [
                ("Resumo / Abstract", re.compile(r"(?i)\b(resumo|abstract|sumário)\b")),
                ("Introdução", re.compile(r"(?i)\b(introdução|introduction)\b")),
                ("Material e Métodos", re.compile(r"(?i)\b(material\s+e\s+métodos|materials?\s+and\s+methods|metodologia)\b")),
                ("Resultados", re.compile(r"(?i)\b(resultados?|results?)\b")),
                ("Discussão", re.compile(r"(?i)\b(discussão|discussion)\b")),
                ("Conclusão", re.compile(r"(?i)\b(conclus[ãa]o|conclus[õo]es|conclusions?)\b")),
                ("Referências", re.compile(r"(?i)\b(referências|references)\b"))
            ]
            nomes_vistos = set()
            for idx in range(min(len(reader.pages), 35)):
                txt_p = reader.pages[idx].extract_text() or ""
                for nome_sec, reg in padroes:
                    if nome_sec not in nomes_vistos and reg.search(txt_p[:500]):
                        dados["secoes"].append(f"{nome_sec} (p. {idx + 1})")
                        nomes_vistos.add(nome_sec)
    except Exception as e:
        print(f"   ⚠️ Aviso ao ler PDF: {e}")

    return dados


def extrair_metadados_docx(docx_path: Path) -> dict:
    dados = {
        "tipo": "Word",
        "hash": calcular_sha256(docx_path),
        "total_paginas": "Fluxo contínuo (Word)",
        "titulo_sugerido": docx_path.stem.replace("_", " ").replace("-", " "),
        "ano_sugerido": "A CONFERIR",
        "doi": None,
        "necessita_ocr": False,
        "secoes": [],
        "detalhes": {"paragrafos": 0, "palavras": 0, "tokens_estimados": 0}
    }
    try:
        with zipfile.ZipFile(docx_path) as z:
            xml_content = z.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            paragraphs = []
            for p in tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
                texts = [node.text for node in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t") if node.text]
                if texts:
                    full_p = "".join(texts).strip()
                    if full_p:
                        paragraphs.append(full_p)

            dados["detalhes"]["paragrafos"] = len(paragraphs)
            texto_todo = "\n".join(paragraphs)
            palavras = texto_todo.split()
            dados["detalhes"]["palavras"] = len(palavras)
            dados["detalhes"]["tokens_estimados"] = max(1, round(len(texto_todo) / 4))

            if paragraphs:
                dados["titulo_sugerido"] = paragraphs[0][:75]

            m_doi = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", texto_todo)
            if m_doi:
                dados["doi"] = m_doi.group(0).rstrip(".,;)")

            m_ano = re.findall(r"\b(20[0-2][0-9]|19[8-9][0-9])\b", texto_todo[:2500])
            if m_ano:
                from collections import Counter
                dados["ano_sugerido"] = Counter(m_ano).most_common(1)[0][0]

            for p in paragraphs[:40]:
                if len(p) < 65 and re.match(r"(?i)^(1\.|2\.|3\.|4\.|5\.|I\.|II\.|#|\b(resumo|abstract|introdução|introduction|métodos?|methods?|resultados?|results?|discussão|discussion|conclus[ãa]o|referências))\b", p):
                    dados["secoes"].append(p)
    except Exception as e:
        print(f"   ⚠️ Aviso ao ler Word (.docx): {e}")

    return dados


def extrair_metadados_texto(txt_path: Path) -> dict:
    dados = {
        "tipo": "Texto",
        "hash": calcular_sha256(txt_path),
        "total_paginas": "Texto corrido",
        "titulo_sugerido": txt_path.stem.replace("_", " ").replace("-", " "),
        "ano_sugerido": "A CONFERIR",
        "doi": None,
        "necessita_ocr": False,
        "secoes": [],
        "detalhes": {"linhas": 0, "palavras": 0, "tokens_estimados": 0}
    }
    try:
        content = txt_path.read_text(encoding="utf-8", errors="ignore")
        linhas = [l.strip() for l in content.splitlines() if l.strip()]
        dados["detalhes"]["linhas"] = len(linhas)
        palavras = content.split()
        dados["detalhes"]["palavras"] = len(palavras)
        dados["detalhes"]["tokens_estimados"] = max(1, round(len(content) / 4))

        for l in linhas:
            if l.startswith("#") and len(l) < 70:
                dados["secoes"].append(l.lstrip("#").strip())
            elif re.match(r"(?i)\b(resumo|abstract|introdução|introduction|métodos?|methods?|resultados?|results?|discussão|discussion|conclus[ãa]o|referências)\b", l) and len(l) < 60:
                dados["secoes"].append(l)

        if dados["secoes"]:
            dados["titulo_sugerido"] = dados["secoes"][0]
        elif linhas:
            dados["titulo_sugerido"] = linhas[0][:75]

        m_doi = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", content)
        if m_doi:
            dados["doi"] = m_doi.group(0).rstrip(".,;)")

        m_ano = re.findall(r"\b(20[0-2][0-9]|19[8-9][0-9])\b", content[:2000])
        if m_ano:
            from collections import Counter
            dados["ano_sugerido"] = Counter(m_ano).most_common(1)[0][0]
    except Exception as e:
        print(f"   ⚠️ Aviso ao ler Texto: {e}")

    return dados


def extrair_metadados_imagem(img_path: Path) -> dict:
    dados = {
        "tipo": "Imagem",
        "hash": calcular_sha256(img_path),
        "total_paginas": "1 imagem",
        "titulo_sugerido": img_path.stem.replace("_", " ").replace("-", " "),
        "ano_sugerido": "A CONFERIR",
        "doi": None,
        "necessita_ocr": False,
        "secoes": [],
        "detalhes": {
            "dimensoes": "NÃO CONFIRMADO",
            "formato": img_path.suffix.upper().lstrip("."),
            "tamanho_kb": round(img_path.stat().st_size / 1024, 1),
            "tokens_visao_estimados": 85
        }
    }
    if PIL_AVAILABLE:
        try:
            with Image.open(img_path) as im:
                dados["detalhes"]["dimensoes"] = f"{im.width} x {im.height} px"
                dados["detalhes"]["formato"] = im.format or dados["detalhes"]["formato"]
                dados["detalhes"]["modo_cor"] = im.mode
                tiles_w = (im.width + 511) // 512
                tiles_h = (im.height + 511) // 512
                dados["detalhes"]["tokens_visao_estimados"] = 85 + (tiles_w * tiles_h * 170)
        except Exception as e:
            print(f"   ⚠️ Aviso ao inspecionar Imagem: {e}")

    return dados


def extrair_metadados_arquivo(arquivo_path: Path) -> dict:
    """Encaminha o arquivo para o extrator adequado de acordo com sua extensão."""
    ext = arquivo_path.suffix.lower()
    if ext in EXTENSOES_SUPORTADAS["pdf"]:
        return extrair_metadados_pdf(arquivo_path)
    elif ext in EXTENSOES_SUPORTADAS["word"]:
        return extrair_metadados_docx(arquivo_path)
    elif ext in EXTENSOES_SUPORTADAS["texto"]:
        return extrair_metadados_texto(arquivo_path)
    elif ext in EXTENSOES_SUPORTADAS["imagem"]:
        return extrair_metadados_imagem(arquivo_path)
    else:
        return {
            "tipo": "Outro",
            "hash": calcular_sha256(arquivo_path),
            "total_paginas": "NÃO CONFIRMADO",
            "titulo_sugerido": arquivo_path.stem,
            "ano_sugerido": "A CONFERIR",
            "doi": None,
            "necessita_ocr": False,
            "secoes": [],
            "detalhes": {}
        }


# =====================================================================
# DEDUPLICAÇÃO E VERIFICAÇÕES
# =====================================================================

def buscar_duplicata_no_acervo(arquivo_novo: Path, meta_novo: dict) -> tuple[bool, str, str]:
    """Verifica duplicatas no acervo por Hash binário, DOI ou Similaridade de Título."""
    hash_novo = meta_novo["hash"]
    doi_novo = meta_novo.get("doi")
    titulo_novo = meta_novo.get("titulo_sugerido") or arquivo_novo.stem

    # 1. Checagem por Hash Binário em todo o diretório de arquivos
    pastas_varrer = [VAULT / "PDF", VAULT / "Imagens", VAULT / "txt"]
    for pasta in pastas_varrer:
        if not pasta.exists():
            continue
        for p in pasta.rglob("*"):
            if not p.is_file() or p == arquivo_novo or "_Lixeira_Duplicatas" in str(p):
                continue
            try:
                if p.stat().st_size == arquivo_novo.stat().st_size:
                    if calcular_sha256(p) == hash_novo:
                        return True, "Hash Binário Idêntico", f"Cópia idêntica ao arquivo existente: {p.relative_to(VAULT)}"
            except Exception:
                continue

    # 2. Checagem por DOI em Fontes/
    if doi_novo:
        for f in FONTES_DIR.glob("*.md"):
            txt = f.read_text(encoding="utf-8")
            if doi_novo.lower() in txt.lower():
                return True, "DOI Idêntico", f"DOI [{doi_novo}] já registrado na nota: {f.name}"

    # 3. Checagem Fuzzy por Similaridade de Título (para textos, Word e PDF)
    if meta_novo["tipo"] in ["PDF", "Word", "Texto"]:
        for f in FONTES_DIR.glob("*.md"):
            m = re.match(r"^[A-Za-z0-9]+\s+(.*)\.md$", f.name)
            titulo_fonte = m.group(1) if m else f.stem
            sim = calcular_similaridade(titulo_novo, titulo_fonte)
            if sim >= 0.88:
                return True, f"Título Similar ({int(sim*100)}%)", f"Título quase idêntico ao da nota '{f.name}'"

    return False, "", ""


def mover_para_lixeira_duplicatas(arquivo_file: Path, motivo: str) -> Path:
    """Move arquivo duplicado para quarentena segura (Lixeira de Duplicatas)."""
    LIXEIRA_DIR.mkdir(parents=True, exist_ok=True)
    destino = LIXEIRA_DIR / arquivo_file.name
    if destino.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = LIXEIRA_DIR / f"{arquivo_file.stem}_{timestamp}{arquivo_file.suffix}"
    shutil.move(str(arquivo_file), str(destino))
    return destino


def encontrar_fonte_do_arquivo(nome_arquivo: str) -> tuple[Path | None, str | None]:
    """Localiza qual nota em Fontes/ faz referência ao arquivo."""
    nome_lower = nome_arquivo.lower()
    for f in FONTES_DIR.glob("*.md"):
        txt = f.read_text(encoding="utf-8")
        if nome_lower in txt.lower():
            m = re.match(r"^([A-Za-z0-9]+)\s*[\s—_]", f.name)
            cod = m.group(1).strip() if m else None
            return f, cod
    return None, None


def verificar_fichamento_concluido(cod: str | None, fonte_path: Path | None) -> tuple[bool, Path | None, str]:
    """Verifica se o fichamento existe e está concluído."""
    if not fonte_path or not fonte_path.exists():
        return False, None, "Nota correspondente não encontrada em Fontes/"

    txt_fonte = fonte_path.read_text(encoding="utf-8")
    status_concluido = bool(re.search(r'status:\s*"?fichamento[\s_-]concluido"?', txt_fonte, re.IGNORECASE))

    fich_alvo = None
    if cod:
        for f in FICHAMENTOS_DIR.glob("*.md"):
            if f.name.startswith(f"{cod} ") or f.name.startswith(f"{cod}—") or f.name.startswith(f"{cod} —"):
                fich_alvo = f
                break

    if not fich_alvo:
        m_link = re.search(r"-\s*\*\*Fichamento:\*\*\s*\[\[(?:Fichamentos/)?([^\]]+)\]\]", txt_fonte)
        if m_link:
            nome_link = m_link.group(1).strip()
            if not nome_link.endswith(".md"):
                nome_link += ".md"
            cand = FICHAMENTOS_DIR / nome_link
            if cand.exists():
                fich_alvo = cand

    if not fich_alvo or not fich_alvo.exists():
        return False, None, "Arquivo de fichamento ainda não existe em Fichamentos/"

    if fich_alvo.stat().st_size < 300:
        return False, fich_alvo, f"Fichamento existe ({fich_alvo.name}), mas tem menos de 300 bytes (incompleto)."

    txt_fich = fich_alvo.read_text(encoding="utf-8")
    if "status: \"fichamento concluido\"" not in txt_fich and not status_concluido:
        return False, fich_alvo, f"Fichamento ({fich_alvo.name}) não está marcado com status concluído."

    return True, fich_alvo, "Fichamento completo e validado."


def atualizar_link_na_fonte(fonte_path: Path, nome_arquivo: str, novo_caminho_rel: str) -> bool:
    """Atualiza o link do documento na nota da fonte."""
    txt = fonte_path.read_text(encoding="utf-8")
    novo_link = f"[[{novo_caminho_rel}]]"

    # Substitui links do tipo [[PDF/nome.ext]] ou [[nome.ext]]
    padrao = rf"\[\[(?:[^\]]+/)?{re.escape(nome_arquivo)}\]\]"
    novo_txt, total = re.subn(padrao, novo_link, txt)
    if total > 0:
        fonte_path.write_text(novo_txt, encoding="utf-8")
        return True

    padrao_linha = rf"(?m)^(-\s*\*\*(?:PDF|Arquivo|Imagem|Documento):\*\*\s*)\[\[.*?{re.escape(Path(nome_arquivo).stem)}.*?\]\]"
    novo_txt, total = re.subn(padrao_linha, rf"\1{novo_link}", txt)
    if total > 0:
        fonte_path.write_text(novo_txt, encoding="utf-8")
        return True

    return False


def obter_proximo_codigo_fonte() -> str:
    """Obtém o próximo código numérico disponível."""
    max_num = 0
    for f in FONTES_DIR.glob("*.md"):
        m = re.match(r"^(\d+)\s", f.name)
        if m:
            max_num = max(max_num, int(m.group(1)))
    return str(max_num + 1)


def inserir_na_fila_de_leitura(cod: str, ano: str, fonte_stem: str, titulo: str) -> bool:
    """Insere o novo item na seção de pendências da Fila de Leitura."""
    if not FILA_LEITURA_PATH.exists():
        return False

    txt = FILA_LEITURA_PATH.read_text(encoding="utf-8")
    if f"[[{fonte_stem}" in txt or f"**{cod}**" in txt:
        return False

    linha_nova = f"- [ ] **{cod}** ({ano}) — [[{fonte_stem}|{titulo}]]"
    m_sec = re.search(r"(## PDF ou fichamento disponível[^\n]*\n)", txt)
    if m_sec:
        pos = m_sec.end()
        novo_txt = txt[:pos] + f"\n{linha_nova}\n" + txt[pos:]
        FILA_LEITURA_PATH.write_text(novo_txt, encoding="utf-8")
        return True

    return False


def criar_nota_fonte_multiformato(arquivo_file: Path, meta: dict) -> Path:
    """Cria nota estruturada em Fontes/ adaptada para PDF, Word, Texto ou Imagem."""
    cod = obter_proximo_codigo_fonte()
    tipo = meta["tipo"]
    tit = meta.get("titulo_sugerido") or arquivo_file.stem
    tit_curto = tit[:65].replace(":", " ").replace("/", " ").replace("\\", " ").strip()
    nome_arquivo = f"{cod} {tit_curto}.md"
    caminho = FONTES_DIR / nome_arquivo

    ano_str = meta.get("ano_sugerido") or "A CONFERIR"
    doi_str = meta.get("doi") or "NÃO CONFIRMADO"
    tags = ["fonte", "status/arquivo-obtido", f"formato/{tipo.lower()}"]

    if meta.get("necessita_ocr"):
        tags.append("status/necessita-ocr")

    # Linhas de metadados específicos
    linhas_meta = [
        f"- **Formato:** {tipo} (`{arquivo_file.suffix}`)",
        f"- **Hash SHA-256:** `{meta['hash'][:16]}...`"
    ]

    if tipo == "PDF":
        linhas_meta.append(f"- **Total de páginas:** {meta.get('total_paginas', 'NÃO CONFIRMADO')}")
        linhas_meta.append(f"- **DOI detectado:** {doi_str}")
    elif tipo == "Word":
        det = meta.get("detalhes", {})
        linhas_meta.append(f"- **Parágrafos:** {det.get('paragrafos', 0)} | **Palavras:** {det.get('palavras', 0)}")
        linhas_meta.append(f"- **Tokens estimados:** ~{det.get('tokens_estimados', 0)} tokens")
        linhas_meta.append(f"- **DOI detectado:** {doi_str}")
    elif tipo == "Texto":
        det = meta.get("detalhes", {})
        linhas_meta.append(f"- **Linhas:** {det.get('linhas', 0)} | **Palavras:** {det.get('palavras', 0)}")
        linhas_meta.append(f"- **Tokens estimados:** ~{det.get('tokens_estimados', 0)} tokens")
    elif tipo == "Imagem":
        det = meta.get("detalhes", {})
        linhas_meta.append(f"- **Dimensões:** {det.get('dimensoes', 'NÃO CONFIRMADO')}")
        linhas_meta.append(f"- **Tamanho:** {det.get('tamanho_kb', 0)} KB")
        linhas_meta.append(f"- **Tokens estimados (visão multimodal):** ~{det.get('tokens_visao_estimados', 85)} tokens")

    # Bloco OCR
    bloco_ocr = ""
    if meta.get("necessita_ocr"):
        bloco_ocr = (
            "> [!warning] Alerta de OCR — Sem Camada de Texto Digital\n"
            "> Este documento é uma imagem ou scan sem texto digital extraível.\n"
            "> **Recomendação:** Aplicar OCR antes de iniciar o fichamento.\n\n"
        )

    # Preview se for imagem
    bloco_preview = ""
    if tipo == "Imagem":
        bloco_preview = f"\n### Pré-visualização\n![[{arquivo_file.name}]]\n"

    # Seções
    bloco_secoes = ""
    if meta.get("secoes"):
        bloco_secoes = "\n### Seções Detectadas no Documento\n" + "\n".join([f"- {s}" for s in meta["secoes"]]) + "\n"

    tags_fmt = "\n".join([f"  - {t}" for t in tags])
    meta_fmt = "\n".join(linhas_meta)

    conteudo = f"""---
codigo: "{cod}"
status: "arquivo obtido"
tipo_de_estudo: "A CONFERIR no artigo"
tipo_de_arquivo: "{tipo.lower()}"
nucleo: "proposto"
ano: "{ano_str}"
tags:
{tags_fmt}
---

# {cod} — {tit}

{bloco_ocr}## Arquivo
- **Arquivo:** [[PDF/{arquivo_file.name}]]
- **Fichamento:** a fazer

## Metadados Extraídos Localmente (Custo Zero de IA)
{meta_fmt}
{bloco_preview}{bloco_secoes}
## Procedência da Referência
⚠️ **A CONFERIR no artigo**
"""
    caminho.write_text(conteudo, encoding="utf-8")
    inserir_na_fila_de_leitura(cod, ano_str, caminho.stem, tit)
    return caminho


# =====================================================================
# FLUXO PRINCIPAL DE EXECUÇÃO
# =====================================================================

def processar_fluxo_multiformato(dry_run: bool = False) -> dict:
    print("=" * 72)
    print("⚡ GERENCIADOR MULTIFORMATO: PDF, WORD, TEXTO E IMAGEM")
    print("   Cofre Síndrome de Pandora (UFC - Romulo) — Custo de IA: ZERO tokens")
    print("=" * 72)

    # Garante subpastas
    for pasta in ["PDF_python", "Word_python", "Texto_python", "Imagens_python", "_Lixeira_Duplicatas"]:
        (ORIGEM_DIR / pasta).mkdir(parents=True, exist_ok=True)

    # Lista todos os arquivos suportados soltos na raiz de PDF/
    candidatos = [
        f for f in ORIGEM_DIR.glob("*")
        if f.is_file() and f.suffix.lower() in TODAS_EXTENSOES
    ]

    resultados = {
        "duplicatas_lixeira": 0,
        "novos_metadados_criados": 0,
        "aguardando_fichamento": 0,
        "movidos_fichados": 0
    }

    if not candidatos:
        print("ℹ️ Nenhum arquivo novo solto na pasta raiz 'PDF\\'.")
        print("   -> Você pode colocar arquivos PDF (.pdf), Word (.docx), Texto (.txt/.md) ou Imagens (.png/.jpg) diretamente na pasta 'PDF\\'.")
        print("=" * 72)
        return resultados

    print(f"📦 Identificado(s) {len(candidatos)} arquivo(s) na pasta raiz 'PDF\\':\n")

    for arq in candidatos:
        ext = arq.suffix.lower()
        print(f"📄 [PROCESSANDO {ext.upper()}] {arq.name}")

        # 1. Extração local
        meta = extrair_metadados_arquivo(arq)
        tipo = meta["tipo"]
        print(f"   ├─ Tipo: {tipo} | Hash SHA-256: {meta['hash'][:12]}...")

        if tipo == "PDF":
            print(f"   ├─ Páginas: {meta['total_paginas']}")
        elif tipo == "Word":
            print(f"   ├─ Parágrafos: {meta['detalhes'].get('paragrafos', 0)} | Palavras: {meta['detalhes'].get('palavras', 0)}")
        elif tipo == "Texto":
            print(f"   ├─ Linhas: {meta['detalhes'].get('linhas', 0)} | Palavras: {meta['detalhes'].get('palavras', 0)}")
        elif tipo == "Imagem":
            print(f"   ├─ Dimensões: {meta['detalhes'].get('dimensoes')} | Tamanho: {meta['detalhes'].get('tamanho_kb')} KB")

        if meta.get("doi"):
            print(f"   ├─ DOI detectado: {meta['doi']}")
        if meta.get("necessita_ocr"):
            print(f"   ├─ ⚠️ ALERTA: Necessita OCR (sem camada de texto digital)!")

        # 2. Deduplicação
        is_duplicata, tipo_dup, detalhe = buscar_duplicata_no_acervo(arq, meta)
        if is_duplicata:
            print(f"   🚨 DUPLICATA IDENTIFICADA ({tipo_dup})!")
            print(f"      Detalhe: {detalhe}")
            if not dry_run:
                dest_lixeira = mover_para_lixeira_duplicatas(arq, tipo_dup)
                print(f"      🗑️ [SEGURO] Movido para Lixeira de Duplicatas: {dest_lixeira.relative_to(VAULT)}\n")
            else:
                print(f"      [SIMULAÇÃO] Arquivo seria movido para PDF/_Lixeira_Duplicatas/.\n")
            resultados["duplicatas_lixeira"] += 1
            continue

        # 3. Documento Inédito -> Registra Metadados
        print(f"   ✅ [INÉDITO] Arquivo exclusivo validado ({tipo}).")
        fonte_path, cod = encontrar_fonte_do_arquivo(arq.name)

        if not fonte_path:
            if not dry_run:
                fonte_path = criar_nota_fonte_multiformato(arq, meta)
                m = re.match(r"^([A-Za-z0-9]+)\s", fonte_path.name)
                cod = m.group(1).strip() if m else None
                print(f"   📝 [METADADOS CRIADOS] Nota de Fonte: Fontes/{fonte_path.name}")
                print(f"   📌 Adicionado automaticamente à Fila de Leitura.")
                resultados["novos_metadados_criados"] += 1
            else:
                print("   [SIMULAÇÃO] Criaria nota de Fonte em Fontes/.")
        else:
            print(f"   📋 Nota de Fonte já existente: Fontes/{fonte_path.name}")

        # 4. Verificação de Fichamento
        concluido, fich_path, motivo_fich = verificar_fichamento_concluido(cod, fonte_path)
        if not concluido:
            print(f"   ⏳ [AGUARDANDO FICHAMENTO] {motivo_fich}")
            print(f"      O arquivo permanece em 'PDF\\' para leitura/análise.")
            print(f"      (A LLM lerá apenas os metadados cadastrados em Fontes/).\n")
            resultados["aguardando_fichamento"] += 1
            continue

        # 5. Fichamento Concluído -> Move para pasta de destino do formato
        pasta_dest = obter_pasta_destino(arq.suffix)
        pasta_dest.mkdir(parents=True, exist_ok=True)
        destino_final = pasta_dest / arq.name
        rel_novo = f"PDF/{pasta_dest.name}/{arq.name}"

        print(f"   🎯 [FICHAMENTO CONCLUÍDO COMPROVADO] {fich_path.name}")
        if not dry_run:
            if destino_final.exists() and destino_final != arq:
                base = arq.stem
                ext_arq = arq.suffix
                i = 1
                while (pasta_dest / f"{base}_{i}{ext_arq}").exists():
                    i += 1
                destino_final = pasta_dest / f"{base}_{i}{ext_arq}"
                rel_novo = f"PDF/{pasta_dest.name}/{destino_final.name}"

            shutil.move(str(arq), str(destino_final))
            atualizar_link_na_fonte(fonte_path, arq.name, rel_novo)
            print(f"   🚀 [MOVIDO] Arquivo transferido para: {destino_final.relative_to(VAULT)}")
            print(f"      Wikilink atualizado na Fonte ({fonte_path.name}).\n")
            resultados["movidos_fichados"] += 1
        else:
            print(f"   [SIMULAÇÃO] Arquivo seria movido para {rel_novo}.\n")
            resultados["movidos_fichados"] += 1

    print("=" * 72)
    print("📊 RESUMO DA EXECUÇÃO MULTIFORMATO:")
    print(f"   • Duplicatas enviadas à lixeira:    {resultados['duplicatas_lixeira']}")
    print(f"   • Novos metadados criados em Fontes: {resultados['novos_metadados_criados']}")
    print(f"   • Arquivos aguardando fichamento:    {resultados['aguardando_fichamento']}")
    print(f"   • Arquivos fichados e arquivados:    {resultados['movidos_fichados']}")
    print("=" * 72)

    if (resultados["novos_metadados_criados"] > 0 or resultados["movidos_fichados"] > 0) and not dry_run:
        script_sinc = VAULT / ".claude" / "skills" / "fichamento-pandora" / "scripts" / "sincronizar_cofre.py"
        if script_sinc.exists():
            print("\n🔄 Sincronizando cofre...")
            import subprocess
            subprocess.run([sys.executable, str(script_sinc)], cwd=str(VAULT))

    return resultados


def main():
    parser = argparse.ArgumentParser(description="Ingestão e movimentação multiformato (PDF, Word, Texto, Imagem).")
    parser.add_argument("--dry-run", action="store_true", help="Simula sem mover arquivos.")
    args = parser.parse_args()

    processar_fluxo_multiformato(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
