"""Regressões estruturais do painel publicado, sem abrir navegador."""
from html.parser import HTMLParser
from pathlib import Path
import unittest


RAIZ = Path(__file__).resolve().parents[1]


class InventarioHtml(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.tabs = []
        self.destinos = []

    def handle_starttag(self, _tag, attrs):
        dados = dict(attrs)
        if dados.get("id"):
            self.ids.append(dados["id"])
        if dados.get("data-tab"):
            self.tabs.append(dados["data-tab"])
        if dados.get("data-goto"):
            self.destinos.append(dados["data-goto"])


class InterfacePainel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (RAIZ / "index.html").read_text(encoding="utf-8")
        cls.app = (RAIZ / "app.js").read_text(encoding="utf-8")
        cls.js = (RAIZ / "painel.js").read_text(encoding="utf-8")
        cls.tema = (RAIZ / "tema.css").read_text(encoding="utf-8")
        cls.doc = InventarioHtml()
        cls.doc.feed(cls.html)

    def test_ids_sao_unicos(self):
        repetidos = sorted({item for item in self.doc.ids if self.doc.ids.count(item) > 1})
        self.assertEqual(repetidos, [])

    def test_botoes_e_atalhos_apontam_para_paineis_existentes(self):
        ids = set(self.doc.ids)
        self.assertEqual(sorted(set(self.doc.tabs) - ids), [])
        self.assertEqual(sorted(set(self.doc.destinos) - ids), [])

    def test_atalhos_fixos_do_painel_estao_presentes(self):
        for destino in ("tab-registro", "tab-guia", "tab-roadmap", "tab-nucleos"):
            self.assertIn(f'data-goto="{destino}"', self.html)
        self.assertIn('data-modal="modalKpiAjuda"', self.html)

    def test_inicializacao_e_dados_sao_resilientes(self):
        self.assertIn("function lerArray", self.js)
        self.assertIn("function executarEtapa", self.js)
        self.assertIn("Array.isArray(window.DADOS_INVENTARIO)", self.js)

    def test_barras_de_navegacao_sao_fixadas(self):
        self.assertIn(".tab-nav-wrapper {\n  position: sticky;", self.tema)
        self.assertIn("#tab-painel .pn-toolbar {\n  position: sticky;", self.tema)

    def test_estado_da_arte_tem_nome_completo_e_cor_estavel(self):
        self.assertIn(
            'data-goto="tab-estadoarte">Estado da Arte</a>',
            self.html,
        )
        self.assertIn(
            'Estado da Arte <span class="tab-badge" id="eaCount">0</span>',
            self.html,
        )
        self.assertIn(
            '.tab-btn[data-tab="tab-estadoarte"]',
            self.tema,
        )

    def test_painel_nao_repete_a_galeria_de_recursos(self):
        self.assertNotIn("Galeria de recursos", self.html)
        self.assertIn('id="tab-galeria"', self.html)

    def test_acervo_oferece_inclusao_validada_de_pdf(self):
        self.assertIn('id="addPdfBtn"', self.html)
        self.assertIn('accept="application/pdf,.pdf"', self.html)
        self.assertIn("/api/acervo/adicionar", self.app)
        self.assertIn("new FormData(form)", self.app)
        self.assertIn("modal.classList.add('open')", self.app)
        self.assertIn('id="inboxPdf"', self.html)
        self.assertIn("/api/acervo/entrada", self.app)
        self.assertIn("data.publicacao.cofre.commit", self.app)

    def test_acervo_ordena_codigos_em_ordem_numerica_crescente(self):
        self.assertIn("function compareArticleCodes", self.app)
        self.assertIn("}).sort(compareArticleCodes);", self.app)

    def test_todas_as_abas_usam_somente_o_acervo_com_pdf(self):
        fichamentos = (RAIZ / "fichamentos.js").read_text(encoding="utf-8")
        estado = (RAIZ / "estadoarte.js").read_text(encoding="utf-8")
        painel = (RAIZ / "painel.js").read_text(encoding="utf-8")
        self.assertIn("window.PANDORA_ACERVO", self.app)
        self.assertIn("window.PANDORA_ACERVO", fichamentos)
        self.assertIn("window.PANDORA_ACERVO", estado)
        self.assertIn("window.PANDORA_ACERVO", painel)
        self.assertIn('id="nucleo1Count"', self.html)
        self.assertIn('id="nucleo2Count"', self.html)
        self.assertNotIn("Núcleo 1 Proposto (22 Fontes)", self.html)
        self.assertNotIn("Núcleo 2 Proposto (42 Fontes)", self.html)

    def test_acervo_tem_diagnostico_e_retirada_segura(self):
        self.assertIn('id="acervoHealthBtn"', self.html)
        self.assertIn('id="acervoHealthModal"', self.html)
        self.assertIn('id="drawerRetirarBtn"', self.html)
        self.assertIn("/api/acervo/saude", self.app)
        self.assertIn("/api/acervo/retirar", self.app)
        self.assertIn("Digite ${codigo} para confirmar", self.app)


if __name__ == "__main__":
    unittest.main()
