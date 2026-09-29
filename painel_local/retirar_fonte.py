"""Retirada recuperável de uma fonte: sai do Acervo, preserva rastreabilidade."""
from __future__ import annotations

import re
import threading
from pathlib import Path

from guardiao_acervo import ler_json_js
from sincronizar_acervo import sincronizar


TRAVA_RETIRADA = threading.Lock()


class ErroRetirada(ValueError):
    def __init__(self, mensagem: str, status: int = 400):
        super().__init__(mensagem)
        self.status = status


class RetiradorFonte:
    def __init__(self, cofre: Path, painel: Path, sincronizar_fn=sincronizar):
        self.cofre = Path(cofre)
        self.painel = Path(painel)
        self.sincronizar = sincronizar_fn

    def _item(self, codigo: str) -> dict:
        inventario = ler_json_js(self.painel / "dados_inventario.js", "DADOS_INVENTARIO")
        item = next((i for i in inventario if str(i.get("codigo")) == codigo), None)
        if not item:
            raise ErroRetirada(f"O código {codigo} não pertence ao acervo publicado.", 404)
        return item

    def _nota(self, codigo: str) -> Path:
        encontrados = []
        for nota in (self.cofre / "Fontes").glob("*.md"):
            texto = nota.read_text(encoding="utf-8", errors="replace")
            if re.search(rf'^codigo:\s*["\']?{re.escape(codigo)}["\']?\s*$', texto, re.M | re.I):
                encontrados.append(nota)
        if len(encontrados) != 1:
            raise ErroRetirada(
                f"Esperada uma nota canônica para {codigo}; encontradas {len(encontrados)}.", 409
            )
        return encontrados[0]

    @staticmethod
    def _marcar_retirada(texto: str, antigo: str, novo: str) -> str:
        if re.search(r"(?m)^status:", texto):
            texto = re.sub(
                r'(?m)^status:\s*.*$', 'status: "retirado do acervo"', texto, count=1
            )
        else:
            texto = texto.replace("---\n", '---\nstatus: "retirado do acervo"\n', 1)
        linha = f"- **PDF arquivado:** [[{novo}]]"
        texto, trocas = re.subn(
            r"(?im)^\s*(?:[-*]\s+)?\*\*PDF(?::| arquivado:)\*\*.*$", linha, texto, count=1
        )
        if not trocas:
            texto += f"\n\n## Arquivo retirado\n{linha}\n"
        registro = (
            "\n\n> [!warning] Retirado do Acervo\n"
            f"> O PDF deixou a pasta oficial `PDF/`. Caminho anterior: `{antigo}`. "
            "A nota e eventual fichamento foram preservados somente para rastreabilidade.\n"
        )
        if "[!warning] Retirado do Acervo" not in texto:
            texto += registro
        return texto

    def retirar(self, codigo: str, confirmacao: str) -> dict:
        codigo = str(codigo or "").strip().upper().removeprefix("#")
        if not codigo or str(confirmacao or "").strip().upper().removeprefix("#") != codigo:
            raise ErroRetirada("Confirmação inválida. Digite exatamente o código da fonte.")

        with TRAVA_RETIRADA:
            item = self._item(codigo)
            nota = self._nota(codigo)
            antigo_rel = str(item.get("arquivo", "")).replace("\\", "/")
            antigo = (self.cofre / antigo_rel).resolve()
            raiz = self.cofre.resolve()
            if not antigo.is_relative_to(raiz) or not antigo_rel.startswith("PDF/") or not antigo.is_file():
                raise ErroRetirada("O PDF ativo não foi localizado dentro da pasta oficial PDF/.", 409)

            destino_dir = self.cofre / "PDF_Para conhecimento" / "_Retirados_do_acervo"
            destino_dir.mkdir(parents=True, exist_ok=True)
            destino = destino_dir / f"{codigo} - {antigo.name}"
            if destino.exists():
                raise ErroRetirada("Já existe um PDF arquivado com esse código; nada foi alterado.", 409)
            novo_rel = destino.relative_to(self.cofre).as_posix()
            texto_original = nota.read_text(encoding="utf-8")
            texto_novo = self._marcar_retirada(texto_original, antigo_rel, novo_rel)

            antigo.replace(destino)
            try:
                nota.write_text(texto_novo, encoding="utf-8")
                if self.sincronizar(self.cofre, self.painel, True) != 0:
                    raise ErroRetirada("O Guardião recusou a retirada; o acervo foi restaurado.", 422)
                inventario = ler_json_js(self.painel / "dados_inventario.js", "DADOS_INVENTARIO")
                if any(str(i.get("codigo")) == codigo for i in inventario):
                    raise ErroRetirada("O código continuou publicado; o acervo foi restaurado.", 422)
            except Exception:
                nota.write_text(texto_original, encoding="utf-8")
                if destino.exists() and not antigo.exists():
                    destino.replace(antigo)
                self.sincronizar(self.cofre, self.painel, True)
                raise

        return {
            "codigo": codigo,
            "nota": nota,
            "pdf_anterior": antigo_rel,
            "pdf_arquivado": novo_rel,
        }
