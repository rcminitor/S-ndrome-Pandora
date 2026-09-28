from pathlib import Path
import sys
import unittest


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel_local"))
from guardiao_acervo import validar_dados, validar_publicacao  # noqa: E402


class GuardiaoAcervoTeste(unittest.TestCase):
    def test_publicacao_atual_e_integra(self):
        rel = validar_publicacao(RAIZ)
        self.assertTrue(rel.ok, rel.texto())
        self.assertGreater(rel.numeros["fontes"], 0)

    def test_bloqueia_fichamento_orfao_e_pdf_ausente(self):
        inventario = [{"codigo": "1", "arquivo": "PDF/a.pdf", "status": "fichamento concluido"}]
        pdfs = [{"arquivo": "PDF/a.pdf"}]
        fichamentos = [{"codigo": "2"}]
        rel = validar_dados(inventario, pdfs, fichamentos, lambda _: False)
        self.assertFalse(rel.ok)
        self.assertTrue(any("orfao" in e for e in rel.erros))
        self.assertTrue(any("inexistente" in e for e in rel.erros))
        self.assertTrue(any("status concluido" in e for e in rel.erros))

    def test_contagens_nao_sao_fixas(self):
        inventario = [{"codigo": "X", "arquivo": "PDF/x.pdf", "status": "arquivo obtido"}]
        pdfs = [{"arquivo": "PDF/x.pdf"}]
        rel = validar_dados(inventario, pdfs, [], lambda _: True, lambda _: b"%PDF-")
        self.assertTrue(rel.ok, rel.texto())
        self.assertEqual({"fontes": 1, "pdfs_autorizados": 1, "fichamentos": 0}, rel.numeros)

    def test_bloqueia_duplicata_por_titulo_ou_doi_mesmo_com_pdf_diferente(self):
        inventario = [
            {"codigo": "1", "titulo": "Mesmo artigo", "referencia": "DOI: 10.1234/teste", "arquivo": "PDF/a.pdf"},
            {"codigo": "2", "titulo": "Mesmo Artigo", "referencia": "doi: 10.1234/teste", "arquivo": "PDF/b.pdf"},
        ]
        pdfs = [{"arquivo": "PDF/a.pdf"}, {"arquivo": "PDF/b.pdf"}]
        rel = validar_dados(inventario, pdfs, [], lambda _: True, lambda _: b"%PDF-")
        self.assertFalse(rel.ok)
        self.assertTrue(any("titulo duplicado" in e for e in rel.erros))
        self.assertTrue(any("DOI duplicado" in e for e in rel.erros))

    def test_bloqueia_pdf_publicado_sem_fonte_ativa(self):
        inventario = [{"codigo": "1", "arquivo": "PDF/a.pdf", "status": "arquivo obtido"}]
        pdfs = [{"arquivo": "PDF/a.pdf"}, {"arquivo": "PDF/material-de-apoio.pdf"}]
        rel = validar_dados(inventario, pdfs, [], lambda _: True, lambda _: b"%PDF-")
        self.assertFalse(rel.ok)
        self.assertTrue(any("sem fonte ativa" in e for e in rel.erros))


if __name__ == "__main__":
    unittest.main()
