"""Testes isolados: nunca iniciam o servidor, acessam o cofre ou executam Git."""
import ast
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import Mock, patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel_local"))
from registro import Registro, SITE


def funcoes_servidor():
    # Importar servidor.py inicia rotinas e escreve no cofre real.
    arvore = ast.parse((RAIZ / "painel_local/servidor.py").read_text(encoding="utf-8"))
    nomes = {"secao_path", "salvar_secao", "mover_leitura", "mover", "eu_li"}
    funcoes = [n for n in arvore.body if isinstance(n, ast.FunctionDef) and n.name in nomes]
    for n in funcoes:
        n.decorator_list = []
    ns = dict(Path=Path, shutil=shutil, TRAVA_MOVIMENTO=threading.Lock(),
              jsonify=lambda d: d, request=Mock(), PROG=Mock(), REG=Mock(), atualizar_fila=Mock())
    exec(compile(ast.Module(body=funcoes, type_ignores=[]), "servidor_isolado", "exec"), ns)
    return ns


class Arquivos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.ns = funcoes_servidor()
        self.ler = self.base / "ler"
        self.lido = self.base / "lido"
        self.ler.mkdir()
        self.lido.mkdir()
        self.ns.update(TESE=self.base, PARA_LER=self.ler, LIDO=self.lido)

    def test_criar_repetida_preserva_texto(self):
        p = self.base / "Introducao.md"
        p.write_text("Texto original", encoding="utf-8")
        self.ns["request"].get_json.return_value = dict(nome="Introducao", texto="", criar=True)
        self.assertEqual(self.ns["salvar_secao"]()[1], 409)
        self.assertEqual(p.read_text(encoding="utf-8"), "Texto original")
        self.ns["REG"].publicar_depois.assert_not_called()

    def test_criar_e_salvar(self):
        self.ns["request"].get_json.return_value = dict(nome="Nova", texto="", criar=True)
        self.assertTrue(self.ns["salvar_secao"]()["ok"])
        self.ns["request"].get_json.return_value = dict(nome="Nova", texto="Revisao")
        self.assertTrue(self.ns["salvar_secao"]()["ok"])
        self.assertEqual((self.base / "Nova.md").read_text(), "Revisao")

    def preparar(self):
        pasta = self.ler / "subpasta"
        pasta.mkdir()
        pdf = pasta / "artigo.pdf"
        for nome in ("artigo.pdf", "artigo.leitura.md", "artigo.leitura.json"):
            (pasta / nome).write_bytes(nome.encode())
        return pdf

    def test_mover_conjunto_e_voltar(self):
        pdf = self.preparar()
        novo = self.ns["mover_leitura"](pdf, self.ler, self.lido)
        self.assertFalse(pdf.exists())
        self.assertEqual(len(list(novo.parent.iterdir())), 3)
        volta = self.ns["mover_leitura"](novo, self.lido, self.ler)
        self.assertEqual(volta.read_bytes(), b"artigo.pdf")

    def test_conflito_relatorio_preserva_conjunto_e_registro(self):
        pdf = self.preparar()
        destino = self.lido / "subpasta"
        destino.mkdir()
        conflito = destino / "artigo.leitura.md"
        conflito.write_bytes(b"original")
        self.ns["resolver_id"] = lambda _: pdf
        self.ns["request"].get_json.return_value = dict(id="ler:subpasta/artigo.pdf", para="lido")
        for rota in ("mover", "eu_li"):
            self.assertEqual(self.ns[rota]()[1], 409)
        self.assertEqual(len(list(pdf.parent.iterdir())), 3)
        self.assertEqual(conflito.read_bytes(), b"original")
        self.ns["REG"].humano_li.assert_not_called()

    def test_falha_copia_preserva_originais(self):
        pdf = self.preparar()
        with patch.object(shutil, "copyfileobj", side_effect=OSError("disco cheio")):
            with self.assertRaises(OSError):
                self.ns["mover_leitura"](pdf, self.ler, self.lido)
        self.assertEqual(len(list(pdf.parent.iterdir())), 3)
        self.assertEqual(list((self.lido / "subpasta").iterdir()), [])


class Publicacao(unittest.TestCase):
    def executar(self, codigos):
        reg = Registro(Path("unused"), Path("unused"))
        reg.escrever_site = Mock()
        reg._git = Mock(side_effect=lambda *args: subprocess.CompletedProcess(
            args, codigos.get(args[0], 0), "", "erro simulado"))
        reg._publicar("teste")
        return [c.args[0] for c in reg._git.call_args_list]

    def test_reenvia_sem_novas_alteracoes(self):
        comandos = self.executar({})
        self.assertIn("push", comandos)
        self.assertNotIn("commit", comandos)
        self.assertTrue(SITE["ok"])

    def test_alteracoes_criam_commit(self):
        comandos = self.executar({"diff": 1})
        self.assertLess(comandos.index("commit"), comandos.index("push"))

    def test_erros_nao_indicam_sucesso(self):
        for comando, codigo in (("add", 1), ("diff", 128), ("push", 1)):
            with self.subTest(comando=comando):
                self.executar({comando: codigo})
                self.assertFalse(SITE["ok"])
                self.assertIn(comando, SITE["erro"])
                self.assertFalse(SITE["enviando"])


if __name__ == "__main__":
    unittest.main()
