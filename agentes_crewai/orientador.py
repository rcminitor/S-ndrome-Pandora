"""
Agente orientador — debate sobre o texto da tese
================================================

Lê a seção que você escreveu e conversa com você como um orientador:
faz perguntas, pede a fonte de cada afirmação, contra-argumenta e debate.
Usa como base SÓ o seu texto e as leituras já processadas pelo leitor
(arquivos *.leitura.json nas pastas de leitura). Não inventa referência.

Modos:
  questionar — faz 2 ou 3 perguntas sobre o trecho, uma de cada tipo
               (conceito, evidência, ligação com a tese)
  debater    — responde ao seu argumento, discorda quando houver motivo,
               e termina sempre com uma pergunta
  revisar    — aponta afirmações sem fonte, saltos lógicos e lacunas

Economia de tokens: o texto e as leituras vão resumidos com teto de
caracteres; o histórico enviado é só das últimas trocas; a resposta tem
teto de tamanho.

Uso no terminal (o painel local usa as mesmas funções):
    python orientador.py "C:\\...\\Notas\\Tese\\01 Introducao.md"
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import dotenv_values

import contexto_cofre
import ia

AQUI = Path(__file__).resolve().parent
CFG = {
    "MODELO_ORIENTADOR": "",
    "MODELO_TUTOR": "anthropic/claude-sonnet-5",
    "LLM_BASE_URL": "",
    "LLM_API_KEY": "",
    "RESERVA_API_KEY": "",
    "BIBLIOTECA": "",
    "TESE_MAX_CHARS": "6000",
    "LEITURAS_MAX_CHARS": "4000",
    "HISTORICO_TROCAS": "6",
    "MAX_TOKENS_ORIENTADOR": "700",
    **{k: v for k, v in dotenv_values(AQUI / ".env").items() if v is not None},
}

SISTEMA = """Você é o orientador de doutorado do Romulo, cuja tese trata da Síndrome de Pandora em felinos \
(cistite idiopática felina, estresse, eixo HHA, adrenais, ambiente, comportamento, enriquecimento, sensores/IoT e IA).

Seu papel é fazê-lo pensar, não escrever por ele:
- Faça perguntas diretas e curtas. No máximo 3 por mensagem.
- Discorde quando houver motivo e explique por quê. Não elogie por elogiar.
- Peça a fonte de toda afirmação científica sem referência.
- Siga as REGRAS DO COFRE abaixo; são as regras da tese.
- Base de evidência, nesta ordem: FICHAMENTOS DO COFRE (lidos no PDF, com página) e LEITURAS DO PAINEL.
  Só afirme o que um estudo diz se estiver nesses blocos, e cite pelo código (ex.: "#51, p. 387").
- O CATÁLOGO mostra o que ele tem no acervo e o status de cada fonte. Use-o para apontar qual fonte
  ele deveria ler ou fichar para sustentar um trecho — mas sem afirmar o conteúdo de fonte não fichada.
- Nunca invente autor, ano, página ou resultado. Conhecimento geral sem fonte no cofre vai marcado:
  "(conhecimento geral — precisa de fonte)".
