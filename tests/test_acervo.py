import json
import sys
import tempfile
import unittest
from pathlib import Path

import pymupdf


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel_local"))
from acervo import auditar, corrigir  # noqa: E402


def _js(nome, valor):
    return f"window.{nome} = " + json.dumps(valor, ensure_ascii=False) + ";\n"


def _pdf(caminho):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "PDF válido")
    doc.save(caminho)
    doc.close()


class AuditoriaAcervoTeste(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        raiz = Path(self.tmp.name)
        self.cofre, self.painel = raiz / "cofre", raiz / "painel"
        (self.cofre / "Fontes").mkdir(parents=True)
        self.painel.mkdir()
        self.pdf_rel = "PDF/Ativos/fonte.pdf"
        _pdf(self.cofre / self.pdf_rel)
        self.nota = self.cofre / "Fontes/1 Fonte.md"
        self.nota.write_text(
            '''---
codigo: "1"
ano: "2025"
titulo: "Fonte acadêmica"
nucleo: "Núcleo 1"
fase: "Ler depois"
status: "arquivo obtido"
tema: "Tema"
tipo_de_estudo: "artigo"
---
# Fonte acadêmica

## Arquivo
- **PDF:** [[PDF/Antiga/fonte.pdf]]

## Referência (ABNT)
> AUTOR. Fonte acadêmica. 2025.

## Por que ler
Uso acadêmico.

## Como usar na tese
Contextualização.

## Cautelas
Conferir resultados no original.
''', encoding="utf-8")
        item = {
            "codigo": "1", "titulo": "Fonte acadêmica", "ano": "2025", "nucleo": "Núcleo 1",
            "fase": "Ler depois", "status": "arquivo obtido", "grupo": "Tema",
            "tipoEstudo": "artigo", "procedencia": "confirmada", "porQueLer": "Uso acadêmico.",
            "comoUsar": "Contextualização.", "cautelas": "Conferir resultados no original.",
            "arquivo": self.pdf_rel, "fichamento": "", "referencia": "AUTOR. Fonte acadêmica. 2025.",
        }
        (self.painel / "dados_inventario.js").write_text(_js("DADOS_INVENTARIO", [item]), encoding="utf-8")
        (self.painel / "dados_pdfs.js").write_text(_js("DADOS_PDFS", [{
            "pasta": "PDF/Ativos", "nome": "fonte", "arquivo": self.pdf_rel, "kb": 1,
        }]), encoding="utf-8")
        (self.painel / "dados_fichamentos.js").write_text(
            _js("DADOS_FICHAMENTOS", {"atualizado": "", "fichamentos": []}), encoding="utf-8",
        )
        (self.painel / "index.html").write_text(
            '<script src="dados_pdfs.js"></script><script src="dados_inventario.js"></script>'
            '<script src="dados_fichamentos.js"></script>', encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_diagnostica_e_corrige_link_sem_apagar_pdf_extra(self):
        extra = self.cofre / "PDF/Extras/preservar.pdf"
        _pdf(extra)
        antes = auditar(self.cofre, self.painel)
        self.assertTrue(any(a["tipo"] == "link_nota_divergente" for a in antes["achados"]))
        resultado = corrigir(self.cofre, self.painel, publicar=False)
        self.assertIn(f"[[{self.pdf_rel}]]", self.nota.read_text(encoding="utf-8"))
        self.assertTrue(extra.is_file())
        self.assertFalse(any(a["corrigivel"] for a in resultado["depois"]["achados"]))


if __name__ == "__main__":
    unittest.main()
