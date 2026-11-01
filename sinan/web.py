"""Servidor local do dashboard: entrega a interface (pasta web/) e uma API JSON.

Tudo roda no próprio computador (localhost); só a atualização de dados usa a internet.
"""

from __future__ import annotations

import io
import json
import threading
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import agravos as cat
from . import consultas as cq
from .config import (AMAZONIA_LEGAL, ARQ_INVENTARIO, ARQ_MAPA, RAIZ, UFS, carregar_config,
                     salvar_config)
from .download import listagem_salva, listar_ftp
from .pipeline import atualizar
from .processar import FAIXAS, ler_inventario, remover
from .tabnet import ler_cnv, ler_def

PASTA_WEB = RAIZ / "web"
PLOTLY_JS = Path(plotly.__file__).parent / "package_data" / "plotly.min.js"
ARBOVIROSES = {"DENG", "CHIK", "ZIKA"}
UF_NOME = {"AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá", "BA": "Bahia", "CE": "Ceará",
           "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
           "MG": "Minas Gerais", "MS": "Mato Grosso do Sul", "MT": "Mato Grosso", "PA": "Pará",
           "PB": "Paraíba", "PE": "Pernambuco", "PI": "Piauí", "PR": "Paraná", "RJ": "Rio de Janeiro",
           "RN": "Rio Grande do Norte", "RO": "Rondônia", "RR": "Roraima", "RS": "Rio Grande do Sul",
           "SC": "Santa Catarina", "SE": "Sergipe", "SP": "São Paulo", "TO": "Tocantins"}


# ------------------------------------------------------------------ utilidades
def _json(dados, status: int = 200) -> Response:
    texto = json.dumps(dados, ensure_ascii=False, default=_conv)
    return Response(texto, status_code=status, media_type="application/json")


def _conv(v):
    if isinstance(v, (pd.Timestamp, datetime)):
        return v.strftime("%Y-%m-%d")
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if hasattr(v, "item"):
        return v.item()
    if pd.isna(v):
        return None
    return str(v)


def _registros(df: pd.DataFrame) -> list[dict]:
    df = df.astype(object).where(df.notna(), None)
    return df.to_dict(orient="records")


def _lista(valor: str | None) -> tuple[str, ...]:
    return tuple(x for x in (valor or "").split(",") if x)


def _area_base() -> list[str]:
    ufs = [u for u in carregar_config()["ufs"] if u in UFS.values()]
    return ufs


def _filtro(req: Request) -> tuple[cq.Filtro, list[str]]:
    q = req.query_params
    agravo = q.get("agravo", "DENG").upper()
    anos = cq.anos(agravo)
    ini = int(q.get("ini") or anos[0])
    fim = int(q.get("fim") or anos[-1])
    ag = cat.obter(agravo)
    contagem = "todas" if ag.todos_casos else q.get("contagem", "confirmados")
    if contagem == "provaveis" and agravo not in ARBOVIROSES:
        contagem = "confirmados"
    f = cq.Filtro(agravo, min(ini, fim), max(ini, fim), q.get("local", "res") != "not",
                  _lista(q.get("ufs")), _lista(q.get("mun")), contagem,
                  _lista(q.get("sexo")), _lista(q.get("faixa")))
    area = list(f.ufs) or _area_base() or cq.ufs_presentes(agravo)[:1]
    return f, area


def _versao() -> float:
    try:
        return ARQ_INVENTARIO.stat().st_mtime
    except OSError:
        return 0.0


_cache: dict = {}


def _memo(chave, func):
    """Cache simples, invalidado quando os dados mudam."""
    k = (chave, _versao())
    if k not in _cache:
        if len(_cache) > 400:
            _cache.clear()
        _cache[k] = func()
    return _cache[k]


