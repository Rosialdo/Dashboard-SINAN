"""Tela "Atualizar dados": o que está no computador, o que existe no DATASUS, baixar e remover."""

from __future__ import annotations

import re

from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

from ... import agravos as cat
from ... import config
from ... import consultas as cq
from ...download import listagem_salva, listar_ftp
from ...processar import ler_inventario, remover
from .. import cache, tarefa
from ..filtros import UF_NOME
from ..respostas import erro, json_resp

router = APIRouter(prefix="/dados", tags=["Atualizar dados"])

UFS_VALIDAS = set(config.UFS.values()) | {"BR"}
_CHAVE_ITEM = re.compile(r"[A-Z0-9]{2,8}_\d{4}")


class PedidoAtualizar(BaseModel):
    agravos: list[str] = Field(default_factory=list, description="Códigos dos agravos, ex.: DENG")
    anos: list[int] = Field(default_factory=list, description="Anos, ex.: 2024")
    ufs: list[str] = Field(default_factory=list, description='Siglas das UFs ou "BR"')
    forcar: bool = False

    @field_validator("agravos")
    @classmethod
    def _agravos(cls, v: list[str]) -> list[str]:
        return [cq.validar_agravo(a) for a in v]

    @field_validator("ufs")
    @classmethod
    def _ufs(cls, v: list[str]) -> list[str]:
        v = [u.upper() for u in v]
        invalidas = [u for u in v if u not in UFS_VALIDAS]
        if invalidas:
            raise ValueError(f"UF desconhecida: {', '.join(invalidas)}")
        return v

    @field_validator("anos")
    @classmethod
    def _anos(cls, v: list[int]) -> list[int]:
        if any(not 1990 <= a <= 2100 for a in v):
            raise ValueError("ano fora do esperado")
        return sorted(set(v))


class PedidoRemover(BaseModel):
    itens: list[str] = Field(default_factory=list, description='Chaves "AGRAVO_ANO", ex.: DENG_2024')

    @field_validator("itens")
    @classmethod
    def _itens(cls, v: list[str]) -> list[str]:
        for chave in v:
            if not _CHAVE_ITEM.fullmatch(chave):
                raise ValueError(f"item inválido: {chave!r}")
        return v


def _situacao_dados() -> dict:
    cfg = config.carregar_config()
    listagem = listagem_salva()
    arquivos = (listagem or {}).get("arquivos", {})
    inv = ler_inventario()
    itens = []
    for v in sorted(inv.values(), key=lambda x: (cat.nome(x["agravo"]), x["ano"])):
        info = arquivos.get(v["agravo"], {}).get(str(v["ano"]))
        if not info:
            status = "desconhecido"
        elif info.get("data_ftp") != v.get("data_ftp") or info.get("situacao") != v.get("situacao"):
            status = "nova"
        else:
            status = "em_dia"
        itens.append({**v, "nome": cat.nome(v["agravo"]), "status": status})
    catalogo = sorted(set(cat.AGRAVOS) | set(arquivos), key=cat.nome)
    return {
        "config": cfg,
        "listagem_em": (listagem or {}).get("atualizado_em"),
        "catalogo": [{"codigo": c, "nome": cat.nome(c),
                      "anos": sorted((int(a) for a in arquivos.get(c, {})), reverse=True),
                      "tamanhos": {a: i.get("tamanho", 0) for a, i in arquivos.get(c, {}).items()}}
                     for c in catalogo],
        "ufs": sorted(config.UFS.values()),
        "ufs_nome": UF_NOME,
        "inventario": itens,
        "job": tarefa.estado(),
    }


@router.get("", summary="Dados no computador e catálogo do DATASUS")
def api_dados():
    return json_resp(_situacao_dados())


@router.post("/listar", summary="Consulta o FTP do DATASUS (precisa de internet)")
def api_listar_ftp():
    try:
        listar_ftp()
    except Exception as e:
        return erro(f"Sem conexão com o DATASUS: {e}", 502)
    return json_resp(_situacao_dados())


@router.post("/atualizar", summary="Baixa e processa em segundo plano")
def api_atualizar(pedido: PedidoAtualizar):
    if not (pedido.agravos and pedido.anos and pedido.ufs):
        return erro("Escolha UF, agravo e ano.")
    if not tarefa.iniciar(pedido.agravos, pedido.anos, pedido.ufs, pedido.forcar):
        return erro("Já existe uma atualização em andamento.", 409)
    return json_resp(tarefa.estado())


@router.get("/status", summary="Andamento da atualização")
def api_status():
    return json_resp(tarefa.estado())


@router.post("/remover", summary="Apaga do computador os anos escolhidos")
def api_remover(pedido: PedidoRemover):
    for chave in pedido.itens:
        agravo, ano = chave.rsplit("_", 1)
        remover(agravo, int(ano))
    cache.limpar()
    return json_resp(_situacao_dados())
