"""
Resumo semanal — um e-mail na segunda-feira com a semana que passou
===================================================================

Toda segunda (ou na primeira vez que o painel ligar depois dela), o painel monta o
resumo da semana ANTERIOR (segunda a domingo) só com números e listas que já
existem — nada de IA, nada inventado:

  • o que você fez: artigos lidos, páginas lidas, fichamentos, páginas escritas
    (tese e artigo), revisões e acerto, leituras da IA, conversas com o orientador
    — com a comparação com a semana anterior;
  • a revisão de hoje: cartões a revisar, firmes/total;
  • a Fila de leitura: as 3 primeiras e a mais urgente sem PDF;
  • a rastreabilidade: parágrafos, com fonte, alertas; fichadas fora do texto;
  • o backup do cofre: último envio ao GitHub (ou o erro);
  • UMA próxima atividade recomendada (a primeira da fila, ou o PDF a buscar).

Grava sempre a nota Notas\\Resumos semanais\\Semana AAAA-MM-DD.md no cofre e, se o
e-mail estiver configurado no .env de agentes_crewai (RESUMO_PARA, SMTP_…), envia.
Enviar agora, para testar:   python painel_local\\resumo_semanal.py --agora
"""
from __future__ import annotations

import html
import json
import smtplib
import ssl
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

from progresso import segunda


def _br(d: date) -> str:
    return f"{d:%d/%m}"


def _seta(atual, anterior) -> str:
    if anterior in (None, 0) or atual is None:
        return ""
    return " ↑" if atual > anterior else " ↓" if atual < anterior else " ="


