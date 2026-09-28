import json
from pathlib import Path
import sys
import tempfile
import unittest


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel_local"))
from acervo_ativo import codigos_ativos  # noqa: E402


def _js(nome, valor):
    return f"window.{nome} = " + json.dumps(valor) + ";\n"


class AcervoAtivoTeste(unittest.TestCase):
    def test_exige_inventario_manifesto_e_pdf_fisico(self):
        with tempfile.TemporaryDirectory() as tmp:
            painel = Path(tmp)
            (painel / "PDF").mkdir()
            (painel / "PDF/ok.pdf").write_bytes(b"%PDF-1.4\nok")
            inventario = [
                {"codigo": "1", "arquivo": "PDF/ok.pdf"},
                {"codigo": "2", "arquivo": "PDF/ausente.pdf"},
                {"codigo": "3", "arquivo": "fora.pdf"},
            ]
            manifesto = [
                {"arquivo": "PDF/ok.pdf"},
                {"arquivo": "PDF/ausente.pdf"},
                {"arquivo": "fora.pdf"},
            ]
            (painel / "dados_inventario.js").write_text(
                _js("DADOS_INVENTARIO", inventario), encoding="utf-8"
            )
            (painel / "dados_pdfs.js").write_text(
                _js("DADOS_PDFS", manifesto), encoding="utf-8"
            )
            self.assertEqual({"1"}, codigos_ativos(painel))
