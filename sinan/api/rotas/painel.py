"""Telas de análise: visão geral, mapa e perfil dos casos."""

from __future__ import annotations

from fastapi import APIRouter

from ... import consultas as cq
from ... import processar
from .. import cache, servicos
from ..filtros import Filtros
from ..respostas import json_resp, registros

router = APIRouter(tags=["Painel"])


@router.get("/qualidade", summary="Prazos de notificação, digitação, investigação e encerramento")
def api_qualidade(ctx: Filtros):
    return json_resp(cache.memo(("qualidade", ctx), lambda: cq.qualidade(
        ctx.filtro, processar.data_dos_arquivos(ctx.filtro.agravo))))


@router.get("/visao", summary="Indicadores e curvas por semana, mês e ano")
def api_visao(ctx: Filtros):
    f = ctx.filtro

    def calcular():
        ind, ano = servicos.indicadores(f, ctx.area), cq.por_ano(f)
        if ctx.restrito:
            ind, ano = servicos.sem_sensiveis(ind), ano.drop(columns="obitos")
        return {
            "indicadores": ind,
            # com município escolhido, a contagem semanal é pequena demais para o site publicado
            "semana": None if ctx.restrito else registros(cq.por_semana(f)),
            "canal": None if ctx.restrito else servicos.canal_endemico(f, ctx.area),
            "contagens_ocultas": ctx.restrito,
            "ano": registros(ano),
            "mes": registros(cq.por_mes(f)),
        }
    return json_resp(cache.memo(("visao", ctx), calcular))


@router.get("/mapa", summary="Casos e incidência por município")
def api_mapa(ctx: Filtros):
    def calcular():
        ind, tabela = servicos.indicadores(ctx.filtro, ctx.area), servicos.tabela_municipios(ctx.filtro, ctx.area)
        if ctx.restrito:
            ind = servicos.sem_sensiveis(ind)
        if ctx.publico:  # óbitos por município, mesmo sem filtro, também é detalhe municipal
            tabela = tabela.drop(columns="obitos")
        return {"indicadores": ind, "municipios": registros(tabela), "area": list(ctx.area)}
    return json_resp(cache.memo(("mapa", ctx), calcular))


@router.get("/perfil", summary="Pirâmide etária, raça/cor, classificação, evolução...")
def api_perfil(ctx: Filtros):
    f = ctx.filtro

    def calcular():
        r = ctx.restrito
        ind = servicos.indicadores(f, ctx.area)
        return {
            "indicadores": servicos.sem_sensiveis(ind) if r else ind,
            "piramide": registros(cq.piramide(f)),
            "raca": servicos.contagem(f, "raca"),
            "situacao": servicos.contagem(f, "situacao", True),
            "classificacao": servicos.contagem(f, "classificacao", True),
            "evolucao": None if r else servicos.contagem(f, "evolucao_caso"),
            "criterio": servicos.contagem(f, "criterio_confirmacao"),
            "hospitalizado": None if r else servicos.contagem(f, "hospitalizado"),
        }
    return json_resp(cache.memo(("perfil", ctx), calcular))
