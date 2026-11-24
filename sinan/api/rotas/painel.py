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
        canal, motivo = (None, None) if ctx.restrito else servicos.canal_endemico(f, ctx.area)
        if ctx.restrito:
            ind, ano = servicos.sem_sensiveis(ind), ano.drop(columns="obitos")
        return {
            "indicadores": ind,
            # com município escolhido, a contagem semanal é pequena demais para o site publicado
            "semana": None if ctx.restrito else registros(cq.por_semana(servicos.filtro_da_serie(f, ctx.area))),
            "canal": canal,
            "canal_motivo": motivo,
            "contagens_ocultas": ctx.restrito,
            "ano": registros(ano),
            "mes": None if ctx.restrito else registros(cq.por_mes(f)),  # idem: contagem mensal pequena demais
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
        semana, alerta = servicos.alerta_municipios(ctx.filtro, ctx.area)
        alerta = alerta.drop(columns="q1").astype({"casos_semana": "Int64"})
        motivo_geral = None
        if semana is None:
            data = servicos.data_referencia(ctx.filtro.agravo)
            if data is None:
                motivo_geral = "sem_data"
            elif not ctx.filtro.ano_ini <= servicos.semana_referencia(data)["ano"] <= ctx.filtro.ano_fim:
                motivo_geral = "fora_do_periodo"
            else:
                motivo_geral = "sem_historico"
        if ctx.publico:  # D7: o nível e a faixa zero continuam; o número por município não
            alerta[["casos_semana", "esperado_ate"]] = None
        tabela = tabela.merge(alerta, on="cod6", how="left")
        return {"indicadores": ind, "municipios": registros(tabela), "area": list(ctx.area),
                "semana_alerta": semana, "contagem_alerta": "nao_descartadas", "contagens_ocultas": ctx.publico,
                "alerta_motivo_geral": motivo_geral}
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
