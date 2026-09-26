"""
Configurador do .env — rode uma vez:  python configurar.py

Pergunta a chave, o e-mail e a pasta de estudo e grava o .env desta pasta
(UTF-8, sem precisar editar nada à mão). Enter mantém o valor atual.
A chave fica só neste computador (arquivo .env, que não vai para o GitHub).
"""
import sys
from getpass import getpass
from pathlib import Path

AQUI = Path(__file__).resolve().parent
MODELO = AQUI / ".env.exemplo"
ENV = AQUI / ".env"
COFRE_PDF = Path(r"C:\Users\rcmin\OneDrive\Documents\Pos-Graduacao\Doutorado UFC\Síndrome de Pandora\PDF\A_classificar")


def ler(arq: Path) -> dict:
    vals = {}
    if arq.exists():
        for l in arq.read_text(encoding="utf-8-sig").splitlines():
            l = l.strip()
            if l and not l.startswith("#") and "=" in l:
                k, v = l.split("=", 1)
                vals[k.strip()] = v.strip()
    return vals


def achar_omniroute() -> tuple[str, str, Path | None]:
    """Procura a chave do OmniRoute nos .claude/settings.local.json dos seus projetos
    (é a mesma que o Claude Code usa). Devolve (chave, modelo, onde)."""
    import json
    candidatos = [AQUI.parent / ".claude" / "settings.local.json"]
    projetos = Path.home() / "Projetos"
    if projetos.exists():
        candidatos += sorted(projetos.glob("*/.claude/settings.local.json"))
    for arq in candidatos:
        try:
            env = json.loads(arq.read_text(encoding="utf-8-sig")).get("env", {})
        except Exception:
            continue
        if "20128" in env.get("ANTHROPIC_BASE_URL", ""):
            chave = env.get("ANTHROPIC_AUTH_TOKEN") or env.get("ANTHROPIC_API_KEY") or ""
            if chave:
                modelo = env.get("ANTHROPIC_MODEL", "")
                return chave, (modelo if modelo and modelo != "auto" else "combo/gratuitos"), arq.parent.parent
    return "", "combo/gratuitos", None


def ler_chave(rotulo: str, prefixo: str = "", manter: str = "") -> str:
    """Campo visível (o de senha do Windows às vezes não aceita colar). Confere o formato
    e mostra só o começo e o fim da chave."""
    print(f"{rotulo}")
    print("  Cole com Ctrl+V ou com o botão direito do mouse e aperte Enter"
          + (" (Enter vazio mantém a atual)." if manter else "."))
    for _ in range(3):
        chave = input("  > ").strip().strip('"').strip("'").replace(" ", "")
        if not chave:
            return manter
        if prefixo and not chave.startswith(prefixo):
            print(f"  Essa chave não parece certa: deveria começar com {prefixo}. Tente de novo (ou Enter para pular).")
            continue
        print(f"  ✓ chave recebida: {chave[:6]}…{chave[-4:]} ({len(chave)} caracteres)")
        if sys.stdout.isatty():                      # apaga a chave da tela depois de conferida
            print("\033[3A\033[J", end="")
            print(f"  ✓ chave recebida: {chave[:6]}…{chave[-4:]} ({len(chave)} caracteres)")
        return chave
    return manter


