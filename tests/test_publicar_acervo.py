import sys
import subprocess
import tempfile
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel_local"))
from publicar_acervo import PublicadorAcervo  # noqa: E402


class PublicadorFalso(PublicadorAcervo):
    def __init__(self, cofre, painel):
        super().__init__(cofre, painel)
        self.chamadas = []

    def _validar(self):
        self.chamadas.append(("validar",))

    def _commit_e_push(self, repo, caminhos, mensagem):
        self.chamadas.append((Path(repo), caminhos, mensagem))
        return {"commit": "abc1234", "remoto": "origin", "ramo": "main"}


class PublicarAcervoTeste(unittest.TestCase):
    def test_publica_somente_nota_dados_e_pdf_da_inclusao(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            cofre, painel = raiz / "cofre", raiz / "painel"
            nota = cofre / "Fontes/68 Fonte.md"
            nota.parent.mkdir(parents=True)
            painel.mkdir()
            nota.write_text("fonte", encoding="utf-8")
            publicador = PublicadorFalso(cofre, painel)
            resultado = publicador.publicar("68", nota, "PDF/A_classificar/fonte.pdf")
            self.assertEqual(("validar",), publicador.chamadas[0])
            self.assertEqual(["Fontes/68 Fonte.md"], publicador.chamadas[1][1])
            self.assertEqual(
                ["dados_inventario.js", "dados_pdfs.js", "dados_fichamentos.js", "index.html",
                 "PDF/A_classificar/fonte.pdf"],
                publicador.chamadas[2][1],
            )
            self.assertEqual("abc1234", resultado["painel"]["commit"])

    def test_commit_real_nao_captura_arquivo_alheio(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            remoto, repo = raiz / "remoto.git", raiz / "repo"
            subprocess.run(["git", "init", "--bare", str(remoto)], check=True, capture_output=True)
            subprocess.run(["git", "clone", str(remoto), str(repo)], check=True, capture_output=True)
            for chave, valor in (("user.name", "Teste"), ("user.email", "teste@example.com")):
                subprocess.run(["git", "-C", str(repo), "config", chave, valor], check=True)
            (repo / "base.txt").write_text("base", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "base.txt"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "base"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "branch", "-M", "main"], check=True)
            subprocess.run(["git", "-C", str(repo), "push", "-u", "origin", "main"], check=True, capture_output=True)
            (repo / "alvo.txt").write_text("alvo", encoding="utf-8")
            (repo / "alheio.txt").write_text("não incluir", encoding="utf-8")
            resultado = PublicadorAcervo(repo, repo)._commit_e_push(repo, ["alvo.txt"], "teste restrito")
            nomes = subprocess.run(
                ["git", "-C", str(repo), "show", "--pretty=", "--name-only", "HEAD"],
                check=True, capture_output=True, text=True,
            ).stdout.splitlines()
            self.assertEqual(["alvo.txt"], nomes)
            self.assertTrue((repo / "alheio.txt").is_file())
            self.assertEqual("main", resultado["ramo"])


if __name__ == "__main__":
    unittest.main()
