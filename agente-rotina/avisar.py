"""Agente de rotina: avisa no WhatsApp (via CallMeBot) os blocos de estudo, escrita, leitura e descanso.

Roda em dois lugares possíveis (coloque a chave em UM só, senão as mensagens chegam em dobro):
  - nuvem: GitHub Actions (.github/workflows/avisos.yml), mesmo com o PC desligado;
  - local: Agendador de Tarefas do Windows, a cada 5 minutos.

Configuração — variáveis de ambiente (nuvem) ou %USERPROFILE%\\.agente-rotina\\config.json (local):
    CALLMEBOT_APIKEY / "apikey"    WHATSAPP_PHONE / "telefone"            (WhatsApp)
    TELEGRAM_TOKEN / "telegram_token"   TELEGRAM_CHAT_ID / "telegram_chat"  (Telegram)
    Com os dois canais configurados, a mensagem vai para ambos.
    AGENTE_COFRE (opcional)        caminho do cofre; padrão = "cofre" em rotina.json
    AGENTE_ESTADO (opcional)       arquivo de estado; padrão = ~/.agente-rotina/enviados.json
    AGENTE_TOLERANCIA (opcional)   minutos de atraso aceitos para um aviso; padrão 15
    ROTINA_JSON (opcional)         conteúdo de rotina.json (na nuvem vem de um secret, para não ficar público)
    AGENTE_PAUSA_ATE (opcional)    AAAA-MM-DD: pausa até essa data (variável do repositório no GitHub)

Uso:
    python avisar.py               verifica e envia o que estiver na hora
    python avisar.py --teste       envia uma mensagem de teste agora
    python avisar.py --hoje        lista os avisos de hoje (não envia)
    python avisar.py --previa      mostra o texto de todas as mensagens (não envia)
    python avisar.py --pausar 7    suspende os avisos por 7 dias (grava pausa.json)
    python avisar.py --retomar     encerra a pausa
    python avisar.py --telegram-chat-id   mostra o chat_id (com TELEGRAM_TOKEN definido)
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

AQUI = Path(__file__).resolve().parent
PASTA_CFG = Path.home() / ".agente-rotina"
CFG = PASTA_CFG / "config.json"
ESTADO = Path(os.environ.get("AGENTE_ESTADO") or PASTA_CFG / "enviados.json")
LOG = PASTA_CFG / "agente.log"
PAUSA = AQUI / "pausa.json"
DIAS = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
TOLERANCIA = timedelta(minutes=int(os.environ.get("AGENTE_TOLERANCIA", "15")))
FALHAS_PARA_ALERTA = 3


def log(msg, uma_vez_por_dia=False):
    print(msg)
    try:
        PASTA_CFG.mkdir(exist_ok=True)
        if uma_vez_por_dia and LOG.exists():
            hoje = f"{datetime.now():%Y-%m-%d}"
            if any(l.startswith(hoje) and l.rstrip().endswith(msg)
                   for l in LOG.read_text(encoding="utf-8").splitlines()[-300:]):
                return
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")
    except OSError:
        pass


def carregar_cfg():
    cfg = json.loads(CFG.read_text(encoding="utf-8")) if CFG.exists() else {}
    cfg["apikey"] = os.environ.get("CALLMEBOT_APIKEY") or cfg.get("apikey", "")
    cfg["telefone"] = os.environ.get("WHATSAPP_PHONE") or cfg.get("telefone", "")
    cfg["telegram_token"] = (os.environ.get("TELEGRAM_TOKEN") or cfg.get("telegram_token", "")).strip()
    cfg["telegram_chat"] = os.environ.get("TELEGRAM_CHAT_ID") or cfg.get("telegram_chat", "")
    return cfg


def canais(cfg):
    """Canais configurados: WhatsApp (CallMeBot) e/ou Telegram."""
    c = []
    if cfg["apikey"] and cfg["telefone"]:
        c.append("whatsapp")
    if cfg["telegram_token"] and cfg["telegram_chat"]:
        c.append("telegram")
    return c


def enviar(cfg, texto):
    """Envia por todos os canais configurados; falha se algum falhar."""
    for canal in canais(cfg):
        (enviar_telegram if canal == "telegram" else enviar_whatsapp)(cfg, texto)


def enviar_telegram(cfg, texto):
    dados = urllib.parse.urlencode({"chat_id": cfg["telegram_chat"], "text": texto}).encode()
    url = f"https://api.telegram.org/bot{cfg['telegram_token']}/sendMessage"
    with urllib.request.urlopen(url, data=dados, timeout=30) as r:
        resposta = json.loads(r.read().decode("utf-8"))
    if not resposta.get("ok"):
        raise RuntimeError(f"Telegram respondeu: {str(resposta)[:200]}")


def descobrir_chat_telegram(cfg):
    """Mostra o chat_id de quem mandou mensagem ao bot (rode depois de mandar /start a ele)."""
    token = cfg["telegram_token"].strip().strip('"').strip("'")
    if not token or ":" not in token:
        return print("Token ausente ou incompleto. Ele tem o formato 123456789:AAH... (número, dois-pontos, letras).")
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            upd = json.loads(r.read().decode("utf-8")).get("result", [])
    except urllib.error.HTTPError as e:
        motivo = {401: "token inválido", 404: "token não reconhecido"}.get(e.code, f"erro {e.code}")
        return print(f"O Telegram recusou: {motivo}. Copie de novo o token que o @BotFather mandou, "
                     "inteiro, sem espaços, e cole entre as aspas.")
    chats = {u["message"]["chat"]["id"]: u["message"]["chat"].get("first_name", "") for u in upd if "message" in u}
    print("\n".join(f"chat_id: {i}  ({n})" for i, n in chats.items()) or "nenhuma mensagem: mande /start ao bot e rode de novo")


def enviar_whatsapp(cfg, texto):
    url = "https://api.callmebot.com/whatsapp.php?" + urllib.parse.urlencode(
        {"phone": cfg["telefone"], "text": texto, "apikey": cfg["apikey"]})
    with urllib.request.urlopen(url, timeout=30) as r:
        corpo = r.read().decode("utf-8", "replace")
    if r.status != 200 or "error" in corpo.lower():
        raise RuntimeError(f"CallMeBot respondeu {r.status}: {corpo[:200]}")


# --- pausa -------------------------------------------------------------------------------------

def pausado_ate(hoje):
    valor = os.environ.get("AGENTE_PAUSA_ATE", "").strip()
    if not valor and PAUSA.exists():
        valor = json.loads(PAUSA.read_text(encoding="utf-8"))["ate"]
    if not valor:
        return None
    ate = date.fromisoformat(valor)
    return ate if hoje <= ate else None


def pausar(dias, hoje):
    ate = hoje + timedelta(days=dias - 1)
    PAUSA.write_text(json.dumps({"ate": ate.isoformat()}, indent=2), encoding="utf-8")
    print(f"avisos pausados até {ate:%d/%m/%Y} (inclusive). Na nuvem, faça commit/push de pausa.json.")


# --- contexto tirado do cofre (só leitura) -----------------------------------------------------

def proxima_atividade(cofre):
    """Primeira linha não vazia sob '## Próxima atividade recomendada' no Índice do cofre."""
    indice = cofre / "00 Índice do cofre.md"
    if not indice.exists():
        return None
    linhas = indice.read_text(encoding="utf-8").splitlines()
    for i, l in enumerate(linhas):
        if l.strip().lower().startswith("## próxima atividade"):
            return next((p.strip()[:300] for p in linhas[i + 1:] if p.strip()), None)
    return None


def palavras_capitulos(cofre):
    """{nome do capítulo: (palavras, status)} de Notas/Tese."""
    caps = {}
    for p in sorted((cofre / "Notas" / "Tese").glob("*.md")):
        t = p.read_text(encoding="utf-8")
        status = next((l.split(":", 1)[1].strip() for l in t.splitlines()[:15] if l.startswith("status:")), "")
        caps[p.stem] = (len(t.split()), status)
    return caps


def fichamentos_da_semana(cofre):
    """(novos, revisados) em Fichamentos/ nos commits dos últimos 7 dias (git do cofre)."""
    def contar(filtro):
        r = subprocess.run(["git", "-C", str(cofre), "log", "--since=7 days ago", f"--diff-filter={filtro}",
                            "--name-only", "--pretty=format:", "--", "Fichamentos"],
                           capture_output=True, text=True, encoding="utf-8", timeout=30,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return {l for l in r.stdout.splitlines() if l.strip()}
    novos = contar("A")
    return len(novos), len(contar("M") - novos)


def contexto(tipo, rotina, agora, semana):
    cofre = Path(os.environ.get("AGENTE_COFRE") or rotina.get("cofre", ""))
    if not cofre.is_dir():
        return ""
    try:
        if tipo == "leitura":
            prox = proxima_atividade(cofre)
            return f"\n📌 Próxima atividade (Índice do cofre): {prox}" if prox else ""
        if tipo == "escrita":
            caps = palavras_capitulos(cofre)
            if not caps:
                return ""
            alvo = next((c for c, (_, s) in caps.items() if s != "redigido"), min(caps, key=lambda c: caps[c][0]))
            return f"\n✍️ Sugestão: {alvo} ({caps[alvo][0]} palavras)."
        if tipo == "balanco":
            caps = palavras_capitulos(cofre)
            total = sum(w for w, _ in caps.values())
            antes = semana.get("palavras_tese")
            delta = f" ({total - antes:+d} na semana)" if antes is not None else ""
            semana["palavras_tese"] = total
            novos, revisados = fichamentos_da_semana(cofre)
            return (f"\n📊 Últimos 7 dias: {novos} fichamento(s) novo(s), {revisados} revisado(s); "
                    f"tese com {total} palavras{delta} em {len(caps)} capítulos.")
    except Exception as e:  # o aviso sai mesmo sem o contexto (OneDrive offline etc.)
        log(f"contexto {tipo} indisponível: {e}")
    return ""


# --- montagem dos avisos -----------------------------------------------------------------------

def blocos_do_dia(rotina, dia_semana):
    return sorted((b for b in rotina["blocos"] if dia_semana in b["dias"]), key=lambda b: b["inicio"])


def resumo_do_dia(rotina, agora, semana):
    blocos = blocos_do_dia(rotina, DIAS[agora.weekday()])
    nome = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"][agora.weekday()]
    if not blocos:
        return f"☀️ Bom dia! {nome}, {agora:%d/%m}: dia livre, sem tese. Aproveite."
    linhas = "\n".join(f"• {b['inicio']}–{b['fim']} {b['titulo']}" for b in blocos)
    extra = contexto("leitura", rotina, agora, semana) if any(b.get("contexto") == "leitura" for b in blocos) else ""
    return f"☀️ Bom dia! {nome}, {agora:%d/%m}:\n{linhas}{extra}"


def montar(b, rotina, agora, semana):
    if b["id"] == "resumo":
        return resumo_do_dia(rotina, agora, semana)
    texto = f"⏰ {b['inicio']}–{b['fim']} · {b['titulo']}\n{b['msg']}"
    if b.get("contexto"):
        texto += contexto(b["contexto"], rotina, agora, semana)
    return texto


def avisos(rotina, dia_semana):
    """(bloco, horário local do aviso 'HH:MM') do dia; inclui o resumo da manhã."""
    if rotina.get("resumo_manha"):
        yield {"id": "resumo", "titulo": "Resumo do dia", "inicio": rotina["resumo_manha"], "fim": ""}, rotina["resumo_manha"]
    for b in blocos_do_dia(rotina, dia_semana):
        if b.get("so_no_resumo"):
            continue
        h, m = map(int, b["inicio"].split(":"))
        t = h * 60 + m - b.get("antecedencia_min", rotina["antecedencia_min"])
        yield b, f"{t // 60:02d}:{t % 60:02d}"


def main():
    rotina = json.loads(os.environ.get("ROTINA_JSON") or (AQUI / "rotina.json").read_text(encoding="utf-8"))
    agora = datetime.now(ZoneInfo(rotina["fuso"]))
    hoje = agora.date()

    if "--pausar" in sys.argv:
        return pausar(int(sys.argv[sys.argv.index("--pausar") + 1]), hoje)
    if "--retomar" in sys.argv:
        PAUSA.unlink(missing_ok=True)
        return print("pausa encerrada")
    if "--hoje" in sys.argv:
        for b, hhmm in avisos(rotina, DIAS[agora.weekday()]):
            print(f"{hhmm}  {b['titulo']}")
        return
    if "--previa" in sys.argv:
        print(f"[resumo]\n{resumo_do_dia(rotina, agora, {})}\n")
        for b in rotina["blocos"]:
            if not b.get("so_no_resumo"):
                print(f"[{','.join(b['dias'])}]\n{montar(b, rotina, agora, {})}\n")
        return

    cfg = carregar_cfg()
    if "--telegram-chat-id" in sys.argv:
        return descobrir_chat_telegram(cfg)
    if not canais(cfg):
        log("nenhum canal configurado (WhatsApp ou Telegram); nada enviado", True)
        return
    if "--teste" in sys.argv:
        enviar(cfg, "✅ Agente de rotina conectado. Você vai receber aqui os avisos de estudo, escrita, leitura e descanso.")
        return print("mensagem de teste enviada")

    ate = pausado_ate(hoje)
    if ate:
        log(f"em pausa até {ate:%d/%m/%Y}; nada enviado", True)
        return

    estado = json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {}
    semana = estado.get("semana", {})
    falhas = estado.get("falhas", 0)
    enviados = {k: v for k, v in estado.items() if k.startswith(hoje.isoformat())}
    for b, hhmm in avisos(rotina, DIAS[agora.weekday()]):
        quando = agora.replace(hour=int(hhmm[:2]), minute=int(hhmm[3:]), second=0, microsecond=0)
        chave = f"{hoje.isoformat()}:{b['id']}"
        if chave in enviados or not (quando <= agora < quando + TOLERANCIA):
            continue
        sem = dict(semana)  # só vale se o envio der certo
        try:
            enviar(cfg, montar(b, rotina, agora, sem))
            semana.update(sem)
            enviados[chave] = agora.isoformat()
            falhas = 0
            log(f"enviado: {b['id']}")
        except Exception as e:  # sem rede, chave errada etc.: tenta de novo na próxima rodada
            falhas += 1
            log(f"falha ao enviar {b['id']} ({falhas}ª seguida): {e}")
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps({**enviados, "semana": semana, "falhas": falhas}, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    if falhas == FALHAS_PARA_ALERTA:  # na nuvem, a execução falha e o GitHub manda e-mail
        log(f"ALERTA: {falhas} falhas seguidas de envio — confira a apikey do CallMeBot")
        sys.exit(1)


if __name__ == "__main__":
    main()
