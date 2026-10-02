# -*- coding: utf-8 -*-
"""
Consulta Cirúrgica de Trechos com Economia Extrema de Tokens (UFC - Romulo).
Cofre Síndrome de Pandora — Custo de IA: ZERO tokens.

Permite localizar em segundos o parágrafo exato que responde à sua dúvida
em qualquer documento (PDF, Word ou Texto), cortando referências bibliográficas
e exibindo o número da página para citação acadêmica precisa.
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

from leitor_documentos import buscar_paragrafos_cirurgicos

def resolver_arquivo(nome_ou_caminho: str | None) -> Path | None:
    if not nome_ou_caminho:
        # Pega o primeiro PDF disponível em PDF/ ou Síndrome CIF
        cands = list((VAULT / "PDF").glob("*.pdf"))
        if not cands:
            cands = list((VAULT / "PDF" / "Síndrome CIF").glob("*.pdf"))
        return cands[0] if cands else None

    p = Path(nome_ou_caminho)
    if p.is_absolute() and p.exists():
        return p

    # Busca em PDF/
    for sub in [VAULT / "PDF", VAULT / "PDF" / "Síndrome CIF", VAULT / "PDF" / "Primordiais", VAULT]:
        cand = sub / nome_ou_caminho
        if cand.exists():
            return cand

    # Busca recursiva por aproximação
    for cand in (VAULT / "PDF").rglob(f"*{nome_ou_caminho}*"):
        if cand.is_file():
            return cand

    return None

def executar_consulta(caminho_arq: Path, pergunta: str, top_k: int = 2):
    print("=" * 70)
    print("🎯 BUSCA CIRÚRGICA DE TRECHOS (Economia de 95%+ em Tokens)")
    print("=" * 70)
    print(f"Documento: {caminho_arq.name}")
    print(f"Pergunta/Termos: \"{pergunta}\"")
    print("=" * 70)

    resultado = buscar_paragrafos_cirurgicos(caminho_arq, pergunta, top_k=top_k)

    print(f"📊 Documento integral: ~{resultado.tokens_documento_inteiro} tokens")
    print(f"⚡ Trechos cirúrgicos:  ~{resultado.tokens_totais_trechos} tokens")
    print(f"💰 Economia de tokens:  {resultado.percentual_economia}%")
    print("=" * 70)

    for i, t in enumerate(resultado.trechos, 1):
        print(f"\n📍 TRECHO {i} — === [PÁGINA {t.pagina} DO DOCUMENTO] ===")
        print(f"   (Relevância: {t.relevancia_score} | Tamanho: ~{t.tokens_estimados} tokens)")
        print("-" * 70)
        print(t.texto.strip())
        print("-" * 70)

    print("\n✅ Trechos prontos para citação com página conferida!")
    print("=" * 70)

def main():
    parser = argparse.ArgumentParser(description="Busca cirúrgica de parágrafos em documentos com economia extrema de tokens.")
    parser.add_argument("termos", nargs="*", help="Pergunta ou palavras-chave para buscar.")
    parser.add_argument("--arquivo", "-a", help="Nome ou caminho do arquivo PDF/Word/Texto.")
    parser.add_argument("--top", "-k", type=int, default=2, help="Quantidade máxima de parágrafos a retornar (padrão: 2).")
    args = parser.parse_args()

    termo_str = " ".join(args.termos).strip()
    if not termo_str:
        try:
            termo_str = input("Digite sua pergunta ou termos de busca (ex: cortisol, estresse, microbiota): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nOperação cancelada.")
            return

    if not termo_str:
        print("Nenhum termo informado.")
        return

    if not args.arquivo:
        try:
            arq_cand = input("Documento específico (ou pressione Enter para o primeiro PDF do cofre): ").strip()
            if arq_cand:
                args.arquivo = arq_cand
        except (EOFError, KeyboardInterrupt):
            pass

    arquivo = resolver_arquivo(args.arquivo)
    if not arquivo:
        print("❌ Nenhum arquivo encontrado para realizar a consulta.")
        return

    executar_consulta(arquivo, termo_str, top_k=args.top)


if __name__ == "__main__":
    main()
