"""NotebookLM opcional; perfis privados e comandos sem shell."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
from datetime import datetime
from urllib.parse import urlparse
from uuid import UUID, uuid4

from flask import Blueprint, current_app, jsonify, request, send_file

bp = Blueprint("notebooklm", __name__)
PERFIS = {"pro": "pandora-pro", "plus": "pandora-plus"}
TRAVAS = {conta: threading.Lock() for conta in PERFIS}
CONFIG = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Pandora" / "notebooklm.json"
TRAVA_CONFIG = threading.Lock()
FORMATOS = {"audio": ".m4a", "report": ".md", "infographic": ".png",
            "slide-deck": ".pdf", "video": ".mp4"}


def pasta_importados():
    return pasta_historico().parent / "Materiais"


def importar_material(conta, caderno, material, artigo=None):
    import hashlib
    remoto = str(UUID(material["id"]))
    tipo = material.get("type_id")
    if material.get("status") != "completed" or tipo not in FORMATOS:
        raise ValueError("Este material ainda não está pronto ou seu formato não é suportado.")
    chave = hashlib.sha256(f"{conta}/{caderno}/{remoto}".encode()).hexdigest()
    destino = pasta_importados() / chave
    if (destino / "registro.json").exists():
        registro = json.loads((destino / "registro.json").read_text(encoding="utf-8"))
        if artigo and artigo not in registro.get("artigos", []):
            registro.setdefault("artigos", []).append(artigo)
            temp = destino / "registro.tmp"
            temp.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(destino / "registro.json")
        return registro
    pasta_importados().mkdir(parents=True, exist_ok=True)
    tmp = pasta_importados() / ("." + uuid4().hex + ".tmp")
    tmp.mkdir()
    arquivo = "material" + FORMATOS[tipo]
    try:
        executar(conta, ["download", tipo, str(tmp / arquivo), "-n", caderno,
                        "-a", remoto, "--json", "--no-clobber"])
        if not (tmp / arquivo).is_file() or (tmp / arquivo).stat().st_size == 0:
            raise RuntimeError("O download não produziu um arquivo válido.")
        registro = {"id": chave, "conta": conta, "caderno": caderno, "artifact_id": remoto,
                    "titulo": material.get("title", tipo), "tipo": tipo, "arquivo": arquivo,
                    "data": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "artigos": [artigo] if artigo else []}
        (tmp / "registro.json").write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.rename(destino)
        return registro
    finally:
        if tmp.exists():
            if not tmp.resolve().is_relative_to(pasta_importados().resolve()):
                raise RuntimeError("Pasta temporária fora do destino permitido.")
            shutil.rmtree(tmp)  # pasta temporária exclusiva, criada acima dentro de Materiais


@bp.get("/api/notebooklm/importados")
def listar_importados():
    itens = []
    for arq in pasta_importados().glob("*/registro.json"):
        if arq.parent.name.startswith("."):
            continue
        try:
            d = json.loads(arq.read_text(encoding="utf-8"))
            if request.args.get("conta") and d["conta"] != request.args["conta"]:
                continue
            if request.args.get("artigo") and not any(a["chave"] == request.args["artigo"] for a in d.get("artigos", [])):
                continue
            itens.append(d)
        except (OSError, ValueError, KeyError):
            continue
    return jsonify(itens=sorted(itens, key=lambda d: d["data"], reverse=True))


@bp.get("/api/notebooklm/importados/<ident>")
def abrir_importado(ident):
    import re
    if not re.fullmatch(r"[a-f0-9]{64}", ident):
        return jsonify(erro="Material inválido."), 400
    pasta = pasta_importados() / ident
    if not (pasta / "registro.json").is_file():
        return jsonify(erro="Material não encontrado."), 404
    d = json.loads((pasta / "registro.json").read_text(encoding="utf-8"))
    arquivo = pasta / ("material" + FORMATOS[d["tipo"]])
    return send_file(arquivo, as_attachment=d["tipo"] not in ("audio", "video", "infographic"), conditional=True)


def pasta_historico():
    return Path(current_app.config["NOTEBOOKLM_HISTORICO"])


def salvar_consulta(conta, caderno, prompt, resultado, artigo=None):
    ident = uuid4().hex
    agora = datetime.now().astimezone().isoformat(timespec="seconds")
    registro = {"id": ident, "data": agora, "conta": conta, "caderno": caderno,
                "prompt": prompt, "answer": resultado.get("answer", ""),
                "references": resultado.get("references", []),
                "conversation_id": resultado.get("conversation_id"), "artigo": artigo}
    raiz = pasta_historico()
    raiz.mkdir(parents=True, exist_ok=True)
    tmp = raiz / ("." + ident + ".tmp")
    tmp.mkdir()
    try:
        (tmp / "consulta.json").write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
        texto = (f"# Consulta ao NotebookLM\n\nData: {agora}\n\nConta: {conta}\n\n"
                 f"Caderno: {caderno}\n\nConversa: {registro['conversation_id'] or 'não informada'}\n\n"
                 f"Artigo: {(artigo or {}).get('nome', 'não vinculado')}\n\n"
                 f"## Pergunta\n\n{prompt}\n\n## Resposta\n\n{registro['answer']}\n\n"
                 "## Referências retornadas\n\n" + json.dumps(registro["references"], ensure_ascii=False, indent=2) + "\n")
        (tmp / "Consulta.md").write_text(texto, encoding="utf-8")
        tmp.rename(raiz / ident)
    except Exception:
        # Só remove os arquivos temporários desta tentativa.
        for nome in ("consulta.json", "Consulta.md"):
            (tmp / nome).unlink(missing_ok=True)
        tmp.rmdir()
        raise
    return ident


@bp.get("/api/notebooklm/historico")
def listar_historico():
    conta = request.args.get("conta", "pro")
    if conta not in PERFIS:
        return jsonify(erro="Conta inválida."), 400
    itens = []
    for arq in pasta_historico().glob("*/consulta.json"):
        if arq.parent.name.startswith("."):
            continue
        try:
            d = json.loads(arq.read_text(encoding="utf-8"))
            filtro = request.args.get("artigo")
            if d["conta"] == conta and (not filtro or (d.get("artigo") or {}).get("chave") == filtro):
                itens.append({k: d[k] for k in ("id", "data", "conta", "caderno", "prompt")})
        except (OSError, ValueError, KeyError):
            continue
    return jsonify(itens=sorted(itens, key=lambda d: d["data"], reverse=True))


@bp.get("/api/notebooklm/historico/<ident>")
def abrir_historico(ident):
    try:
        ident = UUID(ident).hex
    except ValueError:
        return jsonify(erro="Consulta inválida."), 400
    arq = pasta_historico() / ident / "consulta.json"
    if not arq.is_file():
        return jsonify(erro="Consulta não encontrada."), 404
    return jsonify(json.loads(arq.read_text(encoding="utf-8")))


def caderno_id(valor):
    valor = str(valor).strip()
    if "://" in valor:
        url = urlparse(valor)
        if url.scheme != "https" or url.hostname not in (
                "notebooklm.google.com", "notebooklm.google", "gemininotebook.google.com",
                "notebook.google.com"):
            raise ValueError("Use o link do caderno no NotebookLM.")
        partes = url.path.strip("/").split("/")
        if len(partes) != 2 or partes[0] != "notebook":
            raise ValueError("Abra o caderno e copie o link completo.")
        valor = partes[1]
    try:
        return str(UUID(valor))
    except ValueError:
        raise ValueError("Informe um link de caderno ou ID válido.") from None


def configuracao():
    if CONFIG.exists():
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    return {"principal": "pro", "cadernos": {"pro": "", "plus": ""}}


def executar(conta, args, prompt=None):
    cli = shutil.which("notebooklm")
    if not cli:
        candidato = Path.home() / ".local/bin/notebooklm.exe"
        if candidato.is_file():
            cli = str(candidato)
    if not cli:
        raise RuntimeError("NotebookLM não instalado neste computador.")
    ambiente = dict(os.environ)
    # Não herdar credenciais inline ou perfil/caderno de outra integração.
    for chave in ("NOTEBOOKLM_AUTH_JSON", "NOTEBOOKLM_STORAGE_PATH", "NOTEBOOKLM_PROFILE",
                  "NOTEBOOKLM_NOTEBOOK", "NOTEBOOKLM_HOME", "NOTEBOOKLM_REFRESH_CMD"):
        ambiente.pop(chave, None)
    ambiente["PYTHONIOENCODING"] = "utf-8"
    try:
        r = subprocess.run([cli, "-p", PERFIS[conta], *args], input=prompt,
                           capture_output=True, text=True, encoding="utf-8", env=ambiente,
                           timeout=180, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        raise RuntimeError("A consulta demorou demais. Confira o caderno antes de tentar novamente.") from None
    if r.returncode:
        # Saídas brutas de autenticação não devem ir ao navegador ou aos logs.
        raise RuntimeError("Não foi possível concluir. Verifique o login desta conta e o acesso ao caderno.")
    return json.loads(r.stdout)


def autenticar(conta):
    d = executar(conta, ["auth", "check", "--test", "--passive", "--json"])
    if d.get("status") != "ok" or d.get("checks", {}).get("token_fetch") is not True:
        raise RuntimeError("Faça login no perfil desta conta antes de continuar.")


@bp.before_request
def proteger():
    if request.host not in ("127.0.0.1:8765", "localhost:8765"):
        return jsonify(erro="Acesso permitido somente pelo painel local."), 403
    if request.method == "POST":
        if request.headers.get("Origin") not in (None, "http://127.0.0.1:8765", "http://localhost:8765"):
            return jsonify(erro="Abra o NotebookLM pelo painel local."), 403
        if not request.is_json:
            return jsonify(erro="Envie dados JSON."), 415


@bp.get("/notebooklm")
def pagina():
    return send_file(Path(__file__).with_name("notebooklm.html"))


@bp.get("/api/notebooklm/config")
def ler_config():
    return jsonify(configuracao())


@bp.post("/api/notebooklm/<acao>")
def operar(acao):
    d = request.get_json()
    conta = d.get("conta", "pro")
    if conta not in PERFIS or acao not in ("salvar", "verificar", "listar", "perguntar", "materiais", "importar"):
        return jsonify(erro="Conta ou ação inválida."), 400
    if not TRAVAS[conta].acquire(blocking=False):
        return jsonify(erro="Esta conta já tem uma consulta em andamento. Aguarde."), 409
    try:
        if acao == "salvar":
            ident = caderno_id(d.get("caderno", ""))
            with TRAVA_CONFIG:
                cfg = configuracao()
                cfg["cadernos"][conta] = ident
                CONFIG.parent.mkdir(parents=True, exist_ok=True)
                tmp = CONFIG.with_suffix(".tmp")
                tmp.write_text(json.dumps(cfg), encoding="utf-8")
                tmp.replace(CONFIG)
            return jsonify(ok=True)
        autenticar(conta)
        if acao == "verificar":
            return jsonify(ok=True)
        if acao == "listar":
            return jsonify(executar(conta, ["list", "--json"]))
        ident = caderno_id(configuracao()["cadernos"].get(conta, ""))
        if acao in ("materiais", "importar"):
            # Confere novamente a identidade, o tipo e a conclusão no caderno selecionado.
            if d.get("caderno_id") and d["caderno_id"] != ident:
                raise ValueError("O caderno mudou. Atualize a lista de materiais.")
            lista = executar(conta, ["artifact", "list", "-n", ident, "--json"])
            if acao == "materiais":
                return jsonify(caderno_id=ident, itens=[{**m, "suportado": m.get("type_id") in FORMATOS} for m in lista.get("artifacts", [])])
            material = next((m for m in lista.get("artifacts", []) if m["id"] == d.get("material")), None)
            if not material:
                raise ValueError("Material não encontrado neste caderno.")
            artigo = current_app.config["NOTEBOOKLM_ARTIGO"](d["artigo"]) if d.get("artigo") else None
            return jsonify(importar_material(conta, ident, material, artigo))
        prompt = str(d.get("prompt", "")).strip()
        if not prompt or len(prompt) > 20000:
            raise ValueError("Escreva uma pergunta com até 20.000 caracteres.")
        artigo = current_app.config["NOTEBOOKLM_ARTIGO"](d["artigo"]) if d.get("artigo") else None
        resultado = executar(conta, ["ask", "-n", ident, "--prompt-file", "-", "--json"], prompt)
        try:
            resultado["historico_id"] = salvar_consulta(conta, ident, prompt, resultado, artigo)
        except OSError:
            resultado["aviso"] = "Resposta recebida, mas não foi salva no cofre. Copie o texto antes de fechar a página."
        return jsonify(resultado)
    except ValueError as e:
        return jsonify(erro=str(e)), 400
    except (OSError, RuntimeError):
        return jsonify(erro="Não foi possível concluir. Confira o login, o caderno e a conexão. Não houve troca de conta."), 502
    finally:
        TRAVAS[conta].release()