# ------------------------------------------------------------------ meta
async def api_meta(req: Request) -> Response:
    cfg = carregar_config()
    inv = ler_inventario()
    agravos = []
    for cod in cq.agravos_disponiveis():
        ag = cat.obter(cod)
        anos = sorted(int(v["ano"]) for v in inv.values() if v["agravo"] == cod) or cq.anos(cod)
        prelim = sorted(int(v["ano"]) for v in inv.values() if v["agravo"] == cod and v.get("situacao") == "preliminar")
        agravos.append({"codigo": cod, "nome": ag.nome, "todos_casos": ag.todos_casos,
                        "provaveis": cod in ARBOVIROSES, "aviso": ag.aviso,
                        "aviso_so_amazonia": cod == "MALA", "anos": anos, "preliminares": prelim})
    ufs = _area_base()
    if "BR" in cfg["ufs"]:
        ufs_disp = sorted({u for a in agravos for u in cq.ufs_presentes(a["codigo"])})
    else:
        ufs_disp = ufs
    mun = cq.municipios_da_uf(ufs_disp) if ufs_disp else cq.municipios_da_uf([])
    atualizado = max((v.get("processado_em", "") for v in inv.values()), default="")
    return _json({
        "agravos": agravos,
        "ufs": ufs_disp,
        "ufs_nome": {u: UF_NOME.get(u, u) for u in ufs_disp},
        "brasil": "BR" in cfg["ufs"],
        "municipios": _registros(mun),
        "faixas": FAIXAS,
        "amazonia_legal": sorted(AMAZONIA_LEGAL),
        "atualizado_em": atualizado,
    })


# ------------------------------------------------------------------ painel
def _indicadores(f: cq.Filtro, area: list[str]) -> dict:
    ind = cq.indicadores(f)
    pop = 0.0 if (f.sexo or f.faixas) else cq.populacao(f, area)
    casos = ind["notificacoes"] if f.contagem == "todas" else ind[f.contagem]
    ind["casos"] = casos
    ind["incidencia"] = casos * 1e5 / pop if pop else None
    ind["letalidade"] = 100 * ind["obitos"] / ind["confirmados"] if ind["confirmados"] else None
    ind["n_anos"] = f.ano_fim - f.ano_ini + 1
    return ind


async def api_visao(req: Request) -> Response:
    f, area = _filtro(req)

    def calc():
        return {
            "indicadores": _indicadores(f, area),
            "semana": _registros(cq.por_semana(f)),
            "ano": _registros(cq.por_ano(f)),
            "mes": _registros(cq.por_mes(f)),
        }
    return _json(_memo(("visao", f, tuple(area)), calc))


def _tabela_municipios(f: cq.Filtro, area: list[str]) -> pd.DataFrame:
    dados = cq.por_municipio(f)
    base = cq.municipios_da_uf(area)
    if f.municipios:
        base = base[base["cod6"].isin(f.municipios)]
    t = base.merge(dados.drop(columns=["municipio", "uf", "populacao", "incidencia"]), on="cod6", how="left")
    t[["casos", "obitos"]] = t[["casos", "obitos"]].fillna(0).astype(int)
    pop = cq._q("SELECT cod6, avg(populacao) populacao, sum(populacao) pa FROM pop "
                "WHERE ano BETWEEN ? AND ? GROUP BY 1", [f.ano_ini, f.ano_fim])
    t = t.merge(pop, on="cod6", how="left")
    t["incidencia"] = t["casos"] * 1e5 / t["pa"]
    return t.drop(columns="pa").sort_values(["casos", "incidencia"], ascending=False)


async def api_mapa(req: Request) -> Response:
    f, area = _filtro(req)

    def calc():
        return {"indicadores": _indicadores(f, area),
                "municipios": _registros(_tabela_municipios(f, area)),
                "area": area}
    return _json(_memo(("mapa", f, tuple(area)), calc))


_geo_cache: dict = {}


async def api_geo(req: Request) -> Response:
    ufs = tuple(sorted(_lista(req.query_params.get("ufs"))))
    if ufs not in _geo_cache:
        if "geo" not in _geo_cache:
            _geo_cache["geo"] = json.loads(ARQ_MAPA.read_text(encoding="utf-8"))
        codigos = {cod for cod, sigla in UFS.items() if sigla in ufs}
        feats = [f for f in _geo_cache["geo"]["features"] if f["properties"]["cod6"][:2] in codigos]
        _geo_cache[ufs] = {"type": "FeatureCollection", "features": feats}
    return _json(_geo_cache[ufs])


async def api_perfil(req: Request) -> Response:
    f, area = _filtro(req)

    def calc():
        return {
            "indicadores": _indicadores(f, area),
            "piramide": _registros(cq.piramide(f)),
            "raca": _registros(cq.contagem(f, "raca")),
            "situacao": _registros(cq.contagem(f, "situacao", True)),
            "classificacao": _registros(cq.contagem(f, "classificacao", True)),
            "evolucao": _registros(cq.contagem(f, "evolucao_caso")),
            "criterio": _registros(cq.contagem(f, "criterio_confirmacao")),
            "hospitalizado": _registros(cq.contagem(f, "hospitalizado")),
        }
    return _json(_memo(("perfil", f, tuple(area)), calc))


