"""Modelos Pydantic para metadados de documentos e economia de tokens."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SecaoDocumento(BaseModel):
    """Metadados de uma página ou seção de documento."""

    pagina: int = Field(ge=1, description="Número da página (iniciando em 1)")
    titulo_provavel: str = Field(description="Primeira linha significativa ou título do trecho")
    amostra_inicio: str = Field(description="Amostra inicial (primeiros 150 caracteres) para contexto rápido")
    total_caracteres: int = Field(ge=0, description="Contagem de caracteres na página")
    tokens_estimados: int = Field(ge=0, description="Estimativa de tokens (aprox. 4 caracteres por token)")


class MetadadosDocumento(BaseModel):
    """Metadados completos de um documento sem carregar todo o seu texto na LLM."""

    arquivo: str = Field(description="Nome do arquivo")
    caminho_relativo: str = Field(description="Caminho relativo do arquivo")
    total_paginas: int = Field(ge=0, description="Total de páginas")
    tamanho_bytes: int = Field(ge=0, description="Tamanho em bytes do arquivo no disco")
    tokens_estimados_total: int = Field(ge=0, description="Tokens se o documento inteiro fosse enviado para a LLM")
    secoes: list[SecaoDocumento] = Field(default_factory=list, description="Lista de seções/páginas resumidas")


class TrechoDocumento(BaseModel):
    """Conteúdo detalhado de uma única página/seção solicitada sob demanda."""

    arquivo: str
    pagina: int
    conteudo: str
    tokens_estimados: int


class RelatorioEconomiaTokens(BaseModel):
    """Demonstrativo matemático da economia de tokens obtida."""

    documento: str
    tokens_documento_inteiro: int
    tokens_apenas_metadados: int
    tokens_trecho_consultado: int
    tokens_totais_consumidos: int
    tokens_economizados: int
    percentual_economia: float


class ParagrafoCirurgico(BaseModel):
    """Parágrafo exato extraído de um documento com indicação de página."""

    arquivo: str
    pagina: int
    texto: str
    relevancia_score: float = 0.0
    tokens_estimados: int


class ResultadoBuscaCirurgica(BaseModel):
    """Resultado da busca cirúrgica contendo apenas os parágrafos essenciais."""

    arquivo: str
    consulta: str
    trechos: list[ParagrafoCirurgico]
    tokens_totais_trechos: int
    tokens_documento_inteiro: int
    percentual_economia: float

