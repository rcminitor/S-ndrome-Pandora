"""
Contexto do cofre para os agentes
=================================

Dá aos agentes o que você já organizou no cofre Obsidian — de forma compacta,
para gastar poucos tokens:

  regras()             → a regra-mãe do CLAUDE.md do cofre + os dois núcleos
  catalogo()           → uma linha por fonte de Fontes\\ (#código, ano, título, status, núcleo)
  fichamentos(texto)   → os fichamentos mais ligados a um texto, resumidos nas seções
                          que importam (problema, resultados, conclusão, onde entra, pendências)
  pendencias()         → "Próxima atividade recomendada" do 00 Índice do cofre
  no_acervo(ref)       → se uma referência citada já é uma fonte sua (por DOI ou título)

Onde fica o cofre: variável COFRE_DIR (o painel passa a mesma pasta que ele usa),
COFRE_DIR no .env, ou o caminho padrão no PC do Romulo. Sem cofre, tudo devolve
vazio e os agentes seguem funcionando como antes.
"""
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

from dotenv import dotenv_values

AQUI = Path(__file__).resolve().parent
PADRAO = Path(r"C:\Users\rcmin\OneDrive\Documents\Pos-Graduacao\Doutorado UFC\Síndrome de Pandora")
_env = dotenv_values(AQUI / ".env")
LIMITES = {
    "catalogo": int(_env.get("CATALOGO_MAX_CHARS") or 6500),
    "fichamento": int(_env.get("FICHAMENTO_MAX_CHARS") or 2200),
    "n_fichamentos": int(_env.get("FICHAMENTOS_POR_PEDIDO") or 2),
}


def raiz() -> Path | None:
    for c in (os.environ.get("COFRE_DIR"), _env.get("COFRE_DIR"), str(PADRAO)):
        if c and (Path(c) / "Fontes").is_dir():
            return Path(c)
    return None


_CACHE: dict[str, tuple] = {}


def _cacheado(nome: str, pasta_ou_arq, gerar):
    """Guarda o resultado até algum arquivo da pasta mudar (o painel fica ligado o dia todo)."""
    p = Path(pasta_ou_arq) if pasta_ou_arq else None
    if not p or not p.exists():
        return gerar()
    arqs = list(p.glob("*.md")) if p.is_dir() else [p]
    marca = (str(p), len(arqs), max((a.stat().st_mtime for a in arqs), default=0))
    if nome in _CACHE and _CACHE[nome][0] == marca:
        return _CACHE[nome][1]
    valor = gerar()
    _CACHE[nome] = (marca, valor)
    return valor


