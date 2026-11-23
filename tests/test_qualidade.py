"""Indicadores de qualidade por prazo (notificação, digitação, investigação, encerramento)."""

from datetime import date

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from sinan import consultas, processar
from sinan.api import cache

REF = date(2024, 12, 31)
D = date

# (sintomas, notificação, DT_DIGITA, DT_INVEST, DT_ENCERRA, confirmado, município)
FICHAS = [
    (D(2024, 5, 25), D(2024, 6, 1), "20240608", "20240603", "20240731", True, "140010"),
    (D(2024, 5, 24), D(2024, 6, 1), "20240609", "20240604", "20240801", True, "140010"),
    (D(2024, 6, 5), D(2024, 6, 1), "   ", "xx", "xx", True, "140010"),
    (None, D(2024, 6, 1), "20240530", None, "20240520", True, "140010"),
    (None, D(2024, 10, 31), None, None, "  ", True, "140010"),
    (None, D(2024, 11, 1), None, None, None, True, "140010"),
    (D(2024, 5, 31), D(2024, 6, 1), "20240602", "20240601", "20240611", False, "140010"),
    (None, D(2024, 12, 20), None, None, None, True, "140020"),
]


def _txt(d):
    return None if d is None else d.strftime("%Y%m%d")


@pytest.fixture
def dados_qualidade(dados_srag):
    pasta = processar.PASTA_PARQUET / "DENG"
    pasta.mkdir(parents=True)
    n = len(FICHAS)
    comuns = {"uf_res": ["RR"] * n, "uf_not": ["RR"] * n, "sexo": ["Feminino"] * n, "faixa_etaria": ["20-29"] * n}
    pq.write_table(pa.table({
        "ano": [2024] * n, **comuns,
        "data_sintomas": pa.array([f[0] for f in FICHAS], pa.date32()),
        "data_notificacao": pa.array([f[1] for f in FICHAS], pa.date32()),
        "DT_SIN_PRI": [_txt(f[0]) for f in FICHAS],
        "DT_NOTIFIC": [_txt(f[1]) for f in FICHAS],
        "DT_DIGITA": [f[2] for f in FICHAS], "DT_INVEST": [f[3] for f in FICHAS],
        "DT_ENCERRA": [f[4] for f in FICHAS],
        "confirmado": [f[5] for f in FICHAS],
        "situacao": ["Confirmado" if f[5] else "Descartado" for f in FICHAS],
        "mun_res": [f[6] for f in FICHAS], "mun_not": [f[6] for f in FICHAS],
    }), pasta / "DENG_2024.parquet")
    pq.write_table(pa.table({
        "ano": [2023], "uf_res": ["RR"], "uf_not": ["RR"], "sexo": ["Feminino"], "faixa_etaria": ["20-29"],
        "data_sintomas": pa.array([None], pa.date32()),
        "data_notificacao": pa.array([D(2023, 3, 1)], pa.date32()),
        "DT_SIN_PRI": pa.array([None], pa.string()), "DT_NOTIFIC": ["20230301"],
        "confirmado": [True], "situacao": ["Confirmado"], "mun_res": ["140010"], "mun_not": ["140010"],
    }), pasta / "DENG_2023.parquet")
    cache.limpar()


def _resumo(q):
    return {i["id"]: (i["base"], i["no_prazo"], i["pct"], i["sem_encerramento"]) for i in q["prazos"]}


def test_qualidade_por_prazo(dados_qualidade):
    q = consultas.qualidade(consultas.Filtro("DENG", 2024, 2024), REF)
    assert q["referencia"] == REF and q["notificacoes"] == 8
    assert [i["id"] for i in q["prazos"]] == ["notificacao", "digitacao", "investigacao", "encerramento"]
    assert _resumo(q) == {
        "notificacao": (3, 2, 66.7, 0),
        "digitacao": (3, 2, 66.7, 0),
        "investigacao": (3, 2, 66.7, 0),
        "encerramento": (4, 2, 50.0, 1),
    }


def test_qualidade_ignora_filtro_de_confirmados(dados_qualidade):
    todas = consultas.qualidade(consultas.Filtro("DENG", 2024, 2024, contagem="todas"), REF)
    assert _resumo(todas) == _resumo(consultas.qualidade(consultas.Filtro("DENG", 2024, 2024), REF))


def test_ano_sem_campo_nao_conta_como_sem_encerramento(dados_qualidade):
    assert consultas.anos_sem_coluna("DENG", "DT_ENCERRA") == [2023]
    assert consultas.anos_sem_coluna("deng", "DT_ENCERRA") == [2023]
    q = consultas.qualidade(consultas.Filtro("DENG", 2023, 2024), REF)
    assert q["notificacoes"] == 9
    assert _resumo(q)["encerramento"] == (4, 2, 50.0, 1)


def test_referencia_ignora_filtros(dados_qualidade):
    for f in (consultas.Filtro("DENG", 2024, 2024, municipios=("140010",)),
              consultas.Filtro("DENG", 2023, 2023)):
        assert consultas.qualidade(f)["referencia"] == date(2024, 12, 20)


def test_qualidade_sem_campos_originais(dados_teste):
    assert "data_sintomas" in consultas.colunas("ACBI") and "DT_SIN_PRI" not in consultas.colunas("ACBI")
    q = consultas.qualidade(consultas.Filtro("ACBI", 2006, 2006))
    assert [i["disponivel"] for i in q["prazos"]] == [False, False, False, False]
    assert q["notificacoes"] > 0


def test_data_sql_aceita_formatos():
    con = duckdb.connect()
    r = con.execute(f"""SELECT {consultas._data_sql('x')} FROM
        (VALUES ('20240105'), ('05/01/2024'), ('2024-01-05 00:00:00'), (''), ('  '),
        ('xx'), ('20420101'), ('18991231')) t(x)""").fetchall()
    assert [x[0] for x in r] == [date(2024, 1, 5)] * 3 + [None] * 5


def test_data_dos_arquivos(dados_srag):
    for agravo, ano, data in [("DENG", 2023, "01-15-24 10:00AM"), ("DENG", 2024, "11-10-26 09:41AM"),
                              ("SRAG", 2026, "23-11-2026"), ("ZIKA", 2026, "")]:
        processar.registrar_inventario(agravo, ano, 1, ["RR"], {"data_ftp": data}, "x")
    assert processar.data_dos_arquivos("DENG") == date(2026, 11, 10)
    assert processar.data_dos_arquivos("SRAG") == date(2026, 11, 23)
    assert processar.data_dos_arquivos("ZIKA") is None and processar.data_dos_arquivos("CHIK") is None


def test_rota_qualidade(cliente):
    d = cliente.get("/api/qualidade?agravo=ACBI").json()
    assert len(d["prazos"]) == 4 and d["referencia"] == "2007-01-01"
