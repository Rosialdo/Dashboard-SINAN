import math

import pandas as pd
import pytest

from sinan.api.servicos import taxa_suavizada


def test_puxa_municipio_pequeno_para_a_media():
    r = taxa_suavizada(pd.Series([0, 30, 500]), pd.Series([1000, 2000, 100000]))
    assert list(r) == pytest.approx([369.8, 947.2, 500.4], abs=0.1)
    # bruta: 0, 1500, 500 — o grande quase não muda, os pequenos se aproximam de 514,6


def test_sem_casos_na_area_da_zero():
    r = taxa_suavizada(pd.Series([0, 0]), pd.Series([1000, 5000]))
    assert list(r) == [0.0, 0.0]


def test_variancia_pequena_vira_a_media():
    r = taxa_suavizada(pd.Series([0, 1, 50]), pd.Series([1000, 2000, 100000]))
    assert list(r.round(2)) == [49.51, 49.51, 49.51]


@pytest.mark.parametrize("sem_pop", [None, 0])
def test_sem_populacao_fica_vazio_e_nao_entra_na_media(sem_pop):
    r = taxa_suavizada(pd.Series([0, 30, 500, 7]), pd.Series([1000, 2000, 100000, sem_pop]))
    assert math.isnan(r.iloc[3])
    assert list(r.iloc[:3]) == pytest.approx([369.8, 947.2, 500.4], abs=0.1)


def test_sem_populacao_valida():
    r = taxa_suavizada(pd.Series([0, 10, 3]), pd.Series([None, 0, float("inf")]))
    assert r.isna().all()
