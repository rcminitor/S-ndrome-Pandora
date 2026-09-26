"""
Teste rápido da IA configurada no .env — faz o mesmo tipo de pedido que o leitor
(uma tradução curta em JSON) e mostra se funcionou. Não mostra a chave.
    python testar_ia.py
"""
from pydantic import BaseModel

import ia
import leitor_artigos as L


class Teste(BaseModel):
    traducao: str


cfg = L.CFG
print(f"IA principal: {cfg.get('PROVEDOR') or '?'} · modelo: {cfg.get('MODELO_TRADUTOR')}")
print(f"Reserva paga: {'sim' if ia.tem_reserva(cfg) else 'não'}\n")
try:
    obj, tok = ia.com_reserva(cfg, lambda: ia.pedir_json(
        cfg, "tradutor", 400, "Você traduz textos científicos para o português do Brasil.",
        'Traduza: "Cats with FIC had significantly smaller adrenal glands." Formato: {"traducao": "..."}', Teste),
        "teste")
    print(f"✓ Funcionou ({tok} tokens){' — pela RESERVA PAGA' if ia.usando_reserva() else ''}:\n  {obj.traducao}")
except Exception as e:
    print(f"✗ Falhou: {type(e).__name__}: {str(e)[:400]}")
