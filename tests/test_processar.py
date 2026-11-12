"""Regras epidemiológicas das colunas derivadas (sinan/processar.py)."""

import pandas as pd
import pyarrow.parquet as pq
import pytest

from sinan import agravos as cat
from sinan.processar import caminho_parquet, derivar, idade_em_anos, semana_epidemiologica


@pytest.mark.parametrize(("data", "ano", "semana"), [
    ("2024-12-29", 2025, 1),   # domingo: a semana tem 4 dias em 2025
    ("2025-01-04", 2025, 1),   # sábado da mesma semana
    ("2025-12-31", 2025, 53),  # 2025 tem 53 semanas epidemiológicas
    ("2026-01-03", 2025, 53),
    ("2026-01-04", 2026, 1),
    ("2023-01-01", 2023, 1),
    ("2022-01-01", 2021, 52),  # sábado: ainda é a última semana de 2021
    ("2024-06-15", 2024, 24),
])
def test_semana_epidemiologica(data, ano, semana):
    a, s = semana_epidemiologica(pd.Series(pd.to_datetime([data])))
    assert (int(a.iloc[0]), int(s.iloc[0])) == (ano, semana)


def test_idade_em_anos():
    # 1º dígito = unidade (1 hora, 2 dia, 3 mês, 4 ano)
    s = pd.Series(["4025", "3006", "2010", "1005", "4130", None, "abc"])
    r = idade_em_anos(s, len(s))
    assert r.iloc[0] == 25
    assert r.iloc[1] == pytest.approx(0.5)
    assert r.iloc[2] == 0 and r.iloc[3] == 0
    assert pd.isna(r.iloc[4])  # 130 anos: descartado
    assert pd.isna(r.iloc[5]) and pd.isna(r.iloc[6])


def _ficha_dengue(**campos) -> pd.DataFrame:
    n = len(next(iter(campos.values())))
    base = {"DT_NOTIFIC": ["20240110"] * n, "DT_SIN_PRI": ["20240108"] * n, "SG_UF": ["14"] * n,
            "ID_MN_RESI": ["140010"] * n, "NU_IDADE_N": ["4030"] * n, "CS_SEXO": ["F"] * n}
    return pd.DataFrame({**base, **campos})


def test_derivar_dengue_confirmacao_e_obito():
    df = _ficha_dengue(
        CLASSI_FIN=["10", "11", "12", "5", "13", "8", None],
        EVOLUCAO=["2", "1", "3", "1", "1", "4", "9"],
    )
    out = derivar(df, cat.obter("DENG"), 2024)
    assert out["confirmado"].tolist() == [True, True, True, False, False, False, False]
    # 13 = chikungunya na ficha de dengue: conta como descartado para dengue
    assert out["situacao"].tolist()[3:5] == ["Descartado", "Descartado"]
    assert out["situacao"].iloc[5] == "Inconclusivo"
    assert out["situacao"].iloc[6] == "Em aberto/Ign."
    # óbito pelo agravo conta; óbito por outras causas e em investigação não
    assert out["obito"].tolist() == [True, False, False, False, False, False, False]
    assert set(out["uf_res"]) == {"RR"}
    assert out["faixa_etaria"].iloc[0] == "30-39"
    assert out["sem_epi"].iloc[0] == 2 and out["ano_epi"].iloc[0] == 2024


def test_derivar_agravo_sem_confirmacao_conta_tudo():
    df = _ficha_dengue(CLASSI_FIN=["5", None])
    out = derivar(df, cat.obter("TUBE"), 2024)
    assert out["confirmado"].all()
    assert set(out["situacao"]) == {"Notificado"}


def test_data_de_referencia_usa_notificacao_quando_falta_sintoma():
    df = _ficha_dengue(DT_SIN_PRI=[None], CLASSI_FIN=["10"])
    out = derivar(df, cat.obter("DENG"), 2024)
    assert str(out["data_referencia"].iloc[0]) == "2024-01-10"


def test_processar_dbc_filtra_ufs(dados_teste):
    tabela = pq.read_table(caminho_parquet("ACBI", 2006)).to_pandas()
    assert len(tabela) == dados_teste["registros"] > 0
    # cada registro tem residência ou notificação em PR/SP
    dentro = tabela["uf_res"].isin(["PR", "SP"]) | tabela["uf_not"].isin(["PR", "SP"])
    assert dentro.all()
    # mantém as colunas originais (maiúsculas) e as derivadas (minúsculas)
    assert {"ID_AGRAVO", "DT_NOTIFIC", "data_notificacao", "sem_epi", "situacao"} <= set(tabela.columns)
    # nada sobra na pasta de brutos além do .dbc (o .dbf temporário é apagado)
    assert not list((dados_teste["raiz"] / "brutos").glob("*.dbf"))
