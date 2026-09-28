"""Fichamentos no site: só lê o cofre e não gera commit quando nada mudou."""
from pathlib import Path
import sys
import tempfile
import unittest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel_local"))
from fichamentos import Fichamentos, ler_fichamentos  # noqa: E402

FICH = '---\ntipo: fichamento\ncodigo: "50"\ndata_do_fichamento: 2026-09-26\ntags:\n  - nucleo/1\n---\n\n# Fichamento — X\n\ntexto\n'


class FichamentosTeste(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        b = Path(self.tmp.name)
        (b / "cofre" / "Fichamentos").mkdir(parents=True)
        (b / "cofre" / "Fichamentos" / "50 — Fichamento — Small adrenal.md").write_text(FICH, encoding="utf-8")
        (b / "cofre" / "Fichamentos" / "00 Como usar esta pasta.md").write_text("x", encoding="utf-8")
        (b / "site").mkdir()
        (b / "site" / "PDF").mkdir()
        (b / "site" / "PDF" / "fonte-50.pdf").write_bytes(b"%PDF-1.4\nfonte")
        (b / "site" / "dados_inventario.js").write_text(
            'window.DADOS_INVENTARIO = [{"codigo":"50","arquivo":"PDF/fonte-50.pdf"}];\n',
            encoding="utf-8",
        )
        (b / "site" / "dados_pdfs.js").write_text(
            'window.DADOS_PDFS = [{"arquivo":"PDF/fonte-50.pdf"}];\n', encoding="utf-8",
        )
        self.b = b

    def test_le_metadados_e_ignora_00(self):
        f = ler_fichamentos(self.b / "cofre")
        self.assertEqual(len(f), 1)
        self.assertEqual((f[0]["codigo"], f[0]["nucleo"], f[0]["titulo"]), ("50", "1", "Small adrenal"))
        self.assertTrue(f[0]["md"].startswith("# Fichamento"))

    def test_nao_regrava_sem_mudanca(self):
        fi = Fichamentos(self.b / "site", self.b / "cofre")
        fi.escrever_site()
        antes = fi.js.stat().st_mtime_ns
        fi.escrever_site()
        self.assertEqual(fi.js.stat().st_mtime_ns, antes)

    def test_sem_cofre_nao_escreve(self):
        fi = Fichamentos(self.b / "site", None)
        fi.escrever_site()
        self.assertFalse(fi.js.exists())

    def test_nao_publica_fichamento_sem_fonte_com_pdf_ativo(self):
        (self.b / "cofre" / "Fichamentos" / "51 — Fichamento — Órfão.md").write_text(
            FICH.replace('codigo: "50"', 'codigo: "51"'), encoding="utf-8"
        )
        fi = Fichamentos(self.b / "site", self.b / "cofre")
        fi.escrever_site()
        texto = fi.js.read_text(encoding="utf-8")
        self.assertIn('"codigo": "50"', texto)
        self.assertNotIn('"codigo": "51"', texto)


if __name__ == "__main__":
    unittest.main()
