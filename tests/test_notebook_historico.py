import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "painel_local"))
from flask import Flask
import notebook_bridge as nb


class Historico(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.raiz = Path(tmp.name)
        self.app = Flask(__name__)
        self.app.config['NOTEBOOKLM_HISTORICO'] = str(self.raiz / 'historico')
        self.app.register_blueprint(nb.bp)
        self.client = self.app.test_client()
        self.url = {'base_url': 'http://127.0.0.1:8765'}
        self.caderno = '12345678-1234-1234-1234-123456789abc'
        self.resposta = {'answer': 'Resposta com acentuação [1]',
                         'references': [{'source_id': 'fonte', 'citation_number': 1}],
                         'conversation_id': 'conversa'}

    def perguntar(self):
        with patch.object(nb, 'autenticar'), patch.object(nb, 'configuracao', return_value={
                'cadernos': {'pro': self.caderno}}), patch.object(nb, 'executar', return_value=dict(self.resposta)):
            return self.client.post('/api/notebooklm/perguntar', json={'conta': 'pro', 'prompt': 'Pergunta?'}, **self.url)

    def test_salva_e_recupera_sem_nova_chamada(self):
        r = self.perguntar()
        self.assertEqual(r.status_code, 200)
        ident = r.json['historico_id']
        with patch.object(nb, 'executar') as executar:
            itens = self.client.get('/api/notebooklm/historico?conta=pro', **self.url).json['itens']
            salvo = self.client.get('/api/notebooklm/historico/' + ident, **self.url).json
            executar.assert_not_called()
        self.assertEqual(len(itens), 1)
        self.assertEqual(salvo['references'], self.resposta['references'])
        self.assertEqual(salvo['prompt'], 'Pergunta?')
        self.assertEqual(salvo['caderno'], self.caderno)
        self.assertIn(self.resposta['answer'], (self.raiz/'historico'/ident/'Consulta.md').read_text(encoding='utf-8'))
        self.assertEqual(self.client.get('/api/notebooklm/historico?conta=plus', **self.url).json['itens'], [])

    def test_repetidas_nao_sobrescrevem(self):
        self.assertNotEqual(self.perguntar().json['historico_id'], self.perguntar().json['historico_id'])

    def test_falha_disco_preserva_resposta(self):
        with patch.object(nb, 'salvar_consulta', side_effect=OSError('disco cheio')):
            r = self.perguntar()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json['answer'], self.resposta['answer'])
        self.assertIn('aviso', r.json)

    def test_identificador_invalido(self):
        self.assertEqual(self.client.get('/api/notebooklm/historico/invalido', **self.url).status_code, 400)

    def test_importacao_preserva_id_e_nao_repete_download(self):
        material = {'id': self.caderno, 'status': 'completed', 'type_id': 'audio', 'title': 'Áudio'}
        def baixar(conta, args):
            self.assertEqual(args[0:2], ['download', 'audio'])
            self.assertEqual(args[args.index('-a')+1], material['id'])
            Path(args[2]).write_bytes(b'audio')
            return {}
        with self.app.app_context(), patch.object(nb, 'executar', side_effect=baixar) as executar:
            primeiro = nb.importar_material('pro', self.caderno, material)
            segundo = nb.importar_material('pro', self.caderno, material, {'chave':'abc','nome':'Artigo'})
            self.assertEqual(primeiro['id'], segundo['id'])
            executar.assert_called_once()
        r = self.client.get('/api/notebooklm/importados?artigo=abc', **self.url)
        self.assertEqual(len(r.json['itens']), 1)
        with self.client.get('/api/notebooklm/importados/'+primeiro['id'], **self.url) as r:
            self.assertEqual(r.data, b'audio')

    def test_material_incompleto_nao_baixa(self):
        with self.app.app_context(), patch.object(nb, 'executar') as executar:
            with self.assertRaises(ValueError):
                nb.importar_material('pro', self.caderno, {'id':self.caderno,'status':'in_progress','type_id':'audio'})
            executar.assert_not_called()

    def test_download_falho_nao_aparece_como_importado(self):
        with self.app.app_context(), patch.object(nb, 'executar', side_effect=RuntimeError('rede')):
            with self.assertRaises(RuntimeError):
                nb.importar_material('pro', self.caderno, {'id':self.caderno,'status':'completed','type_id':'audio'})
            self.assertEqual(list(nb.pasta_importados().iterdir()), [])

    def test_filtro_por_artigo_preserva_historico_antigo(self):
        with self.app.app_context():
            nb.salvar_consulta('pro', self.caderno, 'Antiga', self.resposta)
            ident = nb.salvar_consulta('pro', self.caderno, 'Vinculada', self.resposta,
                                      {'chave': 'abc', 'nome': 'Artigo'})
            nb.salvar_consulta('pro', self.caderno, 'Outro', self.resposta,
                               {'chave': 'def', 'nome': 'Outro'})
        itens = self.client.get('/api/notebooklm/historico?conta=pro&artigo=abc', **self.url).json['itens']
        self.assertEqual([i['id'] for i in itens], [ident])
        self.assertEqual(len(self.client.get('/api/notebooklm/historico?conta=pro', **self.url).json['itens']), 3)


if __name__ == '__main__':
    unittest.main()
