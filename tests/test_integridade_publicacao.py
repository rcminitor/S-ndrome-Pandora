"""Travas para o acervo publicado e para as abas Estado/Fichamentos."""
import json
from pathlib import Path
import unittest


RAIZ = Path(__file__).resolve().parents[1]


def ler_array_js(nome, variavel):
    texto = (RAIZ / nome).read_text(encoding="utf-8-sig")
    prefixo = f"window.{variavel} ="
    inicio = texto.index(prefixo) + len(prefixo)
    return json.loads(texto[inicio:].strip().removesuffix(";"))


class IntegridadePublicacaoTeste(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventario = ler_array_js("dados_inventario.js", "DADOS_INVENTARIO")
        cls.pdfs = ler_array_js("dados_pdfs.js", "DADOS_PDFS")
        cls.fichamentos = ler_array_js("dados_fichamentos.js", "DADOS_FICHAMENTOS")["fichamentos"]

    def test_inventario_publica_somente_fontes_com_pdf(self):
        caminhos_manifesto = {p["arquivo"].replace("\\", "/") for p in self.pdfs}
        caminhos = [a["arquivo"].replace("\\", "/") for a in self.inventario]
        self.assertEqual(67, len(self.inventario))
        self.assertTrue(all(p.startswith("PDF/") for p in caminhos))
        self.assertEqual(len(caminhos), len(set(p.casefold() for p in caminhos)))
        self.assertTrue(set(caminhos).issubset(caminhos_manifesto))
        self.assertTrue(all((RAIZ / p).is_file() for p in caminhos))

    def test_codigos_e_fichamentos_nao_se_descolam(self):
        codigos = {str(a["codigo"]) for a in self.inventario}
        fichados = {str(f["codigo"]) for f in self.fichamentos}
        self.assertEqual(57, len(codigos & fichados))
        self.assertEqual({"55"}, fichados - codigos)
        self.assertTrue({"11", "20", "34", "38", "41", "48", "54"}.issubset(codigos))
        self.assertTrue({"N35", "N36", "N38", "N42", "N44", "N45"}.issubset(codigos))
        self.assertTrue({"N33", "N34", "N37", "N39", "N40", "N41", "N43"}.isdisjoint(codigos))

    def test_codigo_48_continua_ligado_ao_fichamento_correto(self):
        por_codigo = {str(a["codigo"]): a for a in self.inventario}
        self.assertIn("Etiopathogenesis", por_codigo["48"]["titulo"])
        self.assertIn("current understanding", por_codigo["N45"]["titulo"].lower())

    def test_estado_e_fichamentos_sao_renderizados_dos_dados(self):
        html = (RAIZ / "index.html").read_text(encoding="utf-8")
        app = (RAIZ / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="eaConteudo"', html)
        self.assertIn('id="eaCount"', html)
        self.assertIn('id="fiCount"', html)
        self.assertNotIn("function initTabs()", app)
        self.assertNotIn("<th>#43</th><th>#51</th>", html)


if __name__ == "__main__":
    unittest.main()
