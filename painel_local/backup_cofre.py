"""
Backup do cofre no GitHub (repositório PRIVADO rcminitor/sindrome-de-pandora)
============================================================================

O painel faz sozinho, uma vez por dia (e ao ligar, se o último backup tiver mais de
24 h): git add → commit → junta com o que houver no GitHub → push. Nunca força
nada: se o GitHub e o seu PC mudaram o mesmo arquivo de jeitos diferentes, desfaz
a junção, NÃO envia e avisa (painel e resumo semanal) para você decidir.

Fica de fora do backup (bloco "painel" do .gitignore do cofre):
  • Leitura\\_copias_antes_do_painel\\ e _copias_antes_do_backup\\ (cópias de segurança locais)
  • PDFs dentro de Leitura\\ (cópias de trabalho e artigos citados baixados — os
    originais continuam em PDF\\, que já vai para o GitHub; os citados se baixam de novo)
  • arquivos temporários do painel e qualquer arquivo acima de 95 MB (limite do GitHub)

Primeira vez, se a pasta do cofre ainda não for um repositório git:
    python painel_local\\backup_cofre.py --ligar
  liga a pasta ao repositório do GitHub SEM apagar nada: arquivos só do GitHub
  descem; arquivos que existem nos dois com conteúdo diferente ficam com a versão
  do GitHub e a sua é guardada em Leitura\\_copias_antes_do_backup\\<data>\\ (a lista
  sai na tela); arquivos só do seu PC entram no primeiro backup.

Rodar um backup agora:  python painel_local\\backup_cofre.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

REMOTO = "https://github.com/rcminitor/sindrome-de-pandora.git"
LIMITE_MB = 95
INI, FIM = "# >>> painel (backup_cofre.py) — não edite dentro deste bloco", "# <<< painel"
IGNORAR = [
    "Leitura/_copias_antes_do_painel/",
    "Leitura/_copias_antes_do_backup/",
    "Leitura/**/*.pdf",
    "Leitura/*.pdf",
    "*.painel.tmp",
    "Leitura/*.tmp",
    "Leitura/backup_status.json",
]


class Backup:
    def __init__(self, cofre: Path, biblioteca: Path | None = None):
        self.cofre = cofre
        self.biblioteca = biblioteca or cofre / "Leitura"
        self.arq_status = self.biblioteca / "backup_status.json"

    # ------------------------------------------------------------ util
    def _git(self, *args: str, checar: bool = False) -> subprocess.CompletedProcess:
        r = subprocess.run(["git", "-C", str(self.cofre), "-c", "core.quotepath=off", *args],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if checar and r.returncode != 0:
            raise RuntimeError(f"git {' '.join(args[:2])}: {(r.stderr or r.stdout).strip()[:300]}")
        return r

    @property
    def ligado(self) -> bool:
        return (self.cofre / ".git").exists()

    def status(self) -> dict:
        try:
            return json.loads(self.arq_status.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _gravar_status(self, **d) -> dict:
        st = {"quando": datetime.now().isoformat(timespec="minutes"), **d}
        self.arq_status.parent.mkdir(parents=True, exist_ok=True)
        self.arq_status.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
        return st

    def precisa(self, horas: int = 24) -> bool:
        st = self.status()
        try:
            idade = datetime.now() - datetime.fromisoformat(st["quando"])
            return idade > timedelta(hours=horas if st.get("ok") else 3)       # com erro, tenta de novo a cada 3 h
        except Exception:
            return True

    def _gitignore(self) -> None:
        arq = self.cofre / ".gitignore"
        texto = arq.read_text(encoding="utf-8") if arq.exists() else ""
        bloco = "\n".join([INI, *IGNORAR, FIM])
        if INI in texto:
            antes, resto = texto.split(INI, 1)
            depois = resto.split(FIM, 1)[1] if FIM in resto else ""
            novo = antes + bloco + depois
        else:
            novo = texto.rstrip() + ("\n\n" if texto.strip() else "") + bloco + "\n"
        if novo != texto:
            arq.write_text(novo, encoding="utf-8")
        self._git("rm", "--cached", "-q", "--ignore-unmatch", "--", "Leitura/backup_status.json")

    def _grandes_fora(self) -> list[str]:
        """Arquivos novos/alterados acima do limite do GitHub vão para .git/info/exclude."""
        r = self._git("status", "--porcelain", "-z", "--untracked-files=all")
        grandes = []
        for item in r.stdout.split("\0"):
            if len(item) < 4:
                continue
            rel = item[3:]
            p = self.cofre / rel
            if p.is_file() and p.stat().st_size > LIMITE_MB * 1024 * 1024:
                grandes.append(rel)
        if grandes:
            exc = self.cofre / ".git" / "info" / "exclude"
            exc.parent.mkdir(parents=True, exist_ok=True)
            atual = exc.read_text(encoding="utf-8") if exc.exists() else ""
            novos = [g for g in grandes if g not in atual.split("\n")]
            if novos:
                exc.write_text(atual.rstrip() + "\n" + "\n".join(novos) + "\n", encoding="utf-8")
            for g in grandes:
                self._git("rm", "--cached", "--quiet", "--ignore-unmatch", "--", g)
        return grandes

    # ------------------------------------------------------------ backup
    def fazer(self, motivo: str = "diário") -> dict:
        if not self.ligado:
            return self._gravar_status(ok=False, ligado=False,
                                       erro="O cofre ainda não é um repositório git. Rode uma vez: "
                                            "python painel_local\\backup_cofre.py --ligar")
        try:
            self._gitignore()
            grandes = self._grandes_fora()
            self._git("add", "-A", checar=True)
            mudados = [l for l in self._git("diff", "--cached", "--name-only").stdout.splitlines() if l]
            commit = None
            if mudados:
                msg = f"Backup automático do cofre — {datetime.now():%d/%m/%Y %H:%M} ({len(mudados)} arquivo(s), {motivo})"
                self._git("commit", "-q", "-m", msg, checar=True)
                commit = self._git("rev-parse", "--short", "HEAD").stdout.strip()
            ramo = self._git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "main"
            self._git("fetch", "-q", "origin", ramo, checar=True)
            atras = int(self._git("rev-list", "--count", f"HEAD..origin/{ramo}").stdout.strip() or 0)
            if atras:                                                 # o GitHub tem coisas novas (ex.: PRs)
                m = self._git("merge", "--no-edit", "-q", f"origin/{ramo}")
                if m.returncode != 0:
                    conflitos = self._git("diff", "--name-only", "--diff-filter=U").stdout.splitlines()
                    self._git("merge", "--abort")
                    return self._gravar_status(ok=False, ligado=True, commit=commit, arquivos=len(mudados),
                                               conflitos=conflitos[:30],
                                               erro=f"{len(conflitos)} arquivo(s) mudaram no GitHub e no seu PC de jeitos "
                                                    "diferentes. Nada foi enviado nem perdido; resolva no GitHub Desktop "
                                                    "ou peça ajuda ao Claude.")
            frente = int(self._git("rev-list", "--count", f"origin/{ramo}..HEAD").stdout.strip() or 0)
            if frente:
                self._git("push", "-q", "origin", f"HEAD:{ramo}", checar=True)
            return self._gravar_status(ok=True, ligado=True, commit=commit, arquivos=len(mudados),
                                       recebidos=atras, enviados=frente, grandes_fora=grandes, erro="")
        except Exception as e:
            return self._gravar_status(ok=False, ligado=True, erro=f"{type(e).__name__}: {e}")

    # ------------------------------------------------------------ primeira vez
    def ligar(self) -> None:
        if self.ligado:
            print("O cofre já é um repositório git. Nada a fazer — o backup diário já funciona.")
            return
        print(f"Ligando {self.cofre} a {REMOTO} (nada será apagado)…")
        self._git("init", "-q", checar=True)
        self._git("remote", "add", "origin", REMOTO, checar=True)
        self._git("fetch", "-q", "origin", "main", checar=True)
        self._git("reset", "-q", "--mixed", "origin/main", checar=True)      # arquivos do PC não mudam
        self._git("branch", "-q", "-M", "main")
        self._git("branch", "-q", "--set-upstream-to=origin/main", "main")
        self._gitignore()
        st = self._git("status", "--porcelain", "-z").stdout.split("\0")
        faltando = [s[3:] for s in st if s.startswith(" D ")]                 # só no GitHub: descem
        diferentes = [s[3:] for s in st if s.startswith(" M ")]               # nos dois, diferentes
        copia = self.biblioteca / "_copias_antes_do_backup" / datetime.now().strftime("%Y-%m-%d")
        for rel in diferentes:
            destino = copia / rel
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.cofre / rel, destino)
        if faltando or diferentes:
            self._git("checkout", "-q", "origin/main", "--", *(faltando + diferentes), checar=True)
        print(f"  {len(faltando)} arquivo(s) que só estavam no GitHub foram baixados.")
        if diferentes:
            print(f"  {len(diferentes)} arquivo(s) existiam nos dois com conteúdo diferente: ficou a versão do GitHub;")
            print(f"  a sua está guardada em {copia}:")
            for rel in diferentes[:40]:
                print("   -", rel)
        print("Primeiro backup (arquivos que só estavam no seu PC)…")
        r = self.fazer("primeira ligação")
        print("  ✓ pronto" if r.get("ok") else f"  ✗ {r.get('erro')}")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agentes_crewai"))
    padrao = Path(r"C:\Users\rcmin\OneDrive\Documents\Pos-Graduacao\Doutorado UFC\Síndrome de Pandora")
    try:
        import contexto_cofre
        raiz = contexto_cofre.raiz() or padrao
    except Exception:
        raiz = padrao
    b = Backup(raiz)
    if "--ligar" in sys.argv:
        b.ligar()
    else:
        r = b.fazer("manual")
        print(json.dumps(r, ensure_ascii=False, indent=1))