- Quando o artigo citado não for a fonte primária do achado, diga qual é a primária e cobre a leitura dela.
- Use as PENDÊNCIAS DO COFRE para lembrar o que ainda falta ler ou conferir.
- Diferencie o que o texto dele afirma, o que as fontes dizem e o que é interpretação sua.
- Responda em português, em até 250 palavras."""

MODOS = {
    "questionar": "Leia o texto e faça de 2 a 3 perguntas: uma sobre conceito, uma sobre evidência e uma sobre a ligação com o objetivo da tese.",
    "debater": "Responda ao argumento do Romulo. Concorde só no que se sustenta, contraponha o resto e termine com UMA pergunta.",
    "revisar": "Liste: (1) afirmações sem fonte, (2) saltos lógicos, (3) termos sem definição, (4) lacunas que as leituras disponíveis ajudariam a cobrir. Seja específico, citando o trecho.",
}


def _llm():
    return ia.criar_llm(CFG, "orientador", int(CFG["MAX_TOKENS_ORIENTADOR"]), temperature=0.4)


def resumo_leituras(biblioteca: Path | None = None) -> str:
    """Cartões curtos das leituras já processadas (o que o orientador pode citar)."""
    raiz = biblioteca or (Path(CFG["BIBLIOTECA"]) if CFG["BIBLIOTECA"] else None)
    if not raiz or not raiz.exists():
        return "(nenhuma leitura processada ainda)"
    teto, partes, total = int(CFG["LEITURAS_MAX_CHARS"]), [], 0
    arquivos = sorted(raiz.rglob("*.leitura.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for arq in arquivos:
        try:
            d = json.loads(arq.read_text(encoding="utf-8"))
        except Exception:
            continue
        rel = set(d.get("relevantes", []))
        trechos = [t for t in d.get("trechos", []) if t["id"] in rel][:2]
        estado = "lido" if "2_Lido" in arq.parts else "para ler"
        cartao = f"- {arq.name.replace('.leitura.json', '')} ({estado}): " + " | ".join(
            f"p.{t['pagina']}: {(t.get('traducao') or t['texto'])[:220]}" for t in trechos)
        if total + len(cartao) > teto:
            break
        partes.append(cartao)
        total += len(cartao)
    return "\n".join(partes) or "(nenhuma leitura processada ainda)"


def contexto_do_cofre(texto: str) -> str:
    """Regras, catálogo, fichamentos ligados ao texto e pendências do cofre (vazio se não houver cofre)."""
    if not contexto_cofre.raiz():
        return ""
    partes = [("REGRAS DO COFRE", contexto_cofre.regras()),
              ("FICHAMENTOS DO COFRE (os mais ligados a este texto)", contexto_cofre.fichamentos(texto)),
              ("CATÁLOGO DO ACERVO (#código, ano, título, status, núcleo)", contexto_cofre.catalogo()),
              ("PENDÊNCIAS DO COFRE", contexto_cofre.pendencias())]
    return "".join(f"{t}:\n{c}\n\n" for t, c in partes if c)


def responder(texto_secao: str, historico: list[dict], modo: str = "debater",
              leituras: str | None = None) -> tuple[str, int]:
    """historico = [{"role": "user"|"assistant", "content": "..."}]; devolve (resposta, tokens)."""
    texto = texto_secao.strip()[: int(CFG["TESE_MAX_CHARS"])] or "(seção vazia)"
    base_busca = texto + " " + " ".join(m["content"] for m in historico[-2:])
    cofre = contexto_do_cofre(base_busca)
    contexto = (f"{SISTEMA}\n\nMODO: {MODOS.get(modo, MODOS['debater'])}\n\n"
                f"TEXTO DA SEÇÃO (escrito pelo Romulo):\n\"\"\"\n{texto}\n\"\"\"\n\n"
                f"{cofre}"
                f"LEITURAS DO PAINEL (processadas pelo leitor):\n{leituras if leituras is not None else resumo_leituras()}")
    janela = historico[-2 * int(CFG["HISTORICO_TROCAS"]):]
    if not janela or janela[-1]["role"] != "user":
        janela = janela + [{"role": "user", "content": {"questionar": "Me questione sobre esse texto.",
                                                        "revisar": "Revise esse texto."}.get(modo, "Vamos debater.")}]
    def chamar():
        llm = _llm()
        return llm, str(llm.call([{"role": "system", "content": contexto}, *janela]))

    llm, resposta = ia.com_reserva(CFG, chamar, "orientador")
    try:
        tokens = int(llm.get_token_usage_summary().total_tokens)
    except Exception:
        tokens = (len(contexto) + sum(len(m["content"]) for m in janela) + len(resposta)) // 4
    return resposta.strip(), tokens


def registrar(pasta_debates: Path, secao: str, pergunta: str, resposta: str) -> Path:
    pasta_debates.mkdir(parents=True, exist_ok=True)
    arq = pasta_debates / f"{secao} — debates.md"
    novo = not arq.exists()
    with arq.open("a", encoding="utf-8") as f:
        if novo:
            f.write(f"# Debates com o orientador — {secao}\n\n> Gerado por IA. Confira qualquer referência antes de usar.\n\n")
        f.write(f"## {datetime.now():%d/%m/%Y %H:%M}\n\n**Romulo:** {pergunta}\n\n**Orientador:** {resposta}\n\n")
    return arq


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit('Uso: python orientador.py "caminho\\da\\secao.md"')
    secao = Path(sys.argv[1])
    texto = secao.read_text(encoding="utf-8")
    historico: list[dict] = []
    print("Orientador pronto. Comandos: /questionar  /revisar  /sair  (ou escreva seu argumento)\n")
    modo = "questionar"
    while True:
        resp, tok = responder(texto, historico, modo)
        print(f"\nOrientador ({tok} tokens):\n{resp}\n")
        historico.append({"role": "assistant", "content": resp})
        entrada = input("Você: ").strip()
        if entrada in ("/sair", ""):
            break
        modo = entrada[1:] if entrada in ("/questionar", "/revisar") else "debater"
        historico.append({"role": "user", "content": entrada if modo == "debater" else f"({modo})"})
        registrar(secao.parent / "Debates", secao.stem, entrada, resp)


if __name__ == "__main__":
    main()
