"""Informações gerais para montar a interface: agravos, anos, UFs, municípios e mapa."""

from __future__ import annotations

import json

from fastapi import APIRouter

from ... import agravos as cat
from ... import config
from ... import consultas as cq
from ...processar import FAIXAS, ler_inventario
from ..filtros import ARBOVIROSES, UF_NOME, anos, area_base, lista, ufs_presentes
from ..respostas import json_resp, registros

router = APIRouter(tags=["Geral"])


@router.get("/meta", summary="Agravos, anos, UFs e municípios disponíveis no computador")
def api_meta():
    cfg = config.carregar_config()
    inv = ler_inventario()
    agravos = []
    for cod in cq.agravos_disponiveis():
        ag = cat.obter(cod)
        anos_ag = sorted(int(v["ano"]) for v in inv.values() if v["agravo"] == cod) or anos(cod)
        prelim = sorted(int(v["ano"]) for v in inv.values() if v["agravo"] == cod and v.get("situacao") == "preliminar")
        agravos.append({"codigo": cod, "nome": ag.nome, "todos_casos": ag.todos_casos,
                        "provaveis": cod in ARBOVIROSES, "aviso": ag.aviso,
                        "aviso_so_amazonia": cod == "MALA", "anos": anos_ag, "preliminares": prelim})
    if "BR" in cfg["ufs"]:
        ufs_disp = sorted({u for a in agravos for u in ufs_presentes(a["codigo"])})
    else:
        ufs_disp = area_base()
    mun = cq.municipios_da_uf(ufs_disp)
    atualizado = max((v.get("processado_em", "") for v in inv.values()), default="")
    return json_resp({
        "agravos": agravos,
        "ufs": ufs_disp,
        "ufs_nome": {u: UF_NOME.get(u, u) for u in ufs_disp},
        "brasil": "BR" in cfg["ufs"],
        "municipios": registros(mun),
        "faixas": FAIXAS,
        "amazonia_legal": sorted(config.AMAZONIA_LEGAL),
        "atualizado_em": atualizado,
    })


_geo: dict = {}


@router.get("/geo", summary="Contorno dos municípios das UFs (GeoJSON)")
def api_geo(ufs: str = ""):
    chave = tuple(sorted(lista(ufs)))
    if chave not in _geo:
        if "geo" not in _geo:
            _geo["geo"] = json.loads(config.ARQ_MAPA.read_text(encoding="utf-8"))
        codigos = {cod for cod, sigla in config.UFS.items() if sigla in chave}
        feats = [f for f in _geo["geo"]["features"] if f["properties"]["cod6"][:2] in codigos]
        _geo[chave] = {"type": "FeatureCollection", "features": feats}
    return json_resp(_geo[chave])
