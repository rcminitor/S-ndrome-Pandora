# -*- coding: utf-8 -*-
"""
Calculadora e Demonstrador de Economia de Tokens para Documentos do Cofre.
Cofre Síndrome de Pandora (UFC - Romulo) — Custo de IA: ZERO tokens.

Permite analisar qualquer documento (PDF, Word DOCX, Texto ou Imagem) e exibir:
- Total de páginas/blocos e tokens estimados do documento integral
- Sumário compacto de seções acadêmicas identificadas
- Comparativo:
  * Cenário 1: Envio bruto integral à LLM
  * Cenário 2: Abordagem Inteligente (Metadados + Leitura sob demanda)
  * Cenário 3: Busca Cirúrgica de Parágrafos (95%+ de economia)
"""

import sys
import logging
import warnings
import argparse
from pathlib import Path

warnings.filterwarnings("ignore")
logging.getLogger("pypdf").setLevel(logging.ERROR)

VAULT = Path(r"C:\Users\rcmin\OneDrive\Documents\Pos-Graduacao\Doutorado UFC\Síndrome de Pandora")
sys.path.insert(0, str(VAULT / ".claude" / "skills" / "fichamento-pandora" / "scripts"))

from leitor_documentos import (
    extrair_metadados_documento,
    obter_sumario_compacto,
    calcular_economia,
    buscar_paragrafos_cirurgicos,
    listar_documentos_pasta
)

def analisar_documento(caminho_doc: Path, paginas_consultadas: list[int] | None = None):
    print("=" * 70)
    print("📊 ANÁLISE DE CONSUMO E ECONOMIA DE TOKENS (Multi-Formato)")
    print("=" * 70)
    
    if not caminho_doc.exists():
        print(f"❌ Arquivo não encontrado: {caminho_doc}")
        return

    doc = extrair_metadados_documento(caminho_doc, raiz_projeto=VAULT)
    print(f"Documento: {doc.arquivo}")
    print(f"Formato: {caminho_doc.suffix.upper()} | Total de páginas/blocos: {doc.total_paginas} | Tamanho: {doc.tamanho_bytes} bytes")
    print(f"Tokens estimados (se enviado integralmente): {doc.tokens_estimados_total} tokens\n")
    
    print("--- Sumário Compacto de Metadados (enviado à LLM) ---")
    sumario = obter_sumario_compacto(doc)
    print(sumario)
    
    # Se não passou páginas, simula consulta à página 2 (metodologia) ou 1
    p_alvo = paginas_consultadas or ([min(2, doc.total_paginas)] if doc.total_paginas > 0 else [1])
    relatorio = calcular_economia(doc, p_alvo)
    
    # Busca cirúrgica simulada de teste (ex: metodologia/resultados)
    res_cirurgico = buscar_paragrafos_cirurgicos(caminho_doc, "methodology results diagnosis stress", top_k=2)

    print("\n--- Comparativo de Consumo e Economia de Tokens ---")
    print(f"1. Ingênuo (Enviar documento integral):       {relatorio.tokens_documento_inteiro:5d} tokens")
    print(f"2. Inteligente (Metadados + 1 Página):       {relatorio.tokens_totais_consumidos:5d} tokens")
    print(f"   ├─ Metadados do sumário:                  {relatorio.tokens_apenas_metadados:5d} tokens")
    print(f"   └─ Trecho lido sob demanda (Pág {p_alvo}):    {relatorio.tokens_trecho_consultado:5d} tokens")
    print(f"   └─ Economia líquida:                      {relatorio.tokens_economizados:5d} tokens ({relatorio.percentual_economia}%)")
    print(f"3. Busca Cirúrgica (2 Parágrafos-Chave):     {res_cirurgico.tokens_totais_trechos:5d} tokens")
    print(f"   └─ Economia líquida extrema:              {res_cirurgico.tokens_documento_inteiro - res_cirurgico.tokens_totais_trechos:5d} tokens ({res_cirurgico.percentual_economia}%)")
    print("=" * 70)

def resolver_caminho(arquivo_str: str | None) -> Path | None:
    if not arquivo_str:
        return None
    p = Path(arquivo_str)
    if p.is_absolute() and p.exists():
        return p
    for pasta in [VAULT / "PDF", VAULT / "PDF" / "Síndrome CIF", VAULT / "PDF" / "Primordiais", VAULT]:
        cand = pasta / arquivo_str
        if cand.exists():
            return cand
    for cand in (VAULT / "PDF").rglob(f"*{arquivo_str}*"):
        if cand.is_file():
            return cand
    return None

def main():
    parser = argparse.ArgumentParser(description="Analisa a economia de tokens de documentos no cofre.")
    parser.add_argument("documento", nargs="?", help="Caminho ou nome do documento (PDF, DOCX, TXT, MD, Imagem).")
    args = parser.parse_args()
    
    doc_path = resolver_caminho(args.documento)
    
    if not doc_path:
        # Modo interativo amigável
        print("Deseja analisar qual documento?")
        print("(Pressione ENTER para analisar o primeiro PDF padrão do cofre)")
        try:
            escolha = input("Arquivo ou trecho do nome: ").strip()
            if escolha:
                doc_path = resolver_caminho(escolha)
        except (EOFError, KeyboardInterrupt):
            print("\nOperação cancelada.")
            return

    if not doc_path:
        # Pega o primeiro PDF disponível
        candidatos = list((VAULT / "PDF").glob("*.pdf")) or list((VAULT / "PDF" / "Síndrome CIF").glob("*.pdf"))
        if candidatos:
            doc_path = candidatos[0]
        else:
            print("Nenhum documento encontrado para demonstrar.")
            return

    analisar_documento(doc_path)

if __name__ == "__main__":
    main()

