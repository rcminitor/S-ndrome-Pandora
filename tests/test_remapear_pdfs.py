import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "painel_local"))

from remapear_pdfs import remapear  # noqa: E402


class RemapearPdfsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cofre = Path(self._tmp.name)
        (self.cofre / "Fontes").mkdir()
        (self.cofre / "PDF" / "Nova").mkdir(parents=True)
        (self.cofre / "PDF" / "Nova" / "a.pdf").write_bytes(b"%PDF")

    def tearDown(self):
        self._tmp.cleanup()

    def _nota(self, nome, pdf):
        arq = self.cofre / "Fontes" / nome
        arq.write_text(f"---\ncodigo: \"1\"\n---\n- **PDF:** [[{pdf}]]\n- outra linha\n", encoding="utf-8")
        return arq

    def test_simulacao_nao_grava(self):
        nota = self._nota("1.md", "PDF/Velha/a.pdf")
        antes = nota.read_text(encoding="utf-8")
        remapeados, ausentes, ambiguos = remapear(self.cofre)
        self.assertEqual(remapeados, [("1.md", "PDF/Velha/a.pdf", "PDF/Nova/a.pdf")])
        self.assertEqual(nota.read_text(encoding="utf-8"), antes)

    def test_grava_so_a_linha_do_pdf(self):
        nota = self._nota("1.md", "PDF/Velha/a.pdf")
        remapear(self.cofre, gravar=True)
        self.assertIn("[[PDF/Nova/a.pdf]]", nota.read_text(encoding="utf-8"))
        self.assertIn("- outra linha", nota.read_text(encoding="utf-8"))

    def test_ausente_e_ambiguo_nao_mudam(self):
        self._nota("1.md", "PDF/Velha/inexistente.pdf")
        (self.cofre / "PDF" / "Outra").mkdir()
        (self.cofre / "PDF" / "Outra" / "a.pdf").write_bytes(b"%PDF")
        self._nota2 = (self.cofre / "Fontes" / "2.md")
        self._nota2.write_text("- **PDF:** [[PDF/Velha/a.pdf]]\n", encoding="utf-8")
        remapeados, ausentes, ambiguos = remapear(self.cofre, gravar=True)
        self.assertEqual(remapeados, [])
        self.assertEqual([n for n, _ in ausentes], ["1.md"])
        self.assertEqual([n for n, _ in ambiguos], ["2.md"])


if __name__ == "__main__":
    unittest.main()
