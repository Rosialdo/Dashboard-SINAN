"""Filtros e consultas DuckDB (sinan/consultas.py)."""

import pytest

from sinan import consultas as cq


def test_filtro_monta_sql_com_parametros():
    f = cq.Filtro("DENG", 2020, 2024, por_residencia=False, ufs=("RR", "AM"), municipios=("140010",),
                  contagem="provaveis", sexo=("Feminino",), faixas=("20-29", "30-39"))
    sql, params = f.where()
    assert "uf_not IN (?,?)" in sql and "mun_not IN (?)" in sql
    assert "situacao <> 'Descartado'" in sql
    assert params == [2020, 2024, "RR", "AM", "140010", "Feminino", "20-29", "30-39"]


def test_filtro_confirmados_e_todas():
    assert "confirmado" in cq.Filtro("DENG", 2024, 2024).where()[0]
    sql, params = cq.Filtro("DENG", 2024, 2024, contagem="todas").where()
    assert sql == "ano BETWEEN ? AND ?" and params == [2024, 2024]


@pytest.mark.parametrize("codigo", ["", "D", "DENG'); DROP TABLE mun; --", "../../x", "DENG/..", "ABCDEFGHIJ"])
def test_codigo_de_agravo_invalido(codigo):
    with pytest.raises(cq.AgravoInvalido):
        cq.validar_agravo(codigo)


def test_codigo_valido_vira_maiusculo():
    assert cq.validar_agravo("deng") == "DENG"


def test_agravo_sem_dados(dados_teste):
    assert not cq.tem_dados("DENG")
    with pytest.raises(cq.AgravoInvalido, match="Não há dados"):
        cq.anos("DENG")


def test_consultas_sobre_a_amostra(dados_teste):
    f = cq.Filtro("ACBI", 2006, 2006, contagem="todas")
    assert cq.anos("ACBI") == [2006]
    assert set(cq.ufs_presentes("ACBI")) >= {"PR", "SP"}
    assert cq.total_registros(f) == dados_teste["registros"]
    pagina = cq.registros(f, limite=10, inicio=5)
    assert len(pagina) == 10
    assert cq.indicadores(f)["notificacoes"] == dados_teste["registros"]


def test_contagem_rejeita_coluna_invalida(dados_teste):
    with pytest.raises(ValueError):
        cq.contagem(cq.Filtro("ACBI", 2006, 2006), 'sexo"; DROP TABLE mun; --')