def main() -> None:
    atual = ler(ENV)
    print("Configuração dos agentes — Enter mantém o valor entre colchetes.\n")

    GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
    anterior = atual.get("PROVEDOR", "")
    print("Qual IA usar como principal?")
    print("  1) OmniRoute do seu PC (combo 'gratuitos')")
    print("  2) Gemini direto, com a sua chave do Google AI Studio")
    print("  3) Anthropic (Claude), chave paga")
    print("  4) OpenAI (ChatGPT/GPT), chave paga")
    padrao = {"omniroute": "1", "gemini": "2", "anthropic": "3", "openai": "4"}.get(anterior, "1")
    escolha = input(f"Opção [{padrao}]: ").strip() or padrao
    provedor = {"1": "omniroute", "2": "gemini", "3": "anthropic", "4": "openai"}.get(escolha, "omniroute")
    mesma = provedor == anterior and atual.get("LLM_API_KEY")
    manter = " [já preenchida — Enter mantém]" if mesma else ""

    modelo_omni = "combo/gratuitos"
    if provedor == "omniroute":
        print("  O OmniRoute precisa estar ligado (comando: omni status).")
        achada, modelo_omni, onde = achar_omniroute()
        if achada:
            print(f"  Chave do OmniRoute encontrada em {onde} (não será mostrada).")
            chave = achada
        else:
            print("  Não achei a chave nos seus projetos. Copie-a do painel http://localhost:20128 (API Keys).")
            chave = ler_chave("  Chave do OmniRoute:", "", atual.get("LLM_API_KEY", "") if mesma else "")
    elif provedor == "gemini":
        print("  A chave fica em aistudio.google.com → Get API key (começa com AIza…).")
        chave = ler_chave("  Chave do Gemini:", "AIza", atual.get("LLM_API_KEY", "") if mesma else "")
    elif provedor == "openai":
        print("  A chave fica em platform.openai.com → API keys (começa com sk-…).")
        chave = ler_chave("  Chave da OpenAI:", "sk-", atual.get("LLM_API_KEY", "") if mesma else "")
    else:
        print("  A chave fica em console.anthropic.com → API Keys (começa com sk-ant-…).")
        chave = ler_chave("  Chave da Anthropic:", "sk-ant-", atual.get("LLM_API_KEY", "") if mesma else "")
    usar_omni = provedor in ("omniroute", "gemini")   # nos gratuitos cabe uma reserva paga
    reserva = ""
    if usar_omni:
        tem = "[já preenchida — Enter mantém]" if atual.get("RESERVA_API_KEY") else "[Enter = sem reserva]"
        reserva = ler_chave(f"Chave PAGA de reserva (Anthropic sk-ant-… ou OpenAI sk-…), usada só quando o principal falhar {tem}:", "sk-", "")
    email = input(f"Seu e-mail (para Crossref/OpenAlex) [{atual.get('EMAIL_CONTATO', '')}]: ").strip()
    padrao_pasta = atual.get("PASTA_ESTUDO") or (str(COFRE_PDF) if COFRE_PDF.exists() else "")
    mostra = padrao_pasta or str(AQUI / "biblioteca")
    pasta = input(f"Pasta onde salvar os PDFs baixados [{mostra}]: ").strip().strip('"')

    print("\nResumo semanal por e-mail (Enter em branco = só grava a nota no cofre).")
    para = input(f"  Enviar para [{atual.get('RESUMO_PARA', '')}]: ").strip() or atual.get("RESUMO_PARA", "")
    smtp_user = smtp_senha = ""
    if para:
        smtp_user = input(f"  Conta que envia (Gmail/Workspace) [{atual.get('SMTP_USUARIO') or para}]: ").strip() \
            or atual.get("SMTP_USUARIO") or para
        tem = "[já preenchida — Enter mantém]" if atual.get("SMTP_SENHA") else ""
        print("  Senha de APP (myaccount.google.com → Segurança → Senhas de app), não a senha normal", tem)
        smtp_senha = getpass("  > ").strip().replace(" ", "") or atual.get("SMTP_SENHA", "")

    novos = {
        "RESUMO_PARA": para,
        "SMTP_USUARIO": smtp_user,
        "SMTP_SENHA": smtp_senha,
        "LLM_API_KEY": chave,
        "PROVEDOR": provedor,
        "EMAIL_CONTATO": email or atual.get("EMAIL_CONTATO", ""),
        "RESERVA_API_KEY": (reserva or atual.get("RESERVA_API_KEY", "")) if usar_omni else "",
        "PASTA_ESTUDO": pasta or padrao_pasta,
    }
    if provedor == "omniroute":
        m = f"openai/{modelo_omni}"
        novos.update({"LLM_BASE_URL": "http://localhost:20128/v1", "MODELO_TUTOR": m,
                      "MODELO_BARATO": m, "MODELO_TRADUTOR": m})
    elif provedor == "gemini":                         # os mesmos modelos do seu combo no OmniRoute
        novos.update({"LLM_BASE_URL": GEMINI_URL, "MODELO_TUTOR": "openai/gemini-3.8-flash",
                      "MODELO_TRADUTOR": "openai/gemini-3.8-flash", "MODELO_BARATO": "openai/gemini-3.5-flash-lite"})
    elif provedor == "openai":                         # troque os nomes no .env se preferir outros modelos
        novos.update({"LLM_BASE_URL": "", "MODELO_TUTOR": "openai/gpt-5-mini",
                      "MODELO_TRADUTOR": "openai/gpt-5-mini", "MODELO_BARATO": "openai/gpt-5-nano"})
    else:                                              # chave paga da Anthropic: volta aos modelos Claude
        novos.update({"LLM_BASE_URL": "", "MODELO_TUTOR": "anthropic/claude-sonnet-5",
                      "MODELO_BARATO": "anthropic/claude-haiku-4-5-20251001",
                      "MODELO_TRADUTOR": "anthropic/claude-haiku-4-5-20251001"})
    if novos["PASTA_ESTUDO"] and not Path(novos["PASTA_ESTUDO"]).exists():
        print(f"Aviso: a pasta {novos['PASTA_ESTUDO']} ainda não existe; ela será criada no primeiro download.")

    saida, feitos = [], set()
    for l in MODELO.read_text(encoding="utf-8").splitlines():
        crua = l.lstrip("# ").strip()
        k = crua.split("=", 1)[0].strip() if "=" in crua and not crua.startswith(("Copie", "Formato")) else None
        if k and k.isupper() and k.replace("_", "").isalnum():
            if k in feitos:                                  # exemplo comentado de chave já gravada
                saida.append(l if l.startswith("#") else "# " + l); continue
            valor = novos[k] if k in novos else atual.get(k)
            if k in novos and not valor and l.startswith("#"):
                saida.append(l); continue
            if valor is not None and (valor or not l.startswith("#")):
                saida.append(f"{k}={valor}")            # ativa a linha com o valor escolhido
                feitos.add(k)
                continue
        saida.append(l)
    ENV.write_text("\n".join(saida) + "\n", encoding="utf-8")

    print(f"\n.env gravado em {ENV}")
    print("IA principal:", {"omniroute": "OmniRoute", "gemini": "Gemini direto", "anthropic": "Anthropic",
                            "openai": "OpenAI"}[provedor])
    print("Chave:", "preenchida" if novos["LLM_API_KEY"] else "VAZIA — os agentes não vão funcionar sem ela")
    if usar_omni:
        print("Reserva paga:", "preenchida (entra sozinha quando o principal falhar)" if novos["RESERVA_API_KEY"] else "nenhuma")
    print("E-mail:", novos["EMAIL_CONTATO"] or "vazio (as buscas funcionam, mas mais devagar)")
    print("PDFs baixados em:", novos["PASTA_ESTUDO"] or AQUI / "biblioteca")
    print("Resumo semanal:", f"por e-mail para {novos['RESUMO_PARA']}" if novos["RESUMO_PARA"] and novos["SMTP_SENHA"]
          else "só a nota no cofre (e-mail não configurado)")


if __name__ == "__main__":
    main()
