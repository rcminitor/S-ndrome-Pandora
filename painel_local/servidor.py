"""
Painel local de estudo — Síndrome de Pandora
============================================

Abre no navegador (http://localhost:8765) e roda os agentes no seu PC:

  • Para ler  — clique num PDF: o agente lê, traz só o relevante (traduzido na
                íntegra), mostra as citações e baixa os artigos citados de acesso
                aberto para "1_Para_ler\\<artigo> - citados".
  • Lidos     — o que você marcou como lido (o PDF e a leitura vão para 2_Lido).
  • Acervo    — os PDFs do cofre (PDF\\...). Não são movidos: "Copiar para Para ler"
                faz uma cópia, para não quebrar os links do Obsidian.
  • Minha tese — editor das seções (arquivos .md em Notas\\Tese, visíveis no Obsidian)
                + orientador que questiona, revisa e debate.

Iniciar: dois cliques em "Iniciar painel.bat" (ou: python painel_local/servidor.py)
Só aceita conexões do próprio computador (127.0.0.1).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import threading
import uuid
import webbrowser
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file

RAIZ = Path(__file__).resolve().parent.parent
AGENTES = RAIZ / "agentes_crewai"
sys.path.insert(0, str(AGENTES))
import orientador  # noqa: E402  (lê o mesmo .env de agentes_crewai)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from registro import SITE, Registro  # noqa: E402

CFG = orientador.CFG
COFRE = Path(r"C:\Users\rcmin\OneDrive\Documents\Pos-Graduacao\Doutorado UFC\Síndrome de Pandora")
BASE = COFRE if COFRE.exists() else RAIZ / "estudo_local"      # fora do Windows dele, usa uma pasta local

BIBLIOTECA = Path(CFG.get("BIBLIOTECA") or BASE / "Leitura")
PARA_LER = BIBLIOTECA / "1_Para_ler"
LIDO = BIBLIOTECA / "2_Lido"
ACERVO = Path(CFG.get("ACERVO") or BASE / "PDF")
TESE = Path(CFG.get("TESE_DIR") or BASE / "Notas" / "Tese")
for p in (PARA_LER, LIDO, TESE):
    p.mkdir(parents=True, exist_ok=True)
orientador.CFG["BIBLIOTECA"] = str(BIBLIOTECA)
REG = Registro(BIBLIOTECA, RAIZ, publicar=(CFG.get("PUBLICAR_NO_SITE", "sim").lower() != "nao"))

app = Flask(__name__, static_folder=None)
JOBS: dict[str, dict] = {}
PORTA = 8765
# O site publicado pode conversar com este painel (só ele e o próprio PC).
ORIGENS = {"https://rcminitor.github.io", f"http://localhost:{PORTA}", f"http://127.0.0.1:{PORTA}"}


@app.after_request
def permitir_site(resp):
    origem = request.headers.get("Origin", "")
    if origem in ORIGENS:
        resp.headers["Access-Control-Allow-Origin"] = origem
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Allow-Private-Network"] = "true"   # Chrome: site público → localhost
        resp.headers["Vary"] = "Origin"
    # deixa o site mostrar o painel dentro dele (iframe) e nenhum outro
    resp.headers["Content-Security-Policy"] = "frame-ancestors 'self' " + " ".join(sorted(ORIGENS))
    return resp


@app.get("/api/ping")
def ping():
    return jsonify({"ok": True, "painel": "Pandora"})


@app.post("/api/desligar")
def desligar():
    if request.remote_addr not in ("127.0.0.1", "::1"):
        abort(403)
    threading.Timer(0.5, lambda: __import__("os")._exit(0)).start()
    return jsonify({"ok": True})


# ------------------------------------------------------------------ util
def seguro(rel: str, *raizes: Path) -> Path:
    """Resolve um caminho recebido da página e garante que fica dentro das pastas permitidas."""
    for raiz in raizes or (BIBLIOTECA, ACERVO, TESE):
        alvo = (raiz / rel).resolve()
        if alvo.is_relative_to(raiz.resolve()) and alvo.exists():
            return alvo
    abort(404)


def listar_pdfs(raiz: Path, rotulo: str) -> list[dict]:
    if not raiz.exists():
        return []
    itens = []
    for pdf in sorted(raiz.rglob("*.pdf"), key=lambda p: str(p).lower()):
        rel = pdf.relative_to(raiz)
        itens.append({
            "id": f"{rotulo}:{rel.as_posix()}",
            "nome": pdf.stem,
            "pasta": rel.parent.as_posix() if str(rel.parent) != "." else "",
            "kb": round(pdf.stat().st_size / 1024),
            "leitura": pdf.with_name(pdf.stem + ".leitura.md").exists(),
            "citado": " - citados" in str(rel.parent),
            "reg": REG.resumo(pdf.stem),
        })
    return itens


def resolver_id(ident: str) -> Path:
    rotulo, _, rel = ident.partition(":")
    raiz = {"ler": PARA_LER, "lido": LIDO, "acervo": ACERVO}.get(rotulo)
    if not raiz:
        abort(400)
    return seguro(rel, raiz)


# ------------------------------------------------------------------ páginas
@app.get("/")
def pagina():
    return send_file(Path(__file__).with_name("index.html"))


@app.get("/api/estado")
def estado():
    return jsonify({
        "para_ler": listar_pdfs(PARA_LER, "ler"),
        "lido": listar_pdfs(LIDO, "lido"),
        "acervo": listar_pdfs(ACERVO, "acervo"),
        "secoes": [p.stem for p in sorted(TESE.glob("*.md"))],
        "pastas": {"para_ler": str(PARA_LER), "lido": str(LIDO), "acervo": str(ACERVO), "tese": str(TESE)},
        "ia": bool(CFG.get("LLM_API_KEY")),
        "site": SITE,
    })


@app.get("/pdf")
def abrir_pdf():
    return send_file(resolver_id(request.args["id"]), mimetype="application/pdf")


@app.get("/api/leitura")
def ver_leitura():
    import markdown
    pdf = resolver_id(request.args["id"])
    versao = request.args.get("versao")
    md = REG.arquivo_versao(pdf.stem, versao) if versao else pdf.with_name(pdf.stem + ".leitura.md")
    if not md or not md.exists():
        abort(404)
    return markdown.markdown(md.read_text(encoding="utf-8"), extensions=["extra", "sane_lists"])


# ------------------------------------------------------------------ leitor
@app.post("/api/analisar")
def analisar():
    d = request.get_json()
    pdf = resolver_id(d["id"])
    if d["id"].startswith("acervo:"):                  # do acervo: trabalha numa cópia em Para ler
        copia = PARA_LER / pdf.name
        if not copia.exists():
            shutil.copy2(pdf, copia)
        pdf = copia
    cmd = [sys.executable, "-u", str(AGENTES / "leitor_artigos.py"), str(pdf),
           "--destino", str(pdf.parent / f"{pdf.stem} - citados"),
           "--relatorio-dir", str(pdf.parent),
           "--profundidade", str(int(d.get("profundidade", 1))),
           "--baixar", d.get("baixar", "relevantes")]
    if d.get("sem_traducao"):
        cmd.append("--sem-traducao")
    job = {"id": uuid.uuid4().hex[:8], "arquivo": pdf.name, "status": "rodando", "log": []}
    JOBS[job["id"]] = job
    REG.ia_inicio(pdf, {"profundidade": int(d.get("profundidade", 1)), "sem_traducao": bool(d.get("sem_traducao"))})

    def rodar():
        proc = subprocess.Popen(cmd, cwd=AGENTES, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace",
                                env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
        for linha in proc.stdout:
            job["log"].append(linha.rstrip())
        ok = proc.wait() == 0
        job["versao"] = REG.ia_fim(pdf, ok, job["log"])       # guarda tudo no histórico
        job["status"] = "ok" if ok else "erro"

    threading.Thread(target=rodar, daemon=True).start()
    return jsonify(job)


@app.get("/api/job/<jid>")
def ver_job(jid):
    j = JOBS.get(jid) or abort(404)
    return jsonify({**j, "log": j["log"][-200:]})


@app.post("/api/mover")
def mover():
    d = request.get_json()
    pdf = resolver_id(d["id"])
    destino = LIDO if d["para"] == "lido" else PARA_LER
    origem_raiz = PARA_LER if d["id"].startswith("ler:") else LIDO
    alvo_dir = destino / pdf.parent.relative_to(origem_raiz)
    alvo_dir.mkdir(parents=True, exist_ok=True)
    for arq in [pdf, pdf.with_name(pdf.stem + ".leitura.md"), pdf.with_name(pdf.stem + ".leitura.json")]:
        if arq.exists():
            shutil.move(str(arq), str(alvo_dir / arq.name))
    return jsonify({"ok": True})


@app.post("/api/eu_li")
def eu_li():
    """Você confirma que leu: registra data + nota (a nota fica só no seu PC) e move para Lidos."""
    d = request.get_json()
    pdf = resolver_id(d["id"])
    REG.humano_li(pdf, d.get("nota", ""))
    if d["id"].startswith("ler:"):
        alvo_dir = LIDO / pdf.parent.relative_to(PARA_LER)
        alvo_dir.mkdir(parents=True, exist_ok=True)
        for arq in [pdf, pdf.with_name(pdf.stem + ".leitura.md"), pdf.with_name(pdf.stem + ".leitura.json")]:
            if arq.exists():
                shutil.move(str(arq), str(alvo_dir / arq.name))
    return jsonify({"ok": True})


@app.get("/api/historico")
def historico():
    pdf = resolver_id(request.args["id"])
    return jsonify({"versoes": REG.versoes(pdf.stem), "resumo": REG.resumo(pdf.stem)})


@app.post("/api/publicar")
def publicar_agora():
    REG.publicar("envio manual")
    return jsonify({"ok": True})


@app.post("/api/copiar_para_ler")
def copiar_para_ler():
    pdf = resolver_id(request.get_json()["id"])
    alvo = PARA_LER / pdf.name
    if not alvo.exists():
        shutil.copy2(pdf, alvo)
    return jsonify({"ok": True, "id": f"ler:{alvo.name}"})


# ------------------------------------------------------------------ tese
def secao_path(nome: str) -> Path:
    limpo = "".join(c for c in nome if c not in '\\/:*?"<>|#^[]').strip()[:70]
    if not limpo:
        abort(400)
    return TESE / f"{limpo}.md"


@app.get("/api/secao")
def ler_secao():
    p = secao_path(request.args["nome"])
    return jsonify({"nome": p.stem, "texto": p.read_text(encoding="utf-8") if p.exists() else ""})


@app.post("/api/secao")
def salvar_secao():
    d = request.get_json()
    p = secao_path(d["nome"])
    p.write_text(d["texto"], encoding="utf-8")
    return jsonify({"ok": True, "nome": p.stem})


@app.post("/api/orientador")
def conversar():
    d = request.get_json()
    if not CFG.get("LLM_API_KEY"):
        return jsonify({"erro": "Configure a IA primeiro: python agentes_crewai/configurar.py"}), 400
    texto = secao_path(d["secao"]).read_text(encoding="utf-8") if secao_path(d["secao"]).exists() else d.get("texto", "")
    try:
        resp, tok = orientador.responder(d.get("texto") or texto, d.get("historico", []), d.get("modo", "debater"))
    except Exception as e:                                   # mostra o erro na página em vez de travar
        return jsonify({"erro": f"{type(e).__name__}: {e}"}), 502
    ultima = next((m["content"] for m in reversed(d.get("historico", [])) if m["role"] == "user"), f"({d.get('modo')})")
    orientador.registrar(TESE / "Debates", secao_path(d["secao"]).stem, ultima, resp)
    return jsonify({"resposta": resp, "tokens": tok})


def ja_rodando() -> bool:
    import socket
    with socket.socket() as sk:
        sk.settimeout(0.5)
        return sk.connect_ex(("127.0.0.1", PORTA)) == 0


if __name__ == "__main__":
    porta = PORTA
    if ja_rodando():                                   # nunca duas cópias
        print("O painel já está ligado.")
        if "--sem-navegador" not in sys.argv:
            webbrowser.open(f"http://127.0.0.1:{porta}")
        sys.exit(0)
    print(f"Painel em http://127.0.0.1:{porta}  (feche esta janela para desligar)")
    print(f"  Para ler: {PARA_LER}\n  Lidos:    {LIDO}\n  Acervo:   {ACERVO}\n  Tese:     {TESE}")
    if "--sem-navegador" not in sys.argv:
        threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{porta}")).start()
    app.run(host="127.0.0.1", port=porta, debug=False)
