"""Tela "Dados e exportação": tabela paginada e download em Excel/CSV."""

from __future__ import annotations

import io
from typing import Annotated, Literal

import pandas as pd
from fastapi import APIRouter, Query

from ... import consultas as cq
from .. import cache, servicos
from ..filtros import Filtros
from ..respostas import anexo, json_resp, registros

router = APIRouter(tags=["Dados e exportação"])

POR_PAGINA = 50
LIMITE_EXCEL = 1_000_000  # o Excel aceita no máximo 1.048.576 linhas por planilha
CSV = "text/csv"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _csv(df: pd.DataFrame) -> bytes:
    # ";" e "," decimal: abre direto no Excel em português; BOM para os acentos
    return df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


@router.get("/registros", summary="Registros (fichas) filtrados, 50 por página")
def api_registros(ctx: Filtros, pagina: Annotated[int, Query(ge=0)] = 0):
    f = ctx.filtro
    # paginação feita no próprio DuckDB: só 50 linhas saem do disco por vez
    total = cache.memo(("total_regs", f), lambda: cq.total_registros(f))
    trecho = cq.registros(f, limite=POR_PAGINA, inicio=pagina * POR_PAGINA)
    trecho = servicos.trocar_codigos_municipio(servicos.textos_simples(trecho))
    return json_resp({"total": total, "pagina": pagina, "por_pagina": POR_PAGINA, "linhas": registros(trecho)})


@router.get("/exportar", summary="Baixa os dados filtrados (Excel ou CSV)")
def api_exportar(ctx: Filtros,
                 formato: Literal["xlsx", "csv", "csv_completo", "municipios"] = "xlsx"):
    f, area = ctx.filtro, ctx.area
    nome = f"sinan_{f.agravo}_{f.ano_ini}-{f.ano_fim}"

    if formato == "municipios":
        t = servicos.tabela_municipios(f, area)[["municipio", "uf", "casos", "incidencia", "obitos", "populacao"]]
        t.columns = ["Município", "UF", "Casos", "Incidência por 100 mil hab./ano", "Óbitos", "População média"]
        return anexo(_csv(t), f"{nome}_municipios.csv", CSV)

    completo = formato == "csv_completo"
    df = cq.registros(f, limite=LIMITE_EXCEL if formato == "xlsx" else None, todas_colunas=completo)
    df = servicos.trocar_codigos_municipio(servicos.textos_simples(df))

    if formato == "xlsx":
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="registros")
            servicos.tabela_municipios(f, area).to_excel(w, index=False, sheet_name="por_municipio")
            cq.por_semana(f).to_excel(w, index=False, sheet_name="por_semana")
            cq.por_ano(f).to_excel(w, index=False, sheet_name="por_ano")
        return anexo(buf.getvalue(), f"{nome}.xlsx", XLSX)

    sufixo = "_completo" if completo else ""
    return anexo(_csv(df), f"{nome}{sufixo}.csv", CSV)
