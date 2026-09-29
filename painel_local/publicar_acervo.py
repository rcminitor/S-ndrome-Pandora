"""Commit e push restritos aos arquivos produzidos pela inclusão de uma fonte."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

from guardiao_acervo import validar_publicacao


TRAVA_PUBLICACAO = threading.Lock()


class ErroPublicacao(RuntimeError):
    pass


class PublicadorAcervo:
    def __init__(self, cofre: Path, painel: Path):
        self.cofre = Path(cofre)
        self.painel = Path(painel)

    def _executar(self, comando: list[str], cwd: Path, timeout: int = 240) -> subprocess.CompletedProcess:
        resultado = subprocess.run(
            comando, cwd=cwd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
        if resultado.returncode != 0:
            detalhe = (resultado.stderr or resultado.stdout).strip()[-1000:]
            raise ErroPublicacao(f"{' '.join(comando[:3])}: {detalhe}")
        return resultado

    def _git(self, repo: Path, *args: str, aceitar: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess:
        resultado = subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=240,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
        if resultado.returncode not in aceitar:
            detalhe = (resultado.stderr or resultado.stdout).strip()[-1000:]
            raise ErroPublicacao(f"git {args[0]}: {detalhe}")
        return resultado

    def _destino_remoto(self, repo: Path) -> tuple[str, str]:
        upstream = self._git(
            repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}",
            aceitar=(0, 128),
        )
        valor = upstream.stdout.strip()
        if upstream.returncode == 0 and "/" in valor:
            return tuple(valor.split("/", 1))  # type: ignore[return-value]
        ramo = self._git(repo, "branch", "--show-current").stdout.strip()
        if not ramo:
            raise ErroPublicacao("Não foi possível identificar o ramo Git para publicação.")
        return "origin", ramo

    def _commit_e_push(self, repo: Path, caminhos: list[str], mensagem: str) -> dict:
        remoto, ramo = self._destino_remoto(repo)
        self._git(repo, "pull", "--rebase", "--autostash", remoto, ramo)
        self._git(repo, "add", "-A", "--", *caminhos)
        mudou = self._git(repo, "diff", "--cached", "--quiet", "--", *caminhos, aceitar=(0, 1))
        if mudou.returncode == 1:
            self._git(repo, "commit", "-m", mensagem, "--", *caminhos)
        commit = self._git(repo, "rev-parse", "--short", "HEAD").stdout.strip()
        self._git(repo, "push", remoto, f"HEAD:{ramo}")
        return {"commit": commit, "remoto": remoto, "ramo": ramo}

    def _validar(self) -> None:
        relatorio = validar_publicacao(self.painel)
        if not relatorio.ok:
            raise ErroPublicacao(relatorio.texto())
        testes = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"]
        self._executar(testes, self.painel)

    def publicar(self, codigo: str, nota: Path, caminho_pdf: str) -> dict:
        nota = Path(nota).resolve()
        try:
            nota_rel = nota.relative_to(self.cofre.resolve()).as_posix()
        except ValueError as exc:
            raise ErroPublicacao("A nota criada ficou fora do cofre.") from exc
        pdf_rel = str(caminho_pdf).replace("\\", "/")
        dados_painel = [
            "dados_inventario.js", "dados_pdfs.js", "dados_fichamentos.js",
            "index.html", pdf_rel,
        ]
        with TRAVA_PUBLICACAO:
            self._validar()
            cofre = self._commit_e_push(
                self.cofre, [nota_rel], f"acervo: cadastrar fonte {codigo} pelo painel",
            )
            painel = self._commit_e_push(
                self.painel, dados_painel, f"acervo: publicar fonte {codigo} pelo painel",
            )
        return {"cofre": cofre, "painel": painel, "testes": "aprovados", "guardiao": "aprovado"}

    def publicar_correcao(self, caminhos: list[str], mensagem: str = "acervo: aplicar correcoes automaticas") -> dict:
        """Publica somente derivados já aprovados; nunca inclui notas ou PDFs não autorizados."""
        caminhos = list(dict.fromkeys(str(c).replace("\\", "/") for c in caminhos))
        with TRAVA_PUBLICACAO:
            self._validar()
            painel = self._commit_e_push(self.painel, caminhos, mensagem)
        return {"painel": painel, "testes": "aprovados", "guardiao": "aprovado"}

    def publicar_retirada(self, codigo: str, nota: Path, pdf_anterior: str,
                          pdf_arquivado: Path) -> dict:
        nota_rel = Path(nota).resolve().relative_to(self.cofre.resolve()).as_posix()
        pdf_rel = str(pdf_anterior).replace("\\", "/")
        painel_pdf = (self.painel / pdf_rel).resolve()
        if not painel_pdf.is_relative_to(self.painel.resolve()):
            raise ErroPublicacao("Caminho do PDF retirado ficou fora do painel.")
        derivados = [
            "dados_inventario.js", "dados_pdfs.js", "dados_fichamentos.js", "index.html", pdf_rel,
        ]
        removeu_painel = False
        with TRAVA_PUBLICACAO:
            self._validar()
            if painel_pdf.exists():
                painel_pdf.unlink()
                removeu_painel = True
            try:
                cofre = self._commit_e_push(
                    self.cofre, [nota_rel, pdf_rel], f"acervo: retirar fonte {codigo}",
                )
                painel = self._commit_e_push(
                    self.painel, derivados, f"acervo: retirar fonte {codigo}",
                )
            except Exception:
                if removeu_painel and not painel_pdf.exists() and Path(pdf_arquivado).is_file():
                    painel_pdf.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(pdf_arquivado, painel_pdf)
                raise
        return {"cofre": cofre, "painel": painel, "testes": "aprovados", "guardiao": "aprovado"}

    def publicar_auditoria(self, notas: list[Path], caminhos_painel: list[str]) -> dict:
        notas_rel = [Path(n).resolve().relative_to(self.cofre.resolve()).as_posix() for n in notas]
        caminhos_painel = list(dict.fromkeys(str(c).replace("\\", "/") for c in caminhos_painel))
        with TRAVA_PUBLICACAO:
            self._validar()
            cofre = None
            if notas_rel:
                cofre = self._commit_e_push(
                    self.cofre, notas_rel, "acervo: corrigir links canônicos de PDFs",
                )
            painel = self._commit_e_push(
                self.painel, caminhos_painel, "acervo: publicar correções da auditoria",
            )
        return {"cofre": cofre, "painel": painel, "testes": "aprovados", "guardiao": "aprovado"}
