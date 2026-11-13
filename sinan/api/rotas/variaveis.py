"""Tela "Outras variáveis": qualquer campo da ficha, com os rótulos do TabNet."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from ... import consultas as cq
from ... import rotulos
from ...tabnet import ler_cnv
from .. import cache, servicos
from ..filtros import Filtros
from ..respostas import json_resp, registros

router = APIRouter(tags=["Variáveis da ficha"])


@router.get("/variaveis", summary="Lista de variáveis da ficha, com nome amigável e grupo")
def api_variaveis(agravo: str = "DENG"):
    agravo = cq.validar_agravo(agravo)
    return json_resp(cache.memo(("vars", agravo), lambda: servicos.lista_variaveis(agravo)))


@router.get("/variavel", summary="Distribuição dos casos em uma variável")
def api_variavel(ctx: Filtros, id: Annotated[int, Query(ge=0)] = 0):
    f = ctx.filtro
    vs = servicos.variaveis(f.agravo)
    if not vs:
        return json_resp({"rotulo": "", "valores": []})
    v = vs[min(id, len(vs) - 1)]

    def calcular():
        conv = ler_cnv(v.cnv)
        d = cq.contagem(f, v.campo)
        d["valor"] = conv.mapear(d["valor"].replace("", None), v.inicio)
        d = d.groupby("valor", as_index=False)["casos"].sum()
        ordem = {r: i for i, r in enumerate(conv.rotulos)}
        d["ordem"] = d["valor"].map(ordem).fillna(999)
        # "Não informado" vai para o fim da lista, depois das respostas de verdade
        d = servicos.simplificar(d, ordenar=False)
        d.loc[d["valor"] == rotulos.NAO_INFORMADO, "ordem"] = 1000
        return {"rotulo": rotulos.nome_amigavel(v.rotulo, v.campo, v.cnv), "rotulo_tabnet": v.rotulo,
                "campo": v.campo, "valores": registros(d.sort_values("ordem"))}
    return json_resp(cache.memo(("var", ctx, id), calcular))
