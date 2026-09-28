import json
from pathlib import Path
import sys
import tempfile
import unittest


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel_local"))
from guardiao_acervo import ler_json_js, validar_publicacao  # noqa: E402
from sincronizar_acervo import sincronizar  # noqa: E402


def _js(variavel, valor):
    return f"window.{variavel} = " + json.dumps(valor, ensure_ascii=False, indent=1) + ";\n"


def _nota(codigo, titulo, pdf):
    return f"""---
codigo: {codigo}
titulo: {titulo}
ano: 2025
nucleo: 2
status: arquivo obtido
tipo_de_estudo: estudo observacional
---

## Arquivo

**PDF:** [[{pdf}]]

## Referência (ABNT)

AUTOR. {titulo}. Revista Teste, 2025.

*Procedência:* ✔️ confirmada na fonte
"""


class SincronizarAcervoTeste(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.cofre = self.base / "cofre"
        self.painel = self.base / "painel"
        (self.cofre / "Fontes").mkdir(parents=True)
        (self.cofre / "Fichamentos").mkdir()
        (self.cofre / "PDF" / "Síndrome CIF").mkdir(parents=True)
        self.painel.mkdir()

        pdf_a = "PDF/Síndrome CIF/a.pdf"
        (self.cofre / pdf_a).write_bytes(b"%PDF-1.4\nfonte a")
        (self.painel / pdf_a).parent.mkdir(parents=True)
        (self.painel / pdf_a).write_bytes(b"%PDF-1.4\nfonte a")
        (self.cofre / "Fontes" / "1 Fonte A.md").write_text(
            _nota("1", "Fonte A", pdf_a), encoding="utf-8"
        )
        inventario = [{
            "codigo": "1", "titulo": "Fonte A corrigida no painel", "arquivo": pdf_a,
            "status": "arquivo obtido", "fichamento": "nao iniciado"
        }]
        manifesto = [{"pasta": "PDF/Síndrome CIF", "nome": "a", "arquivo": pdf_a, "kb": 0}]
        self._gravar("dados_inventario.js", _js("DADOS_INVENTARIO", inventario))
        self._gravar("dados_pdfs.js", _js("DADOS_PDFS", manifesto))
        self._gravar("dados_fichamentos.js", _js("DADOS_FICHAMENTOS", {"atualizado": "", "fichamentos": []}))
        self._gravar("index.html", '<script src="dados_pdfs.js"></script>\n'
                                    '<script src="dados_inventario.js"></script>\n'
                                    '<script src="dados_fichamentos.js"></script>\n')

    def tearDown(self):
        self.tmp.cleanup()

    def _gravar(self, nome, conteudo):
        (self.painel / nome).write_text(conteudo, encoding="utf-8")

    def test_conferencia_nao_altera_e_escrita_inclui_so_fonte_com_pdf(self):
        pdf_b = "PDF/Síndrome CIF/b.pdf"
        (self.cofre / pdf_b).write_bytes(b"%PDF-1.4\nfonte b")
        (self.cofre / "Fontes" / "2 Fonte B.md").write_text(
            _nota("2", "Fonte B", pdf_b), encoding="utf-8"
        )
        (self.cofre / "Fontes" / "3 Sem PDF.md").write_text(
            _nota("3", "Sem PDF", "PDF/Síndrome CIF/ausente.pdf"), encoding="utf-8"
        )
        antes = {p.name: p.read_bytes() for p in self.painel.iterdir() if p.is_file()}

        self.assertEqual(0, sincronizar(self.cofre, self.painel, escrever=False))
        depois = {p.name: p.read_bytes() for p in self.painel.iterdir() if p.is_file()}
        self.assertEqual(antes, depois)

        self.assertEqual(0, sincronizar(self.cofre, self.painel, escrever=True))
        inventario = ler_json_js(self.painel / "dados_inventario.js", "DADOS_INVENTARIO")
        self.assertEqual(["1", "2"], [str(a["codigo"]) for a in inventario])
        self.assertEqual("Fonte A corrigida no painel", inventario[0]["titulo"])
        self.assertTrue((self.painel / pdf_b).is_file())
        self.assertTrue(validar_publicacao(self.painel).ok)

    def test_erro_de_integridade_nao_substitui_arquivos(self):
        inventario_invalido = [{
            "codigo": "1", "titulo": "Fonte A", "arquivo": "PDF/Síndrome CIF/ausente.pdf",
            "status": "arquivo obtido", "fichamento": "nao iniciado"
        }]
        self._gravar("dados_inventario.js", _js("DADOS_INVENTARIO", inventario_invalido))
        (self.cofre / "Fontes" / "1 Fonte A.md").write_text(
            _nota("1", "Fonte A", "PDF/Síndrome CIF/ausente.pdf"), encoding="utf-8"
        )
        inventario_antes = (self.painel / "dados_inventario.js").read_bytes()

        self.assertEqual(1, sincronizar(self.cofre, self.painel, escrever=True))
        self.assertEqual(inventario_antes, (self.painel / "dados_inventario.js").read_bytes())


if __name__ == "__main__":
    unittest.main()