def _variaveis(agravo: str):
    existentes = set(cq.colunas(agravo))
    excluir = ("munic", "uf", "regiao", "rmetri", "nhe", "anos", "meses", "semana", "trime", "mun", "capital")
    return [v for v in ler_def(cat.obter(agravo).arquivo_def or "")
            if v.campo in existentes and not v.cnv.lower().startswith(excluir)]


async def api_variaveis(req: Request) -> Response:
    agravo = req.query_params.get("agravo", "DENG").upper()
    lista = _memo(("vars", agravo), lambda: [
        {"id": i, "rotulo": v.rotulo, "campo": v.campo} for i, v in enumerate(_variaveis(agravo))])
    return _json(lista)


async def api_variavel(req: Request) -> Response:
    f, _ = _filtro(req)
    idx = int(req.query_params.get("id", 0))
    variaveis = _variaveis(f.agravo)
    if not variaveis:
        return _json({"rotulo": "", "valores": []})
    v = variaveis[min(idx, len(variaveis) - 1)]

    def calc():
        conv = ler_cnv(v.cnv)
        d = cq.contagem(f, v.campo)
        d["valor"] = conv.mapear(d["valor"].replace("", None), v.inicio)
        d = d.groupby("valor", as_index=False)["casos"].sum()
        ordem = {r: i for i, r in enumerate(conv.rotulos)}
        d["ordem"] = d["valor"].map(ordem).fillna(999)
        return {"rotulo": v.rotulo, "campo": v.campo, "valores": _registros(d.sort_values("ordem"))}
    return _json(_memo(("var", f, idx), calc))


def _nomes_municipios() -> dict[str, str]:
    df = cq._q("SELECT cod6, municipio || ' (' || uf || ')' n FROM mun")
    return dict(zip(df["cod6"], df["n"]))


async def api_registros(req: Request) -> Response:
    f, _ = _filtro(req)
    pagina = max(0, int(req.query_params.get("pagina", 0)))
    por_pagina = 50

    def calc():
        df = cq.registros(f, limite=None)
        return df
    df = _memo(("regs", f), calc)
    nomes = _nomes_municipios()
    trecho = df.iloc[pagina * por_pagina:(pagina + 1) * por_pagina].copy()
    for col in ("mun_not", "mun_res"):
        trecho[col] = trecho[col].map(lambda c: nomes.get(c, c))
    return _json({"total": len(df), "pagina": pagina, "por_pagina": por_pagina,
                  "linhas": _registros(trecho)})


