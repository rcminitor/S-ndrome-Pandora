"""
Escolha do modelo com reserva paga
==================================

Todos os agentes pedem o modelo por aqui. A ordem é:
  1. o principal (ex.: OmniRoute, combo gratuito);
  2. se ele falhar (limite estourado, fora do ar, chave recusada...), a
     RESERVA paga (ex.: chave da Anthropic) — automaticamente, sem perguntar.

Depois que a reserva entra, ela vale por RESERVA_MINUTOS (padrão 30) — para
não ficar batendo no gratuito que já acabou — e então o gratuito é tentado de
novo. Cada troca é avisada no registro, para você saber quando está gastando.

Configuração no .env desta pasta:
  RESERVA_API_KEY=sk-ant-... (Anthropic) ou sk-... (OpenAI)   (vazio = sem reserva)
  RESERVA_MODELO_FORTE=anthropic/claude-sonnet-5
  RESERVA_MODELO_BARATO=anthropic/claude-haiku-4-5-20251001
  RESERVA_MINUTOS=30
"""
from __future__ import annotations

import time

ESTADO = {"reserva": False, "desde": 0.0, "minutos": 30.0}

# papel → (chave do modelo principal no .env, qual modelo da reserva usar)
PAPEIS = {
    "forte": ("MODELO_TUTOR", "RESERVA_MODELO_FORTE"),
    "orientador": ("MODELO_ORIENTADOR", "RESERVA_MODELO_FORTE"),
    "barato": ("MODELO_BARATO", "RESERVA_MODELO_BARATO"),
    "tradutor": ("MODELO_TRADUTOR", "RESERVA_MODELO_BARATO"),
}
PADRAO_RESERVA = {
    "RESERVA_MODELO_FORTE": "anthropic/claude-sonnet-5",
    "RESERVA_MODELO_BARATO": "anthropic/claude-haiku-4-5-20251001",
}


def tem_reserva(cfg: dict) -> bool:
    return bool(cfg.get("RESERVA_API_KEY"))


def usando_reserva() -> bool:
    if ESTADO["reserva"] and time.time() - ESTADO["desde"] > ESTADO["minutos"] * 60:
        ESTADO["reserva"] = False                       # passou o prazo: volta a tentar o gratuito
        print("  ↺ voltando a tentar o modelo gratuito")
    return ESTADO["reserva"]


PADRAO_RESERVA_OPENAI = {
    "RESERVA_MODELO_FORTE": "openai/gpt-5-mini",
    "RESERVA_MODELO_BARATO": "openai/gpt-5-nano",
}


def _limites(modelo: str, max_tokens: int, temperature: float) -> dict:
    """GPT-5 em diante e a série o (OpenAI) raciocinam: exigem max_completion_tokens e não aceitam
    temperatura. Os demais usam max_tokens + temperatura."""
    import re
    nome = modelo.rsplit("/", 1)[-1].lower()
    g = re.match(r"^gpt-(\d+)", nome)
    if re.match(r"^o\d", nome) or (g and int(g.group(1)) >= 5):
        return {"max_completion_tokens": max_tokens, "reasoning_effort": "low"}
    return {"max_tokens": max_tokens, "temperature": temperature}


def criar_llm(cfg: dict, papel: str, max_tokens: int, temperature: float = 0.2):
    from crewai import LLM
    chave_modelo, chave_reserva = PAPEIS[papel]
    if usando_reserva():
        chave = cfg["RESERVA_API_KEY"]
        anthropic = chave.startswith("sk-ant-")          # sk-ant-… = Anthropic; outro sk-… = OpenAI
        padroes = PADRAO_RESERVA if anthropic else PADRAO_RESERVA_OPENAI
        modelo = cfg.get(chave_reserva) or ""
        if modelo.startswith("anthropic/") != anthropic:  # modelo do .env é de outra empresa
            modelo = padroes[chave_reserva]
        if not anthropic:
            max_tokens += int(cfg.get("FOLGA_RACIOCINIO") or 6000)
        return LLM(model=modelo, api_key=chave, **_limites(modelo, max_tokens, temperature))
    modelo = cfg.get(chave_modelo) or cfg.get("MODELO_TUTOR" if papel == "orientador" else "MODELO_BARATO")
    if not modelo.startswith("anthropic/"):
        # modelos que "pensam" antes de responder (Gemini, GPT-5…) gastam parte do limite
        # raciocinando; sem essa folga a resposta sai cortada (LengthFinishReasonError)
        max_tokens += int(cfg.get("FOLGA_RACIOCINIO") or 6000)
    extra = {}
    if cfg.get("LLM_BASE_URL"):
        extra["base_url"] = cfg["LLM_BASE_URL"]
    if cfg.get("LLM_API_KEY"):
        extra["api_key"] = cfg["LLM_API_KEY"]
    return LLM(model=modelo, **_limites(modelo, max_tokens, temperature), **extra)


def com_reserva(cfg: dict, tarefa, descricao: str = "tarefa"):
    """Roda tarefa(); se o modelo principal falhar e houver reserva, repete com a paga."""
    try:
        return tarefa()
    except Exception as erro:
        if usando_reserva() or not tem_reserva(cfg):
            raise
        motivo = str(erro).splitlines()[0][:160] if str(erro) else type(erro).__name__
        print(f"  ⚠ modelo gratuito falhou em '{descricao}' ({type(erro).__name__}: {motivo})")
        ESTADO["minutos"] = float(cfg.get("RESERVA_MINUTOS") or 30)
        print(f"  → usando a RESERVA PAGA pelos próximos {ESTADO['minutos']:.0f} minutos")
        ESTADO.update(reserva=True, desde=time.time())
        return tarefa()


def pedir_json(cfg: dict, papel: str, max_tokens: int, sistema: str, pedido: str, Modelo):
    """Pedido simples (sem 'resposta estruturada' do provedor): o modelo devolve texto com
    um JSON dentro e nós validamos. Funciona igual no OmniRoute e na Anthropic.
    Devolve (objeto validado, tokens)."""
    import json
    import re
    llm = criar_llm(cfg, papel, max_tokens, temperature=0)
    texto = str(llm.call([{"role": "system", "content": sistema},
                          {"role": "user", "content": pedido + "\n\nResponda SOMENTE com o JSON, sem comentários."}]))
    bloco = re.search(r"\{.*\}", re.sub(r"```(?:json)?", "", texto), re.S)
    if not bloco:
        raise ValueError(f"o modelo não devolveu JSON (resposta: {texto[:150]!r})")
    try:
        obj = Modelo.model_validate(json.loads(bloco.group(0)))
    except Exception as e:
        raise ValueError(f"JSON incompleto ou inválido — resposta cortada? ({type(e).__name__})") from e
    try:
        tokens = int(llm.get_token_usage_summary().total_tokens)
    except Exception:
        tokens = (len(sistema) + len(pedido) + len(texto)) // 4
    return obj, tokens