class Resumo:
    def __init__(self, cfg: dict, cofre, prog, rev, fila, rast, backup, biblioteca: Path):
        self.cfg, self.cofre, self.prog, self.rev, self.fila, self.rast, self.backup = cfg, cofre, prog, rev, fila, rast, backup
        self.arq_status = biblioteca / "resumo_semanal_status.json"

    # ------------------------------------------------------------ quando
    def _status(self) -> dict:
        try:
            return json.loads(self.arq_status.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def semana_devida(self) -> date:
        """Segunda-feira da semana anterior à atual."""
        return segunda(date.today()) - timedelta(days=7)

    def precisa(self) -> bool:
        return self._status().get("semana") != self.semana_devida().isoformat()

    @property
    def email_configurado(self) -> bool:
        return all(self.cfg.get(k) for k in ("RESUMO_PARA", "SMTP_USUARIO", "SMTP_SENHA"))

    # ------------------------------------------------------------ conteúdo
    def montar(self, ini: date | None = None) -> dict:
        ini = ini or self.semana_devida()
        fim = ini + timedelta(days=6)
        sems = {s["semana"]: s for s in self.prog.semanas()} if self.prog else {}
        s = sems.get(ini.isoformat()) or {}
        a = sems.get((ini - timedelta(days=7)).isoformat()) or {}
        itens = [("Artigos lidos por você", "artigosLidos"), ("Páginas lidas", "paginasLidas"),
                 ("Fichamentos", "fichamentos"), ("Páginas escritas — tese", "pagTese"),
                 ("Páginas escritas — artigo", "pagArtigo"), ("Cartões revisados", "revisoes"),
                 ("Leituras feitas pela IA", "leiturasIA"), ("Conversas com o orientador", "conversas")]
        feito = [(rot, s.get(k) or 0, _seta(s.get(k) or 0, a.get(k))) for rot, k in itens]
        acerto = s.get("acerto")

        rv = self.rev.resumo() if self.rev else {}
        fl = self.fila.calcular() if self.fila else {}
        tr = {}
        if self.rast and self.rast.ativo:
            try:
                fontes = self.rast._fontes()
                uso, por_secao = self.rast._uso_no_texto(fontes)
                pars = [p for ps in por_secao.values() for p in ps]
                tr = {"paragrafos": len(pars), "com_fonte": sum(1 for p in pars if p["fontes"]),
                      "alertas": sum(len(p["alertas"]) for p in pars),
                      "secoes_alerta": [k for k, ps in por_secao.items() if any(p["alertas"] for p in ps)][:5]}
            except Exception:
                tr = {}
        bk = self.backup.status() if self.backup else {}

        prox = None
        if fl.get("sugeridas"):
            i = fl["sugeridas"][0]
            prox = f"Ler #{i['codigo']} — {i['titulo'][:90]} ({'; '.join(i['motivos'][:2])})."
        elif fl.get("sem_pdf"):
            i = fl["sem_pdf"][0]
            prox = f"Buscar o PDF de #{i['codigo']} — {i['titulo'][:90]} (Portal CAPES, biblioteca ou autor)."
        return {"ini": ini, "fim": fim, "feito": feito, "acerto": acerto, "acerto_ant": a.get("acerto"),
                "vazia": not any(v for _, v, _ in feito), "revisao": rv, "fila": fl, "rastreio": tr,
                "backup": bk, "proxima": prox}

    def markdown(self, d: dict) -> str:
        L = [f"# Resumo da semana {_br(d['ini'])} a {_br(d['fim'])}/{d['fim']:%Y}", "",
             f"*Gerado pelo painel em {datetime.now():%d/%m/%Y %H:%M}, só com números do cofre e do painel (sem IA).*", "",
             "## O que você fez", "", "| | semana | vs. anterior |", "|---|---|---|"]
        L += [f"| {rot} | {v} | {seta.strip() or '—'} |" for rot, v, seta in d["feito"]]
        if d["acerto"] is not None:
            L.append(f"| Acerto nas revisões | {d['acerto']}% | {_seta(d['acerto'], d['acerto_ant']).strip() or '—'} |")
        if d["vazia"]:
            L += ["", "> Semana sem registro no painel. Se estudou fora dele (papel, outro programa), anote no Registro Semanal do site."]
        rv = d["revisao"]
        if rv.get("total"):
            L += ["", "## Revisão", f"- **{rv['hoje']}** cartão(ões) para revisar hoje · {rv['firmes']}/{rv['total']} firmes"]
        fl = d["fila"]
        if fl.get("sugeridas") or fl.get("sem_pdf"):
            L += ["", "## Próximas leituras (Fila de leitura)"]
            L += [f"{k}. [[{i['stem']}|#{i['codigo']}]] {i['titulo'][:90]} — {i['pontos']} pts" for k, i in enumerate(fl.get("sugeridas", [])[:3], 1)]
            if fl.get("sem_pdf"):
                i = fl["sem_pdf"][0]
                L.append(f"- Buscar o PDF: [[{i['stem']}|#{i['codigo']}]] {i['titulo'][:90]}")
        tr = d["rastreio"]
        if tr.get("paragrafos"):
            L += ["", "## Rastreabilidade do texto",
                  f"- {tr['paragrafos']} parágrafo(s) · {tr['com_fonte']} com fonte identificada · **{tr['alertas']}** alerta(s)"]
            if tr["secoes_alerta"]:
                L.append("- Seções com alerta: " + ", ".join(f"[[{s}]]" for s in tr["secoes_alerta"]) + " — veja [[Rastreabilidade da escrita]]")
        bk = d["backup"]
        L += ["", "## Backup do cofre no GitHub"]
        if not bk:
            L.append("- Ainda não rodou.")
        elif bk.get("ok"):
            L.append(f"- ✔ Último backup em {bk['quando'].replace('T', ' ')} (repositório privado sindrome-de-pandora).")
        else:
            L.append(f"- ✗ {bk.get('erro', 'erro')}")
            L += [f"    - {c}" for c in bk.get("conflitos", [])[:10]]
        if d["proxima"]:
            L += ["", "## Próxima atividade recomendada", d["proxima"]]
        return "\n".join(L) + "\n"

    # ------------------------------------------------------------ envio
    def _html(self, md: str) -> str:
        try:
            import markdown as mdlib
            corpo = mdlib.markdown(md.replace("[[", "").replace("]]", ""), extensions=["extra", "sane_lists"])
        except Exception:
            corpo = "<pre>" + html.escape(md) + "</pre>"
        return (f"<div style=\"font:15px/1.5 system-ui,Segoe UI,sans-serif;color:#1c1b18;max-width:640px\">{corpo}"
                "<p style=\"color:#8b877c;font-size:12px\">Enviado pelo Painel de Estudo (painel_local/resumo_semanal.py) "
                "do seu computador.</p></div>").replace("<table>", "<table style=\"border-collapse:collapse\" cellpadding=\"4\">")

    def enviar(self, assunto: str, md: str) -> None:
        c = self.cfg
        msg = EmailMessage()
        msg["Subject"] = assunto
        msg["From"] = c.get("SMTP_REMETENTE") or c["SMTP_USUARIO"]
        msg["To"] = c["RESUMO_PARA"]
        texto = md.replace("[[", "").replace("]]", "")
        msg.set_content(texto)
        msg.add_alternative(self._html(md), subtype="html")
        host = c.get("SMTP_SERVIDOR") or "smtp.gmail.com"
        porta = int(c.get("SMTP_PORTA") or 465)
        ctx = ssl.create_default_context()
        if porta == 465:
            with smtplib.SMTP_SSL(host, porta, context=ctx, timeout=30) as s:
                s.login(c["SMTP_USUARIO"], c["SMTP_SENHA"].replace(" ", ""))
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, porta, timeout=30) as s:
                s.starttls(context=ctx)
                s.login(c["SMTP_USUARIO"], c["SMTP_SENHA"].replace(" ", ""))
                s.send_message(msg)

    def rodar(self, forcar: bool = False) -> dict:
        """Gera a nota e envia o e-mail da semana devida (uma vez por semana, salvo forcar)."""
        if not forcar and not self.precisa():
            return self._status()
        d = self.montar()
        md = self.markdown(d)
        st = {"semana": d["ini"].isoformat(), "quando": datetime.now().isoformat(timespec="minutes"),
              "nota": "", "email": "não configurado", "erro": ""}
        if self.cofre and self.cofre.ativo:
            pasta = self.cofre.notas / "Resumos semanais"
            pasta.mkdir(parents=True, exist_ok=True)
            nota = pasta / f"Semana {d['ini'].isoformat()}.md"
            nota.write_text(md, encoding="utf-8")
            st["nota"] = str(nota)
        if self.email_configurado:
            try:
                self.enviar(f"Pandora — resumo da semana {_br(d['ini'])} a {_br(d['fim'])}", md)
                st["email"] = f"enviado para {self.cfg['RESUMO_PARA']}"
            except Exception as e:
                st["email"], st["erro"] = "falhou", f"{type(e).__name__}: {str(e)[:250]}"
        self.arq_status.parent.mkdir(parents=True, exist_ok=True)
        if st["erro"]:                                   # não marca a semana como feita: tenta de novo depois
            st_salvo = {**self._status(), "ultimo_erro": st["erro"], "quando_erro": st["quando"]}
        else:
            st_salvo = st
        self.arq_status.write_text(json.dumps(st_salvo, ensure_ascii=False, indent=1), encoding="utf-8")
        return st


if __name__ == "__main__":
    import sys
    sys.argv.append("--sem-navegador")
    import servidor                                   # reaproveita tudo o que o painel já montou
    r = servidor.RESUMO.rodar(forcar="--agora" in sys.argv)
    print(json.dumps(r, ensure_ascii=False, indent=1))
