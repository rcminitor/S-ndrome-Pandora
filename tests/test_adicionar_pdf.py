import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace

import pymupdf
from werkzeug.datastructures import FileStorage


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel_local"))
from adicionar_pdf import AdicionadorPDF, ErroAdicao  # noqa: E402


def _arquivo_pdf(nome="fonte.pdf", texto="PDF de teste"):
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), texto)
    conteudo = doc.tobytes()
    doc.close()
    return FileStorage(stream=io.BytesIO(conteudo), filename=nome, content_type="application/pdf")


def _js(variavel, valor):
    return f"window.{variavel} = " + json.dumps(valor, ensure_ascii=False) + ";\n"


class AdicionarPdfTeste(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.cofre = self.base / "cofre"
        self.painel = self.base / "painel"
        (self.cofre / "Fontes").mkdir(parents=True)
        (self.cofre / "PDF").mkdir()
        self.painel.mkdir()
        self.dados = {
            "codigo": "68", "titulo": "Fonte acadêmica de teste", "ano": "2025",
            "nucleo": "Núcleo 2", "fase": "Ler depois", "tipo_documento": "Artigo",
            "tema": "Teste", "referencia": "AUTOR. Fonte acadêmica de teste. 2025.",
        }

    def tearDown(self):
        self.tmp.cleanup()

    def _sincronizador_aprovado(self, cofre, painel, escrever):
        self.assertTrue(escrever)
        caminho = "PDF/A_classificar/fonte.pdf"
        item = {"codigo": "68", "titulo": self.dados["titulo"], "arquivo": caminho}
        pdf = {"pasta": "PDF/A_classificar", "nome": "fonte", "arquivo": caminho, "kb": 1}
        (painel / "dados_inventario.js").write_text(_js("DADOS_INVENTARIO", [item]), encoding="utf-8")
        (painel / "dados_pdfs.js").write_text(_js("DADOS_PDFS", [pdf]), encoding="utf-8")
        return 0

    def test_cria_pdf_e_nota_somente_apos_validacao(self):
        adicionador = AdicionadorPDF(self.cofre, self.painel, self._sincronizador_aprovado)
        resultado = adicionador.adicionar(_arquivo_pdf(), self.dados)
        self.assertEqual("68", resultado["item"]["codigo"])
        self.assertTrue((self.cofre / "PDF/A_classificar/fonte.pdf").is_file())
        notas = list((self.cofre / "Fontes").glob("68 *.md"))
        self.assertEqual(1, len(notas))
        self.assertIn("⚠️ **A CONFERIR no artigo**", notas[0].read_text(encoding="utf-8"))

    def test_recusa_arquivo_que_nao_e_pdf(self):
        adicionador = AdicionadorPDF(self.cofre, self.painel, self._sincronizador_aprovado)
        falso = FileStorage(stream=io.BytesIO(b"nao e pdf"), filename="fonte.pdf")
        with self.assertRaisesRegex(ErroAdicao, "cabeçalho"):
            adicionador.adicionar(falso, self.dados)
        self.assertEqual([], list((self.cofre / "Fontes").glob("*.md")))

    def test_reverte_pdf_e_nota_quando_guardiao_recusa(self):
        adicionador = AdicionadorPDF(self.cofre, self.painel, lambda *_: 1)
        with self.assertRaisesRegex(ErroAdicao, "Guardião recusou"):
            adicionador.adicionar(_arquivo_pdf(), self.dados)
        self.assertEqual([], list((self.cofre / "Fontes").glob("*.md")))
        self.assertEqual([], list((self.cofre / "PDF").rglob("*.pdf")))

    def test_recusa_codigo_duplicado(self):
        (self.cofre / "Fontes/68 Existente.md").write_text("---\ncodigo: 68\n---\n", encoding="utf-8")
        adicionador = AdicionadorPDF(self.cofre, self.painel, self._sincronizador_aprovado)
        with self.assertRaisesRegex(ErroAdicao, "já existe"):
            adicionador.adicionar(_arquivo_pdf(), self.dados)

    def test_recusa_titulo_duplicado_mesmo_com_outro_codigo(self):
        (self.cofre / "Fontes/1 Existente.md").write_text(
            '---\ncodigo: "1"\ntitulo: "Fonte acadêmica de teste"\n---\n', encoding="utf-8"
        )
        dados = {**self.dados, "codigo": "69"}
        adicionador = AdicionadorPDF(self.cofre, self.painel, self._sincronizador_aprovado)
        with self.assertRaisesRegex(ErroAdicao, "mesmo título"):
            adicionador.adicionar(_arquivo_pdf(), dados)

    def test_recusa_doi_duplicado_encontrado_no_pdf(self):
        (self.cofre / "Fontes/1 Existente.md").write_text(
            '---\ncodigo: "1"\ntitulo: "Outra fonte"\n---\nDOI: 10.1234/teste.2025.1\n',
            encoding="utf-8",
        )
        dados = {**self.dados, "codigo": "69", "titulo": "Título diferente", "referencia": ""}
        adicionador = AdicionadorPDF(self.cofre, self.painel, self._sincronizador_aprovado)
        with self.assertRaisesRegex(ErroAdicao, "DOI"):
            adicionador.adicionar(_arquivo_pdf(texto="DOI 10.1234/teste.2025.1"), dados)

    def test_move_pdf_da_caixa_de_entrada_apos_aprovacao(self):
        origem = self.cofre / "PDF/_Entrada/fonte.pdf"
        origem.parent.mkdir()
        arquivo = _arquivo_pdf()
        origem.write_bytes(arquivo.stream.read())
        adicionador = AdicionadorPDF(self.cofre, self.painel, self._sincronizador_aprovado)
        adicionador.adicionar(SimpleNamespace(filename=origem.name), self.dados, origem_movel=origem)
        self.assertFalse(origem.exists())
        self.assertTrue((self.cofre / "PDF/A_classificar/fonte.pdf").is_file())

    def test_restaura_pdf_na_entrada_quando_guardiao_recusa(self):
        origem = self.cofre / "PDF/_Entrada/fonte.pdf"
        origem.parent.mkdir()
        arquivo = _arquivo_pdf()
        origem.write_bytes(arquivo.stream.read())
        adicionador = AdicionadorPDF(self.cofre, self.painel, lambda *_: 1)
        with self.assertRaisesRegex(ErroAdicao, "Guardião recusou"):
            adicionador.adicionar(SimpleNamespace(filename=origem.name), self.dados, origem_movel=origem)
        self.assertTrue(origem.is_file())
        self.assertFalse((self.cofre / "PDF/A_classificar/fonte.pdf").exists())


if __name__ == "__main__":
    unittest.main()
