"""
Painel local de estudo — Síndrome de Pandora
============================================

Abre no navegador (http://localhost:8765) e roda os agentes no seu PC:

  • Próxima leitura — a fila inteligente (painel_local/fila.py): o que ler a seguir,
                com os motivos (fase, citações cruzadas, menções no cofre, texto da tese,
                núcleo menos coberto). As 10 primeiras vão para Notas\\Fila de leitura.
  • Minha tese → "Conferir fontes": rastreabilidade parágrafo a parágrafo
                (painel_local/rastreio.py), que também mantém Notas\\Matriz de síntese
                e Notas\\Rastreabilidade da escrita no cofre.
  • Rotinas    — enquanto o painel está ligado: backup do cofre no GitHub privado
                1×/dia (backup_cofre.py) e resumo da semana toda segunda, por e-mail
                e em Notas\\Resumos semanais (resumo_semanal.py).
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
from types import SimpleNamespace

from flask import Flask, abort, jsonify, request, send_file

RAIZ = Path(__file__).resolve().parent.parent
AGENTES = RAIZ / "agentes_crewai"
sys.path.insert(0, str(AGENTES))
import orientador  # noqa: E402  (lê o mesmo .env de agentes_crewai)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cofre import Cofre  # noqa: E402
from registro import COFRE_ST, SITE, Registro  # noqa: E402
from revisao import Revisao  # noqa: E402
from progresso import Progresso  # noqa: E402
from fila import Fila  # noqa: E402
from rastreio import Rastreio  # noqa: E402
from backup_cofre import Backup  # noqa: E402
from resumo_semanal import Resumo  # noqa: E402
from estadoarte import EstadoArte  # noqa: E402
from fichamentos import Fichamentos  # noqa: E402
from adicionar_pdf import AdicionadorPDF, ErroAdicao  # noqa: E402
from caixa_entrada_pdf import caminho_seguro, listar_entrada  # noqa: E402
from acervo_ativo import codigos_ativos  # noqa: E402
from retirar_fonte import ErroRetirada, RetiradorFonte  # noqa: E402
from acervo import auditar  # noqa: E402
from publicar_acervo import ErroPublicacao, PublicadorAcervo  # noqa: E402
import ia  # noqa: E402
import contexto_cofre  # noqa: E402

CFG = orientador.CFG
COFRE = Path(r"C:\Users\rcmin\OneDrive\Documents\Pos-Graduacao\Doutorado UFC\Síndrome de Pandora")
BASE = COFRE if COFRE.exists() else RAIZ / "estudo_local"      # fora do Windows dele, usa uma pasta local

BIBLIOTECA = Path(CFG.get("BIBLIOTECA") or BASE / "Leitura")
PARA_LER = BIBLIOTECA / "1_Para_ler"
LIDO = BIBLIOTECA / "2_Lido"
ACERVO = Path(CFG.get("ACERVO") or BASE / "PDF")
TESE = Path(CFG.get("TESE_DIR") or BASE / "Notas" / "Tese")
import os  # noqa: E402
os.environ["COFRE_DIR"] = str(BASE)            # agentes (orientador e leitor) leem o mesmo cofre do painel
for p in (PARA_LER, LIDO, TESE):
    p.mkdir(parents=True, exist_ok=True)
orientador.CFG["BIBLIOTECA"] = str(BIBLIOTECA)
COFRE_OBJ = Cofre(BASE, BIBLIOTECA)          # notas de Fontes\\: o registro de verdade
REG = Registro(BIBLIOTECA, RAIZ, publicar=(CFG.get("PUBLICAR_NO_SITE", "sim").lower() != "nao"), cofre=COFRE_OBJ)
REV = Revisao(BIBLIOTECA, COFRE_OBJ, RAIZ)
REG.extras.append(("dados_revisao.js", REV.escrever_site))
PROG = Progresso(BIBLIOTECA, TESE, COFRE_OBJ if COFRE_OBJ.ativo else None, REG, REV, RAIZ, CFG)
REG.extras.append(("dados_progresso.js", PROG.escrever_site))
EA = EstadoArte(RAIZ, COFRE_OBJ)                # Estado da arte por critérios (site + cofre)
REG.extras.append(("dados_estadoarte.js", EA.escrever_site))
FICH = Fichamentos(RAIZ, BASE if COFRE.exists() else None)   # fichamentos do cofre → site
REG.extras.append(("dados_fichamentos.js", FICH.escrever_site))
FILA = Fila(COFRE_OBJ, REG, TESE, {"ler": PARA_LER, "lido": LIDO, "acervo": ACERVO}, casar=contexto_cofre.no_acervo)


RAST = Rastreio(COFRE_OBJ, TESE, BIBLIOTECA)
FILA.uso_no_texto = lambda: RAST._uso_no_texto(RAST._fontes())[0]     # citação ABNT no texto também conta


def atualizar_fila() -> None:
    """Recalcula (em segundo plano) o que é derivado do cofre: a Fila de leitura, a Matriz de
    síntese e a Rastreabilidade da escrita."""
    def rodar():
        for tarefa in (FILA.escrever_obsidian, RAST.escrever_obsidian):
            try:
                tarefa()
            except Exception:
                pass
    threading.Thread(target=rodar, daemon=True).start()


atualizar_fila()
BACKUP = Backup(BASE, BIBLIOTECA)
RESUMO = Resumo(CFG, COFRE_OBJ, PROG, REV, FILA, RAST, BACKUP, BIBLIOTECA)


def rotinas() -> None:
    """Enquanto o painel está ligado: backup do cofre 1×/dia e resumo semanal 1×/semana."""
    import time
    time.sleep(90)                                  # deixa o painel e o OneDrive assentarem
    while True:
        if COFRE_OBJ.ativo:
            try:
                if BACKUP.precisa(24):
                    BACKUP.fazer("diário")
            except Exception:
                pass
            try:
                if RESUMO.precisa():
                    RESUMO.rodar()
            except Exception:
                pass
        time.sleep(3600)


if __name__ == "__main__":
    threading.Thread(target=rotinas, daemon=True).start()
try:
    PROG.fotografar()                       # conta também o que foi escrito direto no Obsidian
except Exception:
    pass

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
app.config["NOTEBOOKLM_HISTORICO"] = str(BIBLIOTECA / "NotebookLM" / "Historico")
from notebook_bridge import bp as notebooklm_bp
app.register_blueprint(notebooklm_bp)
JOBS: dict[str, dict] = {}
ANALISES_ATIVAS: dict[Path, dict] = {}
TRAVA_ANALISES = threading.Lock()
PORTA = 8765
ADICIONADOR_PDF = AdicionadorPDF(BASE, RAIZ)
RETIRADOR_FONTE = RetiradorFonte(BASE, RAIZ)
PUBLICADOR_ACERVO = PublicadorAcervo(BASE, RAIZ)
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
    from collections import Counter
    cont = Counter(c["artigo"] for c in REV.carregar())
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
            "cartoes": cont.get(pdf.stem, 0),
            "fonte": fonte_publica(pdf.name),
        })
    return itens


def fonte_publica(nome_pdf: str) -> dict | None:
    f = COFRE_OBJ.fonte_do_pdf(nome_pdf) if COFRE_OBJ.ativo else None
    return {k: f[k] for k in ("codigo", "status", "nucleo", "fase", "stem")} if f else None


def resolver_id(ident: str) -> Path:
    rotulo, _, rel = ident.partition(":")
    raiz = {"ler": PARA_LER, "lido": LIDO, "acervo": ACERVO}.get(rotulo)
    if not raiz:
        abort(400)
    return seguro(rel, raiz)


def identidade_artigo(ident: str) -> dict:
    import hashlib
    pdf = resolver_id(ident)
    resumo = hashlib.sha256()
    with pdf.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            resumo.update(bloco)
    return {"chave": resumo.hexdigest(), "nome": pdf.stem}


app.config["NOTEBOOKLM_ARTIGO"] = identidade_artigo


@app.get("/api/artigo/materiais")
def materiais_artigo():
    ident = request.args["id"]
    pdf = resolver_id(ident)
    audios = [ext for ext in (".mp3", ".m4a", ".wav", ".ogg") if pdf.with_suffix(ext).is_file()]
    return jsonify({**identidade_artigo(ident), "audios": audios})


@app.get("/api/artigo/audio")
def audio_artigo():
    pdf = resolver_id(request.args["id"])
    ext = request.args.get("ext")
    if ext not in (".mp3", ".m4a", ".wav", ".ogg"):
        abort(400)
    audio = seguro(str(pdf.with_suffix(ext)), pdf.parent)
    return send_file(audio, conditional=True)


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
        "cofre": {**COFRE_ST, "ativo": COFRE_OBJ.ativo},
        "backup": BACKUP.status(),
        "resumo": {"email": RESUMO.email_configurado, **{k: v for k, v in RESUMO._status().items() if k != "nota"}},
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
    original = pdf
    if d["id"].startswith("acervo:"):                  # usa a mesma chave da cópia em Para ler
        pdf = PARA_LER / pdf.name
    cmd = [sys.executable, "-u", str(AGENTES / "leitor_artigos.py"), str(pdf),
           "--destino", str(pdf.parent / f"{pdf.stem} - citados"),
           "--relatorio-dir", str(pdf.parent),
           "--profundidade", str(int(d.get("profundidade", 1))),
           "--baixar", d.get("baixar", "relevantes")]
    if d.get("sem_traducao"):
        cmd.append("--sem-traducao")
    chave = pdf.resolve()
    with TRAVA_ANALISES:
        if chave in ANALISES_ATIVAS:
            # Outro clique/aba acompanha a execução existente, com as opções originais.
            return jsonify({**ANALISES_ATIVAS[chave], "reutilizado": True})
        if original != pdf and not pdf.exists():
            shutil.copy2(original, pdf)
        job = {"id": uuid.uuid4().hex[:8], "arquivo": pdf.name, "status": "rodando", "log": []}
        JOBS[job["id"]] = job
        ANALISES_ATIVAS[chave] = job

    def rodar():
        ok = False
        iniciado = False
        try:
            REG.ia_inicio(pdf, {"profundidade": int(d.get("profundidade", 1)), "sem_traducao": bool(d.get("sem_traducao"))})
            iniciado = True
            with subprocess.Popen(cmd, cwd=AGENTES, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, encoding="utf-8", errors="replace",
                                  env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"}) as proc:
                for linha in proc.stdout:
                    job["log"].append(linha.rstrip())
                ok = proc.wait() == 0
        except Exception as e:
            job["log"].append(f"Falha na análise: {type(e).__name__}: {e}")
        finally:
            try:
                if iniciado:
                    job["versao"] = REG.ia_fim(pdf, ok, job["log"])
                atualizar_fila()
            except Exception as e:
                ok = False
                job["log"].append(f"Falha ao registrar análise: {type(e).__name__}: {e}")
            finally:
                with TRAVA_ANALISES:
                    job["status"] = "ok" if ok else "erro"
                    ANALISES_ATIVAS.pop(chave, None)

    try:
        threading.Thread(target=rodar, daemon=True).start()
    except Exception as e:
        with TRAVA_ANALISES:
            job["status"] = "erro"
            job["log"].append(f"Não foi possível iniciar a análise: {e}")
            ANALISES_ATIVAS.pop(chave, None)
    return jsonify(job)


@app.get("/api/job/<jid>")
def ver_job(jid):
    j = JOBS.get(jid) or abort(404)
    return jsonify({**j, "log": j["log"][-200:]})


TRAVA_MOVIMENTO = threading.Lock()


def mover_leitura(pdf: Path, origem: Path, destino: Path) -> Path:
    """Copia o conjunto sem sobrescrever; só remove originais após copiar tudo."""
    alvo_dir = destino / pdf.parent.relative_to(origem)
    if alvo_dir.resolve() == pdf.parent.resolve():
        return pdf
    with TRAVA_MOVIMENTO:
        arquivos = [p for p in (pdf, pdf.with_suffix(".leitura.md"),
                                pdf.with_suffix(".leitura.json"),
                                *(pdf.with_suffix(ext) for ext in (".mp3", ".m4a", ".wav", ".ogg"))) if p.exists()]
        if any((alvo_dir / p.name).exists() for p in arquivos):
            raise FileExistsError("Já existe um PDF ou relatório com esse nome no destino. Nenhum arquivo foi movido.")
        alvo_dir.mkdir(parents=True, exist_ok=True)
        criados = []
        try:
            for arq in arquivos:
                alvo = alvo_dir / arq.name
                with alvo.open("xb") as saida:
                    criados.append(alvo)
                    with arq.open("rb") as entrada:
                        shutil.copyfileobj(entrada, saida)
                shutil.copystat(arq, alvo)
        except Exception:
            for alvo in criados:
                alvo.unlink()
            raise
        for arq in arquivos:
            arq.unlink()
    return alvo_dir / pdf.name


@app.post("/api/mover")
def mover():
    d = request.get_json()
    pdf = resolver_id(d["id"])
    destino = LIDO if d["para"] == "lido" else PARA_LER
    origem_raiz = PARA_LER if d["id"].startswith("ler:") else LIDO
    try:
        mover_leitura(pdf, origem_raiz, destino)
    except FileExistsError as e:
        return jsonify({"erro": str(e)}), 409
    return jsonify({"ok": True})


@app.post("/api/eu_li")
def eu_li():
    """Você confirma que leu: registra data + nota (a nota fica só no seu PC) e move para Lidos."""
    d = request.get_json()
    pdf = resolver_id(d["id"])
    if d["id"].startswith("ler:"):
        try:
            pdf = mover_leitura(pdf, PARA_LER, LIDO)
        except FileExistsError as e:
            return jsonify({"erro": str(e)}), 409
    REG.humano_li(pdf, d.get("nota", ""))
    atualizar_fila()
    return jsonify({"ok": True})


@app.get("/api/historico")
def historico():
    pdf = resolver_id(request.args["id"])
    return jsonify({"versoes": REG.versoes(pdf.stem), "resumo": REG.resumo(pdf.stem)})


@app.post("/api/publicar")
def publicar_agora():
    REG.publicar("envio manual")
    return jsonify({"ok": True})


@app.post("/api/acervo/adicionar")
def adicionar_pdf_acervo():
    """Inclui PDF + nota, valida, cria commits restritos e envia os dois repositórios."""
    try:
        envio = request.files.get("pdf")
        entrada_nome = str(request.form.get("entrada", "") or "").strip()
        if envio and getattr(envio, "filename", "") and entrada_nome:
            raise ErroAdicao("Escolha o upload ou a Caixa de entrada, não os dois.")
        origem = caminho_seguro(BASE, entrada_nome) if entrada_nome else None
        arquivo = SimpleNamespace(filename=origem.name) if origem else envio
        resultado = ADICIONADOR_PDF.adicionar(arquivo, request.form, origem_movel=origem)
    except ErroAdicao as e:
        return jsonify({"ok": False, "erro": str(e)}), e.status
    except ValueError as e:
        return jsonify({"ok": False, "erro": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "erro": f"Falha ao adicionar PDF: {type(e).__name__}: {e}"}), 500
    COFRE_OBJ._cache = None
    atualizar_fila()
    try:
        publicacao = PUBLICADOR_ACERVO.publicar(
            str(resultado["item"]["codigo"]), BASE / "Fontes" / resultado["nota"], resultado["arquivo"],
        )
    except ErroPublicacao as e:
        return jsonify({
            "ok": True, "publicado": False, **resultado,
            "aviso": "Fonte salva e validada localmente, mas o envio ao GitHub falhou.",
            "erro_publicacao": str(e),
        }), 202
    return jsonify({"ok": True, "publicado": True, "publicacao": publicacao, **resultado})


@app.get("/api/acervo/entrada")
def caixa_entrada_acervo():
    """Lista PDFs ainda não publicados e metadados apresentados apenas como sugestões."""
    try:
        return jsonify({"ok": True, **listar_entrada(BASE)})
    except Exception as e:
        return jsonify({"ok": False, "erro": f"Falha ao ler a Caixa de entrada: {e}"}), 500


@app.get("/api/acervo/saude")
def saude_acervo():
    """Diagnóstico somente leitura usado pela janela administrativa do site."""
    try:
        return jsonify({"ok": True, "relatorio": auditar(BASE, RAIZ)})
    except Exception as e:
        return jsonify({"ok": False, "erro": f"Falha na auditoria: {type(e).__name__}: {e}"}), 500


@app.post("/api/acervo/retirar")
def retirar_fonte_acervo():
    """Retira uma fonte de modo recuperável e publica a nova visão do Acervo."""
    dados = request.get_json(force=True) or {}
    try:
        resultado = RETIRADOR_FONTE.retirar(dados.get("codigo", ""), dados.get("confirmacao", ""))
    except ErroRetirada as e:
        return jsonify({"ok": False, "erro": str(e)}), e.status
    except Exception as e:
        return jsonify({"ok": False, "erro": f"Falha ao retirar fonte: {type(e).__name__}: {e}"}), 500
    COFRE_OBJ._cache = None
    atualizar_fila()
    try:
        publicacao = PUBLICADOR_ACERVO.publicar_retirada(
            resultado["codigo"], resultado["nota"], resultado["pdf_anterior"],
            BASE / resultado["pdf_arquivado"],
        )
    except ErroPublicacao as e:
        return jsonify({
            "ok": True, "publicado": False,
            "codigo": resultado["codigo"], "pdf_arquivado": resultado["pdf_arquivado"],
            "aviso": "Fonte retirada localmente, mas o envio ao GitHub falhou.",
            "erro_publicacao": str(e),
        }), 202
    return jsonify({
        "ok": True, "publicado": True, "codigo": resultado["codigo"],
        "pdf_arquivado": resultado["pdf_arquivado"], "publicacao": publicacao,
    })


# ------------------------------------------------------------------ estado da arte
@app.get("/api/estadoarte")
def estadoarte_ler():
    dados = EA.ler()
    ativos = codigos_ativos(RAIZ)
    dados["fontes"] = [f for f in dados.get("fontes", []) if str(f.get("codigo")) in ativos]
    return jsonify(dados)


@app.post("/api/estadoarte")
def estadoarte_salvar():
    """Inclui ou atualiza uma fonte na Tabela 3 (site e cofre) e publica no GitHub."""
    d = request.get_json(force=True) or {}
    if d.get("remover"):
        ok = EA.remover(str(d["remover"]))
        if ok:
            REG.publicar("estado da arte: fonte removida")
        return jsonify({"ok": ok})
    codigo = str(d.get("codigo", "")).strip().removeprefix("#")
    if codigo not in codigos_ativos(RAIZ):
        return jsonify({
            "ok": False,
            "erros": ["Código fora do acervo publicado. Sem PDF válido, a fonte não entra no Estado da Arte."],
        }), 400
    erros = EA.salvar(d)
    if erros:
        return jsonify({"ok": False, "erros": erros}), 400
    REG.publicar(f"estado da arte: fonte {d.get('codigo')}")
    dados = EA.ler()
    ativos = codigos_ativos(RAIZ)
    dados["fontes"] = [f for f in dados.get("fontes", []) if str(f.get("codigo")) in ativos]
    return jsonify({"ok": True, "dados": dados})


# ------------------------------------------------------------------ revisão espaçada
@app.post("/api/cartoes/gerar")
def gerar_cartoes():
    """Cria cartões de revisão a partir da leitura da IA ou do seu fichamento no cofre."""
    d = request.get_json()
    pdf = resolver_id(d["id"])
    fonte = COFRE_OBJ.fonte_do_pdf(pdf.name) if COFRE_OBJ.ativo else None
    codigo = fonte["codigo"] if fonte else ""
    if d.get("origem") == "fichamento":
        texto = contexto_cofre.fichamentos("", codigos=[codigo]) if codigo else ""
        origem = f"fichamento #{codigo} do cofre (conferido no PDF)"
    else:
        js = pdf.with_name(pdf.stem + ".leitura.json")
        if not js.exists():
            return jsonify({"erro": "Leia o artigo com o agente primeiro."}), 400
        texto = REV.texto_da_leitura(js)
        origem = "leitura da IA (tradução automática — conferir no PDF)"
    if not texto:
        return jsonify({"erro": "Não encontrei texto para gerar cartões."}), 400
    try:
        novos, tokens = REV.gerar(CFG, ia, pdf.stem, codigo, texto, origem)
    except Exception as e:
        return jsonify({"erro": f"{type(e).__name__}: {str(e)[:300]}"}), 502
    REV.escrever_obsidian()
    REG.publicar_depois("novos cartões de revisão")
    return jsonify({"novos": novos, "tokens": tokens})


@app.get("/api/fila")
def fila():
    d = FILA.calcular()
    return jsonify({**d, "sugeridas": d["sugeridas"][:25], "sem_pdf": d["sem_pdf"][:15],
                    "total_pendentes": len(d["sugeridas"]) + len(d["sem_pdf"])})


@app.get("/api/rastreio")
def rastreio():
    """Confere as fontes de uma seção da tese, parágrafo a parágrafo (sem IA)."""
    return jsonify(RAST.conferir_secao(secao_path(request.args["secao"]).stem))


@app.post("/api/backup")
def backup_agora():
    return jsonify(BACKUP.fazer("pelo painel"))


@app.post("/api/resumo")
def resumo_agora():
    """Gera (e envia, se configurado) o resumo da semana passada agora."""
    try:
        return jsonify(RESUMO.rodar(forcar=True))
    except Exception as e:
        return jsonify({"erro": f"{type(e).__name__}: {e}"}), 500


@app.get("/api/progresso")
def progresso():
    sem = PROG.semanas()
    atual = PROG.fotografar()
    return jsonify({"semana": sem[-1] if sem else None, "palavras": sum(atual.values()), "ppp": PROG.ppp})


@app.get("/api/revisao")
def revisao():
    artigo = request.args.get("artigo")
    fila = REV.fila_hoje(artigo)
    return jsonify({"fila": fila[:50], "resumo": REV.resumo()})


@app.post("/api/revisao/responder")
def responder_cartao():
    d = request.get_json()
    c = REV.responder(d["id"], bool(d["lembrou"]))
    REV.escrever_obsidian()
    REG.publicar_depois("sessão de revisão")
    return jsonify({"cartao": c})


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
    try:
        with p.open("x" if d.get("criar") else "w", encoding="utf-8") as arquivo:
            arquivo.write(d["texto"])
    except FileExistsError:
        return jsonify({"erro": "Já existe uma seção com esse nome. Abra a seção existente ou escolha outro nome."}), 409
    try:
        PROG.fotografar()
        atualizar_fila()                         # fonte citada no texto e ainda não lida sobe na fila
        REG.publicar_depois("escrita da tese")
    except Exception:
        pass
    return jsonify({"ok": True, "nome": p.stem})


@app.post("/api/fichamento")
def salvar_fichamento():
    d = request.get_json() or {}
    codigo = str(d.get("codigo", "")).strip()
    nome_arq = d.get("arquivo", "")
    texto = d.get("texto", "")
    if not codigo or not texto:
        return jsonify({"erro": "Código e texto são obrigatórios."}), 400
    if codigo not in codigos_ativos(RAIZ):
        return jsonify({
            "erro": "Código fora do acervo publicado. Sem PDF válido, não é possível salvar fichamento."
        }), 400

    pasta_fich = COFRE / "Fichamentos"
    if not pasta_fich.exists():
        return jsonify({"erro": "Pasta Fichamentos não encontrada no cofre."}), 404

    arquivo_dest = None
    for f in pasta_fich.glob("*.md"):
        if f.name.startswith(f"{codigo} —") or f.name.startswith(f"{codigo} "):
            arquivo_dest = f
            break

    if not arquivo_dest:
        if not nome_arq or not nome_arq.endswith(".md"):
            nome_arq = f"{codigo} — Fichamento.md"
        arquivo_dest = pasta_fich / nome_arq

    arquivo_dest.write_text(texto, encoding="utf-8")
    try:
        FICH.escrever_site()
    except Exception:
        pass
    return jsonify({"ok": True, "arquivo": arquivo_dest.name})


@app.post("/api/orientador")
def conversar():
    d = request.get_json()
    if not CFG.get("LLM_API_KEY"):
        return jsonify({"erro": "Configure a IA primeiro: python agentes_crewai/configurar.py"}), 400
    texto = secao_path(d["secao"]).read_text(encoding="utf-8") if secao_path(d["secao"]).exists() else d.get("texto", "")
    try:
        alertas = ""
        if d.get("modo") in ("revisar", "questionar"):
            try:
                alertas = RAST.alertas_em_texto(RAST.conferir_secao(secao_path(d["secao"]).stem))
            except Exception:
                pass
        resp, tok = orientador.responder(d.get("texto") or texto, d.get("historico", []), d.get("modo", "debater"),
                                         alertas=alertas)
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
