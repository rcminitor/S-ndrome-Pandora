import json
from pathlib import Path
import sys
import tempfile
import unittest


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel_local"))
from retirar_fonte import ErroRetirada, RetiradorFonte  # noqa: E402


def _js(nome, valor):
    return f"window.{nome} = " + json.dumps(valor, ensure_ascii=False) + ";\n"


NOTA = """---
codigo: "1"
status: "arquivo obtido"
titulo: "Fonte teste"
---
# Fonte teste

## Arquivo
- **PDF:** [[PDF/a.pdf]]
"""


class RetirarFonteTeste(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.cofre = self.base / "cofre"
        self.painel = self.base / "painel"
        (self.cofre / "Fontes").mkdir(parents=True)
        (self.cofre / "Fichamentos").mkdir()
        (self.cofre / "PDF").mkdir()
        self.painel.mkdir()
        (self.cofre / "Fontes/1 Fonte teste.md").write_text(NOTA, encoding="utf-8")
        (self.cofre / "Fichamentos/1 — Fichamento — Fonte teste.md").write_text(
            '---\ncodigo: "1"\n---\ntexto', encoding="utf-8"
        )
        (self.cofre / "PDF/a.pdf").write_bytes(b"%PDF-1.4\nfonte")
        self._publicar_item()

    def _publicar_item(self):
        (self.painel / "dados_inventario.js").write_text(
            _js("DADOS_INVENTARIO", [{"codigo": "1", "arquivo": "PDF/a.pdf"}]), encoding="utf-8"
        )
        (self.painel / "dados_pdfs.js").write_text(
            _js("DADOS_PDFS", [{"arquivo": "PDF/a.pdf"}]), encoding="utf-8"
        )

    def _sincronizar_retirada(self, _cofre, painel, _escrever):
        (painel / "dados_inventario.js").write_text(_js("DADOS_INVENTARIO", []), encoding="utf-8")
        (painel / "dados_pdfs.js").write_text(_js("DADOS_PDFS", []), encoding="utf-8")
        return 0

    def test_retira_pdf_e_preserva_nota_e_fichamento(self):
        resultado = RetiradorFonte(
            self.cofre, self.painel, sincronizar_fn=self._sincronizar_retirada
        ).retirar("1", "1")
        self.assertFalse((self.cofre / "PDF/a.pdf").exists())
        self.assertTrue((self.cofre / resultado["pdf_arquivado"]).is_file())
        nota = (self.cofre / "Fontes/1 Fonte teste.md").read_text(encoding="utf-8")
        self.assertIn('status: "retirado do acervo"', nota)
        self.assertIn("PDF arquivado", nota)
        self.assertTrue((self.cofre / "Fichamentos/1 — Fichamento — Fonte teste.md").is_file())

    def test_confirmacao_errada_nao_altera(self):
        retirador = RetiradorFonte(self.cofre, self.painel, sincronizar_fn=lambda *_: 0)
        with self.assertRaises(ErroRetirada):
            retirador.retirar("1", "2")
        self.assertTrue((self.cofre / "PDF/a.pdf").is_file())

    def test_falha_do_guardiao_restaura_pdf_e_nota(self):
        retirador = RetiradorFonte(self.cofre, self.painel, sincronizar_fn=lambda *_: 1)
        with self.assertRaises(ErroRetirada):
            retirador.retirar("1", "1")
        self.assertTrue((self.cofre / "PDF/a.pdf").is_file())
        nota = (self.cofre / "Fontes/1 Fonte teste.md").read_text(encoding="utf-8")
        self.assertIn('status: "arquivo obtido"', nota)
        self.assertNotIn("Retirado do Acervo", nota)


if __name__ == "__main__":
    unittest.main()
