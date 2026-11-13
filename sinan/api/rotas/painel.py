"""Telas de análise: visão geral, mapa e perfil dos casos."""

from __future__ import annotations

from fastapi import APIRouter

from ... import consultas as cq
from .. import cache, servicos
from ..filtros import Filtros
from ..respostas import json_resp, registros

router = APIRouter(tags=["Painel"])


@router.get("/visao", summary="Indicadores e curvas por semana, mês e ano")
def api_visao(ctx: Filtros):
    f = ctx.filtro

    def calcular():
        return {
            "indicadores": servicos.indicadores(f, ctx.area),
            "semana": registros(cq.por_semana(f)),
            "ano": registros(cq.por_ano(f)),
            "mes": registros(cq.por_mes(f)),
        }
    return json_resp(cache.memo(("visao", ctx), calcular))


@router.get("/mapa", summary="Casos e incidência por município")
def api_mapa(ctx: Filtros):
    def calcular():
        return {"indicadores": servicos.indicadores(ctx.filtro, ctx.area),
                "municipios": registros(servicos.tabela_municipios(ctx.filtro, ctx.area)),
                "area": list(ctx.area)}
    return json_resp(cache.memo(("mapa", ctx), calcular))


@router.get("/perfil", summary="Pirâmide etária, raça/cor, classificação, evolução...")
def api_perfil(ctx: Filtros):
    f = ctx.filtro

    def calcular():
        return {
            "indicadores": servicos.indicadores(f, ctx.area),
            "piramide": registros(cq.piramide(f)),
            "raca": servicos.contagem(f, "raca"),
            "situacao": servicos.contagem(f, "situacao", True),
            "classificacao": servicos.contagem(f, "classificacao", True),
            "evolucao": servicos.contagem(f, "evolucao_caso"),
            "criterio": servicos.contagem(f, "criterio_confirmacao"),
            "hospitalizado": servicos.contagem(f, "hospitalizado"),
        }
    return json_resp(cache.memo(("perfil", ctx), calcular))
