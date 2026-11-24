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


def test_semana_por_municipio_usa_o_local_do_filtro(dados_teste, monkeypatch):
    sqls = []
    monkeypatch.setattr(cq, "_q", lambda sql, params=None: sqls.append(sql) or None)
    cq.semana_por_municipio(cq.Filtro("ACBI", 2006, 2006, por_residencia=True), (1,))
    cq.semana_por_municipio(cq.Filtro("ACBI", 2006, 2006, por_residencia=False), (1,))
    assert "mun_res cod6" in sqls[0] and "mun_not cod6" in sqls[1]


def test_semana_por_municipio_bate_com_por_semana(dados_teste):
    f = cq.Filtro("ACBI", 2006, 2006, contagem="todas")
    m = cq.semana_por_municipio(f, tuple(range(1, 54)))
    # por_semana corta o que tem ano_epi fora de ini..fim; semana_por_municipio não
    m = m[m["ano_epi"].between(2006, 2006)].groupby(["ano_epi", "sem_epi"])["casos"].sum()
    s = cq.por_semana(f).set_index(["ano_epi", "sem_epi"])["casos"]
    assert m.to_dict() == s.to_dict()
    assert cq.totais_por_municipio(f)["casos"].sum() >= s.sum()


def test_ultima_notificacao_e_data_referencia(dados_teste):
    ultima = cq.ultima_notificacao("ACBI")
    assert ultima is not None and ultima.year in (2006, 2007)
    assert cq.indicadores(cq.Filtro("ACBI", 2006, 2006, contagem="todas"))["ultima_notificacao"].date() == ultima
    from sinan.api import servicos
    assert servicos.data_referencia("ACBI") <= ultima
    assert servicos.data_referencia("DENG") is None  # sem dados baixados
