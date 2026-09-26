"""
Teste rápido da IA configurada no .env — mostra se o modelo responde, se a
resposta vem cortada e quantos tokens foram gastos "pensando".
    python testar_ia.py
Não mostra a chave.
"""
from dotenv import dotenv_values
from pathlib import Path
from openai import OpenAI

cfg = dotenv_values(Path(__file__).with_name(".env"))
base = cfg.get("LLM_BASE_URL") or None
modelo = (cfg.get("MODELO_BARATO") or "").split("/", 1)[-1] if base else None
if not base:
    raise SystemExit("O principal não é um gateway (LLM_BASE_URL vazio): este teste é para o OmniRoute.")
cli = OpenAI(base_url=base, api_key=cfg.get("LLM_API_KEY") or "x")
print(f"Gateway: {base} · modelo: {modelo}\n")
for limite in (300, 4000):
    try:
        r = cli.chat.completions.create(model=modelo, max_tokens=limite, messages=[
            {"role": "user", "content": 'Traduza para o português: "Cats with FIC had smaller adrenal glands." '
                                        'Responda só com JSON: {"traducao": "..."}'}])
        c, u = r.choices[0], r.usage
        pens = getattr(getattr(u, "completion_tokens_details", None), "reasoning_tokens", None)
        print(f"limite {limite}: fim={c.finish_reason} · resposta={u.completion_tokens} tokens "
              f"(pensando: {pens}) · modelo real: {r.model}\n  → {(c.message.content or '')[:150]!r}\n")
    except Exception as e:
        print(f"limite {limite}: ERRO {type(e).__name__}: {str(e)[:200]}\n")