async def api_exportar(req: Request) -> Response:
    f, area = _filtro(req)
    formato = req.query_params.get("formato", "xlsx")
    nomes = _nomes_municipios()
    nome = f"sinan_{f.agravo}_{f.ano_ini}-{f.ano_fim}"
    if formato == "municipios":
        t = _tabela_municipios(f, area)[["municipio", "uf", "casos", "incidencia", "obitos", "populacao"]]
        t.columns = ["Município", "UF", "Casos", "Incidência por 100 mil hab./ano", "Óbitos", "População média"]
        dados = t.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
        return Response(dados, media_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="{nome}_municipios.csv"'})
    completo = formato == "csv_completo"
    df = cq.registros(f, limite=None if formato != "xlsx" else 1_000_000, todas_colunas=completo)
    for col in ("mun_not", "mun_res"):
        if col in df:
            df[col] = df[col].map(lambda c: nomes.get(c, c))
    if formato == "xlsx":
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="registros")
            _tabela_municipios(f, area).to_excel(w, index=False, sheet_name="por_municipio")
            cq.por_semana(f).to_excel(w, index=False, sheet_name="por_semana")
            cq.por_ano(f).to_excel(w, index=False, sheet_name="por_ano")
        return Response(buf.getvalue(),
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": f'attachment; filename="{nome}.xlsx"'})
    sufixo = "_completo" if completo else ""
    dados = df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
    return Response(dados, media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{nome}{sufixo}.csv"'})


# ------------------------------------------------------------- gestão de dados
_job = {"rodando": False, "tarefa": "", "fracao": 0.0, "mensagem": "", "resultado": None, "erro": None}
_job_lock = threading.Lock()


async def api_dados(req: Request) -> Response:
    cfg = carregar_config()
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
    return _json({
        "config": cfg,
        "listagem_em": (listagem or {}).get("atualizado_em"),
        "catalogo": [{"codigo": c, "nome": cat.nome(c),
                      "anos": sorted((int(a) for a in arquivos.get(c, {})), reverse=True),
                      "tamanhos": {a: i.get("tamanho", 0) for a, i in arquivos.get(c, {}).items()}}
                     for c in catalogo],
        "ufs": sorted(UFS.values()),
        "ufs_nome": UF_NOME,
        "inventario": itens,
        "job": _job,
    })


async def api_listar_ftp(req: Request) -> Response:
    try:
        listar_ftp()
    except Exception as e:
        return _json({"erro": f"Sem conexão com o DATASUS: {e}"}, 502)
    return await api_dados(req)


def _executar(agravos, anos, ufs, forcar):
    def aviso(tarefa, frac, msg):
        _job.update(tarefa=tarefa, fracao=round(frac, 4), mensagem=msg)
    try:
        cfg = carregar_config()
        res = atualizar(agravos, anos, ufs, cfg.get("manter_brutos", False), forcar, aviso)
        _job["resultado"] = res.__dict__
    except Exception as e:
        _job["erro"] = str(e)
    finally:
        _cache.clear()
        _job["rodando"] = False


async def api_atualizar(req: Request) -> Response:
    corpo = await req.json()
    agravos = [a.upper() for a in corpo.get("agravos", [])]
    anos = sorted(int(a) for a in corpo.get("anos", []))
    ufs = [u.upper() for u in corpo.get("ufs", [])]
    if not (agravos and anos and ufs):
        return _json({"erro": "Escolha UF, agravo e ano."}, 400)
    with _job_lock:
        if _job["rodando"]:
            return _json({"erro": "Já existe uma atualização em andamento."}, 409)
        salvar_config({**carregar_config(), "agravos": agravos, "anos": anos, "ufs": ufs})
        _job.update(rodando=True, tarefa="Iniciando", fracao=0.0, mensagem="", resultado=None, erro=None)
        threading.Thread(target=_executar, args=(agravos, anos, ufs, bool(corpo.get("forcar"))),
                         daemon=True).start()
    return _json(_job)


async def api_status(req: Request) -> Response:
    return _json(_job)


async def api_remover(req: Request) -> Response:
    corpo = await req.json()
    for chave in corpo.get("itens", []):
        agravo, ano = chave.rsplit("_", 1)
        remover(agravo, int(ano))
    _cache.clear()
    return await api_dados(req)


# ------------------------------------------------------------------ app
async def pagina(req: Request) -> Response:
    return FileResponse(PASTA_WEB / "index.html", headers={"Cache-Control": "no-cache"})


async def plotly_js(req: Request) -> Response:
    return FileResponse(PLOTLY_JS, headers={"Cache-Control": "max-age=86400"})


def _protegido(func):
    async def inner(req: Request) -> Response:
        try:
            return await func(req)
        except Exception as e:  # erro aparece na tela em vez de travar
            return _json({"erro": str(e)}, 500)
    return inner


rotas = [
    Route("/", pagina),
    Route("/vendor/plotly.min.js", plotly_js),
    Route("/api/meta", _protegido(api_meta)),
    Route("/api/visao", _protegido(api_visao)),
    Route("/api/mapa", _protegido(api_mapa)),
    Route("/api/geo", _protegido(api_geo)),
    Route("/api/perfil", _protegido(api_perfil)),
    Route("/api/variaveis", _protegido(api_variaveis)),
    Route("/api/variavel", _protegido(api_variavel)),
    Route("/api/registros", _protegido(api_registros)),
    Route("/api/exportar", _protegido(api_exportar)),
    Route("/api/dados", _protegido(api_dados)),
    Route("/api/dados/listar", _protegido(api_listar_ftp), methods=["POST"]),
    Route("/api/dados/atualizar", _protegido(api_atualizar), methods=["POST"]),
    Route("/api/dados/status", _protegido(api_status)),
    Route("/api/dados/remover", _protegido(api_remover), methods=["POST"]),
    Mount("/static", StaticFiles(directory=PASTA_WEB), name="static"),
]

app = Starlette(routes=rotas)
