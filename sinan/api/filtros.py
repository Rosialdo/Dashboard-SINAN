"""Filtros do painel: lê os parâmetros da URL e monta o ``consultas.Filtro``.

As rotas recebem o resultado como dependência do FastAPI:

    def api_visao(ctx: Filtros): ...
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Depends

from .. import agravos as cat
from .. import config
from .. import consultas as cq
from . import cache
from .respostas import ErroUsuario

ARBOVIROSES = {"DENG", "CHIK", "ZIKA"}  # as únicas com contagem de "casos prováveis"

UF_NOME = {"AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá", "BA": "Bahia", "CE": "Ceará",
           "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
           "MG": "Minas Gerais", "MS": "Mato Grosso do Sul", "MT": "Mato Grosso", "PA": "Pará",
           "PB": "Paraíba", "PE": "Pernambuco", "PI": "Piauí", "PR": "Paraná", "RJ": "Rio de Janeiro",
           "RN": "Rio Grande do Norte", "RO": "Rondônia", "RR": "Roraima", "RS": "Rio Grande do Sul",
           "SC": "Santa Catarina", "SE": "Sergipe", "SP": "São Paulo", "TO": "Tocantins"}


@dataclass(frozen=True)
class Contexto:
    """Filtro da consulta + área usada no cálculo da população (UFs)."""
    filtro: cq.Filtro
    area: tuple[str, ...]


def lista(valor: str | None) -> tuple[str, ...]:
    """"RR,AM" -> ("RR", "AM")."""
    return tuple(x for x in (valor or "").split(",") if x)


def area_base() -> list[str]:
    """UFs escolhidas na tela "Baixar dados" (sem o "BR")."""
    return [u for u in config.carregar_config()["ufs"] if u in config.UFS.values()]


def anos(agravo: str) -> list[int]:
    return cache.memo(("anos", agravo), lambda: cq.anos(agravo))


def ufs_presentes(agravo: str) -> list[str]:
    return cache.memo(("ufs", agravo), lambda: cq.ufs_presentes(agravo))


def contexto(
    agravo: str = "DENG",
    ini: int | None = None,
    fim: int | None = None,
    contagem: Literal["confirmados", "provaveis", "todas"] = "confirmados",
    local: Literal["res", "not"] = "res",
    ufs: str = "",
    mun: str = "",
    sexo: str = "",
    faixa: str = "",
) -> Contexto:
    """Dependência do FastAPI com os filtros comuns a todas as telas do painel."""
    agravo = cq.validar_agravo(agravo)
    disponiveis = anos(agravo)
    if not disponiveis:
        raise ErroUsuario(f"Não há dados de {cat.nome(agravo)} no computador.")
    ini = disponiveis[0] if ini is None else ini
    fim = disponiveis[-1] if fim is None else fim
    if cat.obter(agravo).todos_casos:
        contagem = "todas"  # agravos sem confirmação: toda notificação é um caso
    elif contagem == "provaveis" and agravo not in ARBOVIROSES:
        contagem = "confirmados"
    f = cq.Filtro(agravo, min(ini, fim), max(ini, fim), local != "not",
                  lista(ufs), lista(mun), contagem, lista(sexo), lista(faixa))
    area = list(f.ufs) or area_base() or ufs_presentes(agravo)[:1]
    return Contexto(f, tuple(area))


# atalho para as rotas: ``def api_visao(ctx: Filtros)``
Filtros = Annotated[Contexto, Depends(contexto)]
