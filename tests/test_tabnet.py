"""Leitura dos rótulos oficiais do TabNet (sinan/tabnet.py)."""

import pandas as pd

from sinan.tabnet import conversor_do_campo, ler_cnv, ler_def


def test_cnv_de_raca():
    conv = ler_cnv("raça.cnv")
    assert conv is not None
    r = conv.mapear(pd.Series(["1", "4", "9", None, "7"]))
    # linhas posteriores têm prioridade sobre o "Ign/Branco ,0-9"
    assert r.tolist()[:2] == ["Branca", "Parda"]
    assert r.iloc[2] == "Ign/Branco"
    assert r.iloc[3] == "Ign/Branco"


def test_mapear_com_posicao_inicial():
    conv = ler_cnv("raça.cnv")
    # posição 2: pega o segundo caractere do código
    assert conv.mapear(pd.Series(["X2"]), inicio=2).iloc[0] == "Preta"


def test_def_da_dengue_tem_classificacao_final():
    variaveis = ler_def("denguenet.def")
    assert any(v.campo == "CLASSI_FIN" for v in variaveis)
    conv = conversor_do_campo("denguenet.def", "CLASSI_FIN")
    assert conv is not None
    assert "descart" in conv.mapear(pd.Series(["5"])).iloc[0].lower()


def test_arquivo_inexistente():
    assert ler_cnv("nao_existe.cnv") is None
    assert ler_def("nao_existe.def") == []
    assert conversor_do_campo(None, "CLASSI_FIN") is None
