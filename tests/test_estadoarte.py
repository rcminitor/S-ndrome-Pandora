"""Estado da arte: validação (nada sem página), gravação no site e no cofre."""
from pathlib import Path
import sys
import tempfile
import unittest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel_local"))
from estadoarte import CRITERIOS, NOTA, EstadoArte  # noqa: E402
from cofre import Cofre  # noqa: E402


def fonte(codigo="50", m="✗", txt=""):
    return {"codigo": codigo, "titulo": "Westropp et al. (2003)",
            "marcas": {c: {"m": m, "txt": txt} for c, _ in CRITERIOS}}


class EstadoArteTeste(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        (self.base / "cofre" / "Notas").mkdir(parents=True)
        (self.base / "cofre" / "Fontes").mkdir()
        (self.base / "cofre" / NOTA).write_text("# Estado da arte\n\n## Tabela 3\n", encoding="utf-8")
        (self.base / "site").mkdir()
        self.ea = EstadoArte(self.base / "site", Cofre(self.base / "cofre", self.base / "leitura"))

    def test_marca_positiva_sem_pagina_e_recusada(self):
        erros = self.ea.validar(fonte(m="✅", txt="20 gatos com FIC"))
        self.assertEqual(len(erros), len(CRITERIOS))
        self.assertFalse((self.base / "site" / "dados_estadoarte.js").exists())

    def test_codigo_invalido(self):
        self.assertTrue(self.ea.validar(fonte(codigo="abc")))

    def test_salva_no_site_e_no_cofre_e_substitui(self):
        self.assertEqual(self.ea.salvar(fonte(m="◐", txt="vivário (p. 68)")), [])
        self.assertEqual(self.ea.salvar(fonte(m="NC")), [])
        dados = self.ea.ler()
        self.assertEqual(len(dados["fontes"]), 1)
        self.assertEqual(dados["fontes"][0]["marcas"]["C1"]["m"], "NC")
        nota = (self.base / "cofre" / NOTA).read_text(encoding="utf-8")
        self.assertIn("<!-- painel:estadoarte:inicio", nota)
        self.assertIn("| #50 |", nota)
        self.assertIn("# Estado da arte", nota)

    def test_ordem_numeros_antes_de_S(self):
        for c in ("S2", "53", "4"):
            self.ea.salvar(fonte(codigo=c))
        self.assertEqual([f["codigo"] for f in self.ea.ler()["fontes"]], ["4", "53", "S2"])

    def test_dados_publicados_tem_10_fontes_validas(self):
        ea = EstadoArte(RAIZ)
        dados = ea.ler()
        self.assertEqual(len(dados["fontes"]), 10)
        for f in dados["fontes"]:
            self.assertEqual(ea.validar(f), [], f["codigo"])


if __name__ == "__main__":
    unittest.main()
