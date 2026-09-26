"""
Configurador do .env — rode uma vez:  python configurar.py

Pergunta a chave, o e-mail e a pasta de estudo e grava o .env desta pasta
(UTF-8, sem precisar editar nada à mão). Enter mantém o valor atual.
A chave é digitada sem aparecer na tela e fica só neste computador.
"""
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


def main() -> None:
    atual = ler(ENV)
    print("Configuração dos agentes — Enter mantém o valor entre colchetes.\n")

    usar_omni = input("Usar o gateway OmniRoute do seu PC (combo 'gratuitos', sem custo)? [S/n]: ").strip().lower() != "n"
    modelo_omni = "combo/gratuitos"
    if usar_omni:
        print("  O OmniRoute precisa estar ligado (comando: omni status).")
        achada, modelo_omni, onde = achar_omniroute()
        if achada:
            print(f"  Chave do OmniRoute encontrada em {onde} (não será mostrada).")
            chave = achada
        else:
            print("  Não achei a chave nos seus projetos. Copie-a do painel http://localhost:20128 (API Keys).")
            chave = getpass("  Chave do OmniRoute: ").strip() or atual.get("LLM_API_KEY", "")
    else:
        chave = getpass(f"Chave de API do provedor (ex.: Anthropic, paga) {'[já preenchida]' if atual.get('LLM_API_KEY') else '[vazia]'}: ").strip()
    reserva = ""
    if usar_omni:
        tem = "[já preenchida — Enter mantém]" if atual.get("RESERVA_API_KEY") else "[Enter = sem reserva]"
        reserva = getpass(f"Chave PAGA de reserva, usada só quando o gratuito falhar (ex.: sk-ant-...) {tem}: ").strip()
    email = input(f"Seu e-mail (para Crossref/OpenAlex) [{atual.get('EMAIL_CONTATO', '')}]: ").strip()
    padrao_pasta = atual.get("PASTA_ESTUDO") or (str(COFRE_PDF) if COFRE_PDF.exists() else "")
    mostra = padrao_pasta or str(AQUI / "biblioteca")
    pasta = input(f"Pasta onde salvar os PDFs baixados [{mostra}]: ").strip().strip('"')

    novos = {
        "LLM_API_KEY": chave or atual.get("LLM_API_KEY", ""),
        "EMAIL_CONTATO": email or atual.get("EMAIL_CONTATO", ""),
        "RESERVA_API_KEY": (reserva or atual.get("RESERVA_API_KEY", "")) if usar_omni else "",
        "PASTA_ESTUDO": pasta or padrao_pasta,
    }
    if usar_omni:
        m = f"openai/{modelo_omni}"
        novos.update({"LLM_BASE_URL": "http://localhost:20128/v1", "MODELO_TUTOR": m,
                      "MODELO_BARATO": m, "MODELO_TRADUTOR": m})
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
    print("Chave:", "preenchida" if novos["LLM_API_KEY"] else "VAZIA — os agentes não vão funcionar sem ela")
    if usar_omni:
        print("Reserva paga:", "preenchida (entra sozinha quando o gratuito falhar)" if novos["RESERVA_API_KEY"] else "nenhuma")
    print("E-mail:", novos["EMAIL_CONTATO"] or "vazio (as buscas funcionam, mas mais devagar)")
    print("PDFs baixados em:", novos["PASTA_ESTUDO"] or AQUI / "biblioteca")


if __name__ == "__main__":
    main()
