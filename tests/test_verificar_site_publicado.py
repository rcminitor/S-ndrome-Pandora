from pathlib import Path
import sys
import unittest


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel_local"))
from verificar_site_publicado import extrair_js, validar_dados_publicados  # noqa: E402


class VerificarSitePublicadoTeste(unittest.TestCase):
    def test_extrai_objeto_javascript(self):
        self.assertEqual({"ok": True}, extrair_js('window.TESTE = {"ok": true};\n', "TESTE"))

    def test_aprova_conjunto_coerente(self):
        inventario = [{"codigo": "1", "arquivo": "PDF/a.pdf"}]
        pdfs = [{"arquivo": "PDF/a.pdf"}]
        fichas = {"fichamentos": [{"codigo": "1"}]}
        estado = {"fontes": [{"codigo": "1"}]}
        self.assertEqual([], validar_dados_publicados(inventario, pdfs, fichas, estado))

    def test_reprova_fontes_orfas_e_contagens_divergentes(self):
        inventario = [{"codigo": "1", "arquivo": "PDF/a.pdf"}]
        pdfs = []
        fichas = {"fichamentos": [{"codigo": "2"}]}
        estado = {"fontes": [{"codigo": "3"}]}
        erros = " | ".join(validar_dados_publicados(inventario, pdfs, fichas, estado))
        self.assertIn("manifesto", erros)
        self.assertIn("contagem", erros)
        self.assertIn("fichamentos sem PDF ativo: 2", erros)
        self.assertIn("Estado da Arte com fontes sem PDF ativo: 3", erros)


if __name__ == "__main__":
    unittest.main()
