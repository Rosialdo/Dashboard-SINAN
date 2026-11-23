"""SRAG do SIVEP-Gripe (sinan/srag.py): conversão para o formato do painel."""

import pandas as pd
import pyarrow.parquet as pq
import pytest
from conftest import escrever_amostra_srag

from sinan import processar, srag


def test_para_sinan_converte_uf_municipio_data_e_idade():
    df = pd.DataFrame({"SG_UF_NOT": ["RR"], "SG_UF": ["RR"], "CO_MUN_NOT": ["140010"],
                       "CO_MUN_RES": ["140010"], "DT_SIN_PRI": ["2026-05-09"],
                       "DT_NOTIFIC": ["2026-05-12"], "TP_IDADE": ["2"], "NU_IDADE_N": ["3"]})
    s = srag.para_sinan(df)
    assert s.loc[0, ["SG_UF", "ID_MN_RESI", "DT_SIN_PRI", "NU_IDADE_N"]].tolist() == \
        ["14", "140010", "20260509", "3003"]  # dia 9 de maio, não 5 de setembro
    assert df.loc[0, "SG_UF"] == "RR"  # o original não é alterado


def test_para_sinan_aceita_data_em_texto_brasileiro_e_idade_vazia():
    df = pd.DataFrame({"SG_UF": ["RR"], "DT_SIN_PRI": ["09/05/2026"], "TP_IDADE": [None], "NU_IDADE_N": [None]})
    s = srag.para_sinan(df)
    assert s.loc[0, "DT_SIN_PRI"] == "20260509" and pd.isna(s.loc[0, "NU_IDADE_N"])


@pytest.mark.parametrize("antiga", [False, True])
def test_processar_srag_filtra_uf_e_deriva(dados_srag, tmp_path, antiga):
    amostra = escrever_amostra_srag(tmp_path / "amostra.parquet", antiga)
    n = srag.processar(amostra, 2026, ["RR"], {"arquivo": "INFLUD26-23-11-2026.parquet",
                       "situacao": "preliminar", "data_ftp": "23-11-2026"})
    t = pq.read_table(processar.caminho_parquet("SRAG", 2026)).to_pandas()
    assert n == len(t) == 3
    assert set(t["uf_res"]) == {"RR"} and t["SG_UF"].eq("RR").all()  # original em sigla
    assert t["CLASSI_FIN"].iloc[0] == "5" and t["classificacao"].iloc[0] == "SRAG por covid-19"
    assert t["classificacao"].iloc[2] == "Em investigação"
    assert (t["sem_epi"].astype(str) == t["SEM_PRI"]).all()  # mesma regra do SIVEP
    assert t["idade"].notna().all() and t["data_sintomas"].notna().all()
    assert t["idade"].iloc[1] == pytest.approx(0.25)  # 3 meses
    assert processar.ler_inventario()["SRAG_2026"]["data_ftp"] == "23-11-2026"


def test_processar_srag_uf_sem_casos_gera_arquivo_vazio(dados_srag, amostra_srag):
    assert srag.processar(amostra_srag, 2026, ["AC"]) == 0
    nomes = pq.read_schema(processar.caminho_parquet("SRAG", 2026)).names
    assert {"CLASSI_FIN", "SG_UF", "CO_MUN_RES", "hospitalizado"} <= set(nomes)  # originais + derivadas
