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


if __name__ == "__main__":
    unittest.main()
