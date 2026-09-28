import sys
import tempfile
import unittest
from pathlib import Path

import pymupdf


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel_local"))
from caixa_entrada_pdf import caminho_seguro, listar_entrada  # noqa: E402
from sincronizar_acervo import _manifesto_pdfs  # noqa: E402


def criar_pdf(caminho: Path, texto="Artigo 2024 DOI 10.1234/teste.2024", titulo="Título sugerido"):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    doc.set_metadata({"title": titulo, "author": "Autora Teste"})
    doc.new_page().insert_text((72, 72), texto)
    doc.save(caminho)
    doc.close()


class CaixaEntradaPdfTeste(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cofre = Path(self.tmp.name)
        (self.cofre / "Fontes").mkdir()
        (self.cofre / "Fontes/7 Fonte.md").write_text("---\ncodigo: 7\n---\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_lista_sugestoes_sem_publicar_pdf_da_entrada(self):
        pdf = self.cofre / "PDF/_Entrada/novo.pdf"
        criar_pdf(pdf)
        resultado = listar_entrada(self.cofre)
        self.assertEqual("8", resultado["codigo_sugerido"])
        self.assertEqual(1, len(resultado["itens"]))
        item = resultado["itens"][0]
        self.assertTrue(item["valido"])
        self.assertEqual("Título sugerido", item["titulo_sugerido"])
        self.assertEqual("10.1234/teste.2024", item["doi_sugerido"])
        manifesto, _ = _manifesto_pdfs(self.cofre)
        self.assertEqual([], manifesto)

    def test_detecta_conteudo_duplicado(self):
        existente = self.cofre / "PDF/Relevantes/existente.pdf"
        entrada = self.cofre / "PDF/_Entrada/copia.pdf"
        criar_pdf(existente)
        entrada.parent.mkdir(parents=True, exist_ok=True)
        entrada.write_bytes(existente.read_bytes())
        item = listar_entrada(self.cofre)["itens"][0]
        self.assertEqual("PDF/Relevantes/existente.pdf", item["duplicado_em"])

    def test_caminho_seguro_nao_aceita_fora_da_entrada(self):
        criar_pdf(self.cofre / "PDF/_Entrada/novo.pdf")
        self.assertEqual("novo.pdf", caminho_seguro(self.cofre, "novo.pdf").name)
        with self.assertRaisesRegex(ValueError, "não encontrado"):
            caminho_seguro(self.cofre, "../fora.pdf")


if __name__ == "__main__":
    unittest.main()
