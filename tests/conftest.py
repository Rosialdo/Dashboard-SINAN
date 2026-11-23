"""Ambiente de teste: uma pasta de dados temporária montada a partir da amostra
real ``fixtures/ACBIBR06.dbc`` (acidentes com material biológico, 2006).

Todos os caminhos de ``dados/`` são redirecionados para essa pasta, então os
testes nunca tocam nos dados baixados no computador.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from sinan import config, consultas, download, processar, srag
from sinan.api import app, cache

AMOSTRA = Path(__file__).parent / "fixtures" / "ACBIBR06.dbc"
UFS_TESTE = ["PR", "SP"]


def _redirecionar(mp: pytest.MonkeyPatch, raiz: Path) -> None:
    caminhos = {
        "PASTA_DADOS": raiz,
        "PASTA_BRUTOS": raiz / "brutos",
        "PASTA_PARQUET": raiz / "parquet",
        "ARQ_INVENTARIO": raiz / "inventario.json",
        "ARQ_LISTAGEM_FTP": raiz / "listagem_ftp.json",
        "ARQ_CONFIG": raiz / "configuracao.json",
    }
    for modulo in (config, processar, consultas, download, srag):
        for nome, valor in caminhos.items():
            if hasattr(modulo, nome):
                mp.setattr(modulo, nome, valor)


@pytest.fixture(scope="session")
def dados_teste(tmp_path_factory):
    """Processa a amostra (só PR e SP) e devolve a pasta de dados de teste."""
    raiz = tmp_path_factory.mktemp("dados")
    with pytest.MonkeyPatch.context() as mp:
        _redirecionar(mp, raiz)
        (raiz / "brutos").mkdir()
        dbc = raiz / "brutos" / AMOSTRA.name
        shutil.copy(AMOSTRA, dbc)
        info = {"arquivo": AMOSTRA.name, "situacao": "final", "tamanho": AMOSTRA.stat().st_size, "data_ftp": "01-01-07"}
        n = processar.processar_dbc(dbc, "ACBI", 2006, UFS_TESTE, info)
        (raiz / "configuracao.json").write_text(
            json.dumps({**config.CONFIG_PADRAO, "ufs": UFS_TESTE, "agravos": ["ACBI"], "anos": [2006]}),
            encoding="utf-8")
        cache.limpar()
        yield {"raiz": raiz, "registros": n}
        cache.limpar()


@pytest.fixture
def cliente(dados_teste):
    from starlette.testclient import TestClient

    with TestClient(app, base_url="http://localhost:8501") as c:
        yield c


def escrever_amostra_srag(caminho: Path, antiga: bool = False) -> Path:
    """Parquet no formato do SIVEP-Gripe, sem dado real: 3 fichas de RR e 3 de SP.

    ``antiga=False`` usa os tipos do arquivo de 2026 (datas em timestamp, códigos em decimal);
    ``antiga=True`` imita anos antigos (data em texto dd/mm/aaaa ou date32, idade em texto).
    """
    import datetime as dt
    from decimal import Decimal

    import pyarrow as pa
    import pyarrow.parquet as pq

    datas = [dt.date(2026, 5, 9), dt.date(2026, 1, 1), dt.date(2026, 1, 4)] * 2
    sem_pri = ["18", "53", "1"] * 2  # semana oficial de cada data
    ufs = ["RR"] * 3 + ["SP"] * 3
    mun = ["140010"] * 3 + ["355030"] * 3
    classi = ["5", "1", None, "4", "2", "5"]
    idade = ["30", "3", "70", "1", "45", "8"]
    tp_idade = ["3", "2", "3", "1", "3", "3"]
    colunas = {
        "SG_UF_NOT": pa.array(ufs), "SG_UF": pa.array(ufs),
        "ID_MUNICIP": pa.array(["BOA VISTA"] * 3 + ["SAO PAULO"] * 3),
        "CO_MUN_NOT": pa.array(mun), "CO_MUN_RES": pa.array(mun),
        "SEM_PRI": pa.array(sem_pri), "TP_IDADE": pa.array(tp_idade),
        "CS_SEXO": pa.array(["F", "M", "F", "M", "F", "I"]), "CS_RACA": pa.array(["5", "4", "9", "1", "4", "2"]),
        "CRITERIO": pa.array([Decimal(1), Decimal(3), None, Decimal(1), Decimal(1), Decimal(2)], pa.decimal128(3, 0)),
        "EVOLUCAO": pa.array(["2", "1", None, "1", "3", "1"]),
        "HOSPITAL": pa.array(["1", "1", "9", "1", "2", "1"]),
    }
    if antiga:
        colunas["DT_NOTIFIC"] = pa.array(datas, pa.date32())
        colunas["DT_SIN_PRI"] = pa.array([d.strftime("%d/%m/%Y") for d in datas])
        colunas["NU_IDADE_N"] = pa.array(idade)
        colunas["CLASSI_FIN"] = pa.array(classi)
    else:
        ts = [dt.datetime.combine(d, dt.time()) for d in datas]
        colunas["DT_NOTIFIC"] = pa.array(ts, pa.timestamp("ns"))
        colunas["DT_SIN_PRI"] = pa.array(ts, pa.timestamp("ns"))
        colunas["NU_IDADE_N"] = pa.array([Decimal(i) for i in idade], pa.decimal128(3, 0))
        colunas["CLASSI_FIN"] = pa.array([Decimal(c) if c else None for c in classi], pa.decimal128(38, 10))
    pq.write_table(pa.table(colunas), caminho)
    return caminho


@pytest.fixture
def amostra_srag(tmp_path):
    return escrever_amostra_srag(tmp_path / "INFLUD26.parquet")


@pytest.fixture
def dados_srag(tmp_path, monkeypatch):
    """Pasta de dados própria e vazia (nunca a ``dados_teste`` da sessão)."""
    raiz = tmp_path / "dados"
    _redirecionar(monkeypatch, raiz)
    cache.limpar()
    yield raiz
    cache.limpar()
