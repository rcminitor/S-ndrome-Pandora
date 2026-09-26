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


def main() -> None:
    atual = ler(ENV)
    print("Configuração dos agentes — Enter mantém o valor entre colchetes.\n")

    chave = getpass(f"Chave de API do provedor {'[já preenchida]' if atual.get('LLM_API_KEY') else '[vazia]'}: ").strip()
    email = input(f"Seu e-mail (para Crossref/OpenAlex) [{atual.get('EMAIL_CONTATO', '')}]: ").strip()
    padrao_pasta = atual.get("PASTA_ESTUDO") or (str(COFRE_PDF) if COFRE_PDF.exists() else "")
    mostra = padrao_pasta or str(AQUI / "biblioteca")
    pasta = input(f"Pasta onde salvar os PDFs baixados [{mostra}]: ").strip().strip('"')

    novos = {
        "LLM_API_KEY": chave or atual.get("LLM_API_KEY", ""),
        "EMAIL_CONTATO": email or atual.get("EMAIL_CONTATO", ""),
        "PASTA_ESTUDO": pasta or padrao_pasta,
    }
    if novos["PASTA_ESTUDO"] and not Path(novos["PASTA_ESTUDO"]).exists():
        print(f"Aviso: a pasta {novos['PASTA_ESTUDO']} ainda não existe; ela será criada no primeiro download.")

    saida = []
    for l in MODELO.read_text(encoding="utf-8").splitlines():
        crua = l.lstrip("# ").strip()
        k = crua.split("=", 1)[0].strip() if "=" in crua and not crua.startswith(("Copie", "Formato")) else None
        if k and k.isupper() and k.replace("_", "").isalnum():
            valor = novos.get(k) or atual.get(k)
            if valor is not None and (valor or not l.startswith("#")):
                saida.append(f"{k}={valor}")            # ativa a linha com o valor escolhido
                continue
        saida.append(l)
    ENV.write_text("\n".join(saida) + "\n", encoding="utf-8")

    print(f"\n.env gravado em {ENV}")
    print("Chave:", "preenchida" if novos["LLM_API_KEY"] else "VAZIA — os agentes não vão funcionar sem ela")
    print("E-mail:", novos["EMAIL_CONTATO"] or "vazio (as buscas funcionam, mas mais devagar)")
    print("PDFs baixados em:", novos["PASTA_ESTUDO"] or AQUI / "biblioteca")


if __name__ == "__main__":
    main()