def _n(t: str) -> str:
    t = unicodedata.normalize("NFD", (t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _palavras(t: str) -> set[str]:
    return {p for p in re.findall(r"[a-z0-9]{4,}", _n(t))} - {
        "with", "from", "that", "this", "their", "study", "cats", "feline", "para", "como", "entre", "sobre"}


def _sem_frontmatter(t: str) -> str:
    return re.sub(r"^---\n.*?\n---\n", "", t, count=1, flags=re.S)


# ------------------------------------------------------------------ regras
def regras() -> str:
    r = raiz()
    return _cacheado("regras", r / "CLAUDE.md" if r else None, _regras)


def _regras() -> str:
    r = raiz()
    arq = r / "CLAUDE.md" if r else None
    if not arq or not arq.exists():
        return ""
    t = arq.read_text(encoding="utf-8")
    partes = []
    for titulo in ("## A regra que vale acima de todas", "## Os dois núcleos"):
        m = re.search(re.escape(titulo) + r"(.*?)(?=\n## |\n---)", t, re.S)
        if m:
            partes.append(titulo.lstrip("# ") + ":" + m.group(1).strip())
    return "\n\n".join(partes)[:2500]


# ------------------------------------------------------------------ fontes
def fontes() -> list[dict]:
    r = raiz()
    return _cacheado("fontes", r / "Fontes" if r else None, _fontes)


def _fontes() -> list[dict]:
    r = raiz()
    if not r:
        return []
    saida = []
    for arq in sorted((r / "Fontes").glob("*.md")):
        t = arq.read_text(encoding="utf-8")
        fm = re.match(r"^---\n(.*?)\n---\n", t, re.S)
        campo = (lambda n: (re.search(rf'^{n}:\s*"?(.*?)"?\s*$', fm.group(1), re.M) or [None, ""])[1]) if fm else (lambda n: "")
        abnt = re.search(r"## Referência \(ABNT\)\s*\n>\s*(.+)", t)
        doi = re.search(r"10\.\d{4,9}/[^\s\"<>]+", abnt.group(1) if abnt else "")
        saida.append({"codigo": campo("codigo"), "ano": campo("ano"), "titulo": campo("titulo"),
                      "status": campo("status"), "nucleo": campo("nucleo"), "stem": arq.stem,
                      "doi": doi.group(0).rstrip(".,;").lower() if doi else ""})
    return saida


def catalogo() -> str:
    linhas = [f"#{f['codigo']} ({f['ano']}) {f['titulo'][:90]} — {f['status'][:40]} — {f['nucleo']}" for f in fontes()]
    texto = "\n".join(linhas)
    return texto[:LIMITES["catalogo"]] + ("\n[catálogo cortado no limite]" if len(texto) > LIMITES["catalogo"] else "")


def no_acervo(ref_texto: str, doi: str = "") -> dict | None:
    """A referência citada já é uma fonte do cofre? Casa por DOI; senão, pelo título."""
    doi = (doi or "").lower()
    ref_n = _n(ref_texto)
    ref_p = _palavras(ref_texto)
    for f in fontes():
        if doi and f["doi"] and doi == f["doi"]:
            return f
    for f in fontes():
        tit = _palavras(f["titulo"])
        if len(tit) >= 3 and len(tit & ref_p) / len(tit) >= 0.8 and (not f["ano"].isdigit() or f["ano"] in ref_n):
            return f
    return None


# ------------------------------------------------------------------ fichamentos
SECOES = ("Problema", "Resultados", "Conclus", "Onde entra", "A conferir", "Minha leitura")


def _fichamentos() -> list[dict]:
    r = raiz()
    return _cacheado("fichamentos", r / "Fichamentos" if r else None, _ler_fichamentos)


def _ler_fichamentos() -> list[dict]:
    r = raiz()
    if not r or not (r / "Fichamentos").is_dir():
        return []
    saida = []
    for arq in sorted((r / "Fichamentos").glob("*— Fichamento —*.md")):
        t = _sem_frontmatter(arq.read_text(encoding="utf-8"))
        blocos = re.split(r"\n(?=## )", t)
        escolhidos = [b.strip() for b in blocos if any(s in b.split("\n", 1)[0] for s in SECOES)]
        resumo = "\n\n".join(escolhidos) or t
        saida.append({"nome": arq.stem, "codigo": arq.stem.split(" ", 1)[0], "texto": resumo,
                      "palavras": _palavras(t)})
    return saida


def fichamentos(texto_base: str, n: int | None = None, codigos: list[str] | None = None) -> str:
    """Os n fichamentos mais ligados ao texto (ou os dos códigos pedidos), resumidos."""
    fs = _fichamentos()
    if codigos:
        escolhidos = [f for f in fs if f["codigo"] in codigos]
    else:
        base = _palavras(texto_base)
        escolhidos = sorted(fs, key=lambda f: len(f["palavras"] & base), reverse=True)[: n or LIMITES["n_fichamentos"]]
        escolhidos = [f for f in escolhidos if f["palavras"] & base]
    teto = LIMITES["fichamento"]
    return "\n\n".join(f"### {f['nome']}\n{f['texto'][:teto]}" + ("\n[…resumo cortado]" if len(f["texto"]) > teto else "")
                       for f in escolhidos)


def pendencias() -> str:
    r = raiz()
    arq = r / "00 Índice do cofre.md" if r else None
    if not arq or not arq.exists():
        return ""
    m = re.search(r"## Próxima atividade recomendada(.*?)(?=\n## )", arq.read_text(encoding="utf-8"), re.S)
    return m.group(1).strip()[:1500] if m else ""
