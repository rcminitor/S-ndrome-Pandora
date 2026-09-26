"""
Estatísticas do acervo — Síndrome de Pandora
============================================

Lê o inventário do site (dados_inventario.js), calcula estatísticas descritivas
e dois testes de hipótese, e grava dados_estatisticas.js, que a aba
"Estatísticas" do index.html desenha.

Uso (na raiz do repositório):
    pip install pandas scipy
    python analise/estatisticas.py

Regra do projeto: nada é inventado. Anos marcados "NAO CONFIRMADO" ficam fora
dos cálculos de ano, e todo resultado leva o aviso de que os anos vêm do .bib
e ainda não foram conferidos nos PDFs, exceto quando a procedência diz o
contrário.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import pandas as pd
from scipy import stats

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "dados_inventario.js"
SAIDA = RAIZ / "dados_estatisticas.js"


# ----------------------------------------------------------------- leitura
def carregar_inventario() -> pd.DataFrame:
    texto = ENTRADA.read_text(encoding="utf-8-sig")
    inicio, fim = texto.index("["), texto.rindex("]") + 1
    df = pd.DataFrame(json.loads(texto[inicio:fim]))
    df["nucleo_curto"] = df["nucleo"].str.extract(r"Nucleo (\d)")[0].map(
        {"1": "Núcleo 1", "2": "Núcleo 2"}
    )
    df["ano_num"] = pd.to_numeric(df["ano"], errors="coerce")
    df["etapa"] = df["status"].map(
        {
            "ainda nao obtido": "Não obtido",
            "arquivo obtido": "Arquivo obtido",
            "fichamento concluido": "Fichado",
        }
    ).fillna("Outro")
    df["procedencia_cat"] = df["procedencia"].map(classificar_procedencia)
    return df


def classificar_procedencia(p: str) -> str:
    p = (p or "").lower()
    if p.startswith("confirmada") or "preenchida por voce" in p:
        return "Confirmada"
    if p.startswith("parcial"):
        return "Parcial"
    if "conferir" in p:
        return "A conferir"
    return "Sem procedência"


# ---------------------------------------------------------- descritivas
def contagem(serie: pd.Series, ordem: list[str]) -> list[dict]:
    c = serie.value_counts()
    return [{"rotulo": k, "n": int(c.get(k, 0))} for k in ordem]


def anos_por_nucleo(df: pd.DataFrame) -> dict:
    validos = df.dropna(subset=["ano_num"])
    anos = list(range(int(validos["ano_num"].min()), int(validos["ano_num"].max()) + 1))
    tab = pd.crosstab(validos["ano_num"].astype(int), validos["nucleo_curto"]).reindex(anos, fill_value=0)
    return {
        "anos": anos,
        "series": {col: tab[col].astype(int).tolist() for col in ["Núcleo 1", "Núcleo 2"]},
        "sem_ano": int(df["ano_num"].isna().sum()),
    }


def resumo_ano(df: pd.DataFrame) -> list[dict]:
    out = []
    for nuc, g in df.dropna(subset=["ano_num"]).groupby("nucleo_curto"):
        a = g["ano_num"]
        out.append(
            {
                "nucleo": nuc,
                "n": int(a.size),
                "mediana": float(a.median()),
                "q1": float(a.quantile(0.25)),
                "q3": float(a.quantile(0.75)),
                "min": int(a.min()),
                "max": int(a.max()),
                "pct_ultimos_3_anos": round(float((a >= date.today().year - 2).mean() * 100), 1),
            }
        )
    return out


# ---------------------------------------------------------------- testes
def teste_mann_whitney(df: pd.DataFrame) -> dict:
    """O Núcleo 2 (ambiente/tecnologia) é mais recente que o Núcleo 1?"""
    v = df.dropna(subset=["ano_num"])
    a = v.loc[v["nucleo_curto"] == "Núcleo 1", "ano_num"]
    b = v.loc[v["nucleo_curto"] == "Núcleo 2", "ano_num"]
    res = stats.mannwhitneyu(b, a, alternative="greater")
    # tamanho de efeito: correlação rank-bisserial (r = 2U/(n1·n2) − 1)
    r = 2 * res.statistic / (len(a) * len(b)) - 1
    return {
        "nome": "Mann–Whitney U (unilateral)",
        "pergunta": "As fontes do Núcleo 2 são mais recentes que as do Núcleo 1?",
        "n1": int(len(a)),
        "n2": int(len(b)),
        "U": float(res.statistic),
        "p": float(res.pvalue),
        "efeito_nome": "correlação rank-bisserial",
        "efeito": round(float(r), 3),
        "leitura": (
            "p < 0,05 indica que, neste acervo, os anos do Núcleo 2 tendem a ser maiores. "
            "O efeito vai de −1 a 1; acima de 0,5 costuma ser lido como grande. "
            "Isso descreve o acervo que você reuniu, não a literatura inteira."
        ),
    }


def teste_qui_quadrado(df: pd.DataFrame) -> dict:
    """A prioridade de leitura (fase) depende do núcleo?"""
    tab = pd.crosstab(df["nucleo_curto"], df["fase"])
    chi2, p, gl, esperado = stats.chi2_contingency(tab)
    n = int(tab.values.sum())
    v = (chi2 / (n * (min(tab.shape) - 1))) ** 0.5
    celulas_baixas = int((esperado < 5).sum())
    return {
        "nome": "Qui-quadrado de independência",
        "pergunta": "A fase de leitura (Ler primeiro / depois / com cautela) depende do núcleo?",
        "tabela": {
            "linhas": tab.index.tolist(),
            "colunas": tab.columns.tolist(),
            "valores": tab.values.astype(int).tolist(),
        },
        "chi2": round(float(chi2), 3),
        "gl": int(gl),
        "p": float(p),
        "efeito_nome": "V de Cramér",
        "efeito": round(float(v), 3),
        "aviso": (
            f"{celulas_baixas} célula(s) com frequência esperada < 5: o qui-quadrado fica impreciso; "
            "trate o resultado como exploratório."
            if celulas_baixas
            else ""
        ),
        "leitura": (
            "p ≥ 0,05 significa que não há evidência de que a prioridade de leitura dependa do núcleo. "
            "V de Cramér perto de 0 indica associação fraca; acima de 0,3, moderada."
        ),
    }


# ----------------------------------------------------------------- saída
def main() -> None:
    df = carregar_inventario()
    total = len(df)
    fichados = int((df["etapa"] == "Fichado").sum())
    resultado = {
        "gerado_em": date.today().isoformat(),
        "total": total,
        "aviso_geral": (
            "Os anos vêm do inventário (gerado do .bib) e, na maioria, ainda não foram conferidos no PDF. "
            "O agrupamento por núcleo é proposto na tese, não declarado pelos autores."
        ),
        "kpis": {
            "fichados": fichados,
            "pct_fichados": round(fichados / total * 100, 1),
            "com_arquivo": int((df["etapa"] != "Não obtido").sum()),
            "procedencia_confirmada": int((df["procedencia_cat"] == "Confirmada").sum()),
        },
        "funil": contagem(df["etapa"], ["Não obtido", "Arquivo obtido", "Fichado"]),
        "funil_por_nucleo": {
            nuc: contagem(g["etapa"], ["Não obtido", "Arquivo obtido", "Fichado"])
            for nuc, g in df.groupby("nucleo_curto")
        },
        "procedencia": contagem(
            df["procedencia_cat"], ["Confirmada", "Parcial", "A conferir", "Sem procedência"]
        ),
        "fase": contagem(df["fase"], ["Ler primeiro", "Ler depois", "Ler com cautela"]),
        "anos": anos_por_nucleo(df),
        "resumo_ano": resumo_ano(df),
        "testes": [teste_mann_whitney(df), teste_qui_quadrado(df)],
    }
    SAIDA.write_text(
        "// Gerado por analise/estatisticas.py — não edite à mão.\n"
        "window.DADOS_ESTATISTICAS = "
        + json.dumps(resultado, ensure_ascii=False, indent=1)
        + ";\n",
        encoding="utf-8",
    )
    print(f"OK: {SAIDA.name} ({total} registros, {fichados} fichados)")
    for t in resultado["testes"]:
        print(f"  {t['nome']}: p = {t['p']:.4f}, {t['efeito_nome']} = {t['efeito']}")


if __name__ == "__main__":
    main()
