from datetime import date

import duckdb
import pandas as pd
import pytest

from sinan import consultas as cq
from sinan import processar
from sinan.api import servicos
from sinan.api.servicos import (
    alerta_municipios,
    anos_do_canal,
    anos_epi_cobertos,
    data_referencia,
    faixa_esperada,
    nivel_alerta,
    semana_coberta,
    semana_referencia,
)


def test_ano_epi_precisa_do_ano_seguinte():
    # 2021 sem 2022 e 2024 sem 2025 são parciais
    assert anos_epi_cobertos([2019, 2020, 2021, 2023, 2024]) == [2019, 2020, 2023]


def test_ano_sem_arquivo_nao_e_coberto():
    assert 2021 not in anos_epi_cobertos([2019, 2020, 2022, 2023])  # sem arquivo de 2021
    assert 2020 not in anos_epi_cobertos([2019, 2020, 2022, 2023])  # 2020 sem o 2021


def test_cobertura_pelo_inventario(monkeypatch):
    inv = {"DENG_2020": {"agravo": "DENG", "ano": 2020, "ufs": ["RR"]},
           "DENG_2021": {"agravo": "DENG", "ano": 2021, "ufs": ["AM", "RR"]},
           "DENG_2022": {"agravo": "DENG", "ano": 2022, "ufs": ["BR"]},
           "HANS_2020": {"agravo": "HANS", "ano": 2020, "ufs": ["AM"]}}
    monkeypatch.setattr(processar, "ler_inventario", lambda: inv)
    assert cq.anos_notificacao_cobertos("DENG", ("RR",)) == [2020, 2021, 2022]
    assert cq.anos_notificacao_cobertos("DENG", ("AM",)) == [2021, 2022]
    assert cq.anos_notificacao_cobertos("DENG", ("AM", "RR")) == [2021, 2022]


def test_cobertura_sem_ufs_exige_br(monkeypatch):
    inv = {"DENG_2020": {"agravo": "DENG", "ano": 2020, "ufs": ["RR"]},
           "DENG_2021": {"agravo": "DENG", "ano": 2021, "ufs": ["AM", "RR"]},
           "DENG_2022": {"agravo": "DENG", "ano": 2022, "ufs": ["BR"]},
           "DENG_2023": {"agravo": "DENG", "ano": 2023}}  # entrada antiga, sem "ufs"
    monkeypatch.setattr(processar, "ler_inventario", lambda: inv)
    assert cq.anos_notificacao_cobertos("DENG", ()) == [2022]
    assert cq.anos_notificacao_cobertos("DENG", ("RR",)) == [2020, 2021, 2022]


def _t(d):   # {ano_epi: casos} -> DataFrame de totais da área
    return pd.DataFrame({"ano_epi": list(d), "casos": list(d.values())})

def _usados(r):
    return r.loc[~r.excluido, "ano_epi"].tolist()

def test_exclui_ano_epidemico():
    r = anos_do_canal(_t({2019: 100, 2020: 110, 2021: 400, 2022: 90, 2023: 105, 2024: 95, 2025: 100}),
                      2026, list(range(2019, 2026)))
    assert r.loc[r.excluido, "ano_epi"].tolist() == [2021] and len(_usados(r)) == 6

def test_dois_anos_atipicos():
    r = anos_do_canal(_t({2019: 100, 2020: 400, 2021: 100, 2022: 350, 2023: 100, 2024: 100, 2025: 100}),
                      2026, list(range(2019, 2026)))
    assert r.loc[r.excluido, "ano_epi"].tolist() == [2020, 2022]

def test_usa_os_7_anos_epidemiologicos_cobertos_mais_recentes():
    # "cobertos" são anos EPIDEMIOLÓGICOS (saída de anos_epi_cobertos), não anos de notificação
    r = anos_do_canal(_t({a: 100 for a in range(2015, 2026)}), 2026, list(range(2015, 2026)))
    assert _usados(r) == list(range(2019, 2026))

def test_registros_tardios_de_ano_nao_coberto_nao_entram():
    # sem arquivo de 2021: os 3 casos com ano_epi 2021 vieram do arquivo de 2022; 2020 também fica parcial (D3)
    r = anos_do_canal(_t({2018: 100, 2019: 100, 2020: 100, 2021: 3, 2022: 100, 2023: 100, 2024: 100, 2025: 100}),
                      2026, [2018, 2019, 2022, 2023, 2024, 2025])
    assert _usados(r) == [2018, 2019, 2022, 2023, 2024, 2025]

def test_ano_coberto_sem_registro_vale_zero():
    r = anos_do_canal(_t({2019: 5, 2020: 5, 2021: 5, 2023: 5, 2024: 5, 2025: 5}), 2026, list(range(2019, 2026)))
    assert 2022 in _usados(r)

def test_menos_de_5_anos_sem_canal():
    assert anos_do_canal(_t({2022: 100, 2023: 100, 2024: 100, 2025: 100}), 2026, [2022, 2023, 2024, 2025]).empty

def test_exclusao_deixa_menos_de_5():
    r = anos_do_canal(_t({2020: 100, 2021: 400, 2022: 100, 2023: 100, 2024: 400, 2025: 100}),
                      2026, list(range(2020, 2026)))
    assert r.empty

def test_agravo_raro_mediana_zero_nao_exclui():
    r = anos_do_canal(_t({2019: 0, 2020: 0, 2021: 1, 2022: 0, 2023: 0, 2024: 0, 2025: 2}), 2026, list(range(2019, 2026)))
    assert len(_usados(r)) == 7

def test_surto_localizado_sai_so_do_municipio():
    # A: surto em 2021; B: estável. Área: 70 em 2021 contra mediana 52 (limite 78) -> a área não exclui
    anos_ = list(range(2019, 2026))
    t = pd.DataFrame({"cod6": ["A"] * 7 + ["B"] * 7, "ano_epi": anos_ * 2,
                      "casos": [2, 2, 20, 2, 2, 2, 2] + [50] * 7})
    cob = pd.DataFrame([(c, a) for c in "ABC" for a in anos_], columns=["cod6", "ano_epi"])
    r = anos_do_canal(t, 2026, cob)
    assert r.loc[r.excluido, ["cod6", "ano_epi"]].values.tolist() == [["A", 2021]]
    assert set(r.cod6) == {"A", "B", "C"}            # C sem nenhum caso: 7 anos com 0
    area = anos_do_canal(t.groupby("ano_epi", as_index=False).casos.sum(), 2026, anos_)
    assert not area.excluido.any()

def test_cada_municipio_usa_a_sua_cobertura():
    # A em UF com 2019-2025 cobertos; B em UF com só 2022-2025 cobertos -> B sem histórico suficiente
    t = pd.DataFrame({"cod6": ["A", "B"], "ano_epi": [2020, 2023], "casos": [1, 1]})
    cob = pd.DataFrame([("A", a) for a in range(2019, 2026)] + [("B", a) for a in range(2022, 2026)],
                       columns=["cod6", "ano_epi"])
    r = anos_do_canal(t, 2026, cob)
    assert set(r.cod6) == {"A"} and len(_usados(r)) == 7

def test_quartis_por_semana():
    anos = pd.DataFrame({"ano_epi": [2019, 2020, 2021, 2022, 2023], "excluido": False})
    s = pd.DataFrame({"ano_epi": [2019, 2020, 2021, 2022, 2023], "sem_epi": 10, "casos": [0, 2, 4, 6, 8]})
    f = faixa_esperada(s, anos)
    assert f[f.sem_epi == 10][["q1", "mediana", "q3"]].iloc[0].tolist() == [2, 4, 6]
    assert f[f.sem_epi == 11][["q1", "mediana", "q3"]].iloc[0].tolist() == [0, 0, 0]   # muitos zeros
    assert len(f) == 53

def test_semana_53_copia_a_52():
    anos = pd.DataFrame({"ano_epi": [2019, 2020, 2021, 2022, 2023], "excluido": False})
    s = pd.DataFrame({"ano_epi": [2019, 2020, 2021, 2022, 2023], "sem_epi": 52, "casos": [1, 2, 3, 4, 5]})
    f = faixa_esperada(s, anos).set_index("sem_epi")
    assert f.loc[53].tolist() == f.loc[52].tolist()

def test_faixa_por_municipio_so_semanas_pedidas_e_zeros():
    anos = pd.DataFrame({"cod6": ["A"] * 5 + ["B"] * 5, "ano_epi": list(range(2019, 2024)) * 2, "excluido": False})
    s = pd.DataFrame({"cod6": ["A"] * 5 + ["B"], "ano_epi": [2019, 2020, 2021, 2022, 2023, 2019],
                      "sem_epi": 10, "casos": [1, 1, 1, 1, 1, 5]})
    f = faixa_esperada(s, anos, semanas=(10,))
    assert len(f) == 2
    assert f[f.cod6 == "B"][["q1", "mediana", "q3"]].iloc[0].tolist() == [0, 0, 0]   # 5, 0, 0, 0, 0


def test_faixa_sem_anos_devolve_vazio():
    s = pd.DataFrame({"ano_epi": [2019], "sem_epi": 10, "casos": [1]})
    f = faixa_esperada(s, pd.DataFrame({"ano_epi": [], "excluido": []}))
    assert f.empty and list(f.columns) == ["sem_epi", "q1", "mediana", "q3"]
    sg = s.assign(cod6="A")
    fg = faixa_esperada(sg, pd.DataFrame({"cod6": [], "ano_epi": [], "excluido": []}))
    assert fg.empty and list(fg.columns) == ["cod6", "sem_epi", "q1", "mediana", "q3"]


def test_serie_fora_de_cobertos_e_ignorada():
    anos_ = list(range(2019, 2026))
    t = pd.DataFrame({"cod6": ["A"] * 7 + ["B"] * 7, "ano_epi": anos_ * 2, "casos": 5})
    cob = pd.DataFrame({"cod6": "A", "ano_epi": anos_})
    assert set(anos_do_canal(t, 2026, cob).cod6) == {"A"}


def test_semana_53_historica_e_descartada():
    anos = pd.DataFrame({"ano_epi": list(range(2019, 2024)), "excluido": False})
    s = pd.DataFrame({"ano_epi": list(range(2019, 2024)) * 2, "sem_epi": [52] * 5 + [53] * 5,
                      "casos": [1] * 5 + [99] * 5})
    f = faixa_esperada(s, anos).set_index("sem_epi")
    assert f.loc[53, "q3"] == 1 and f.loc[52, "q3"] == 1


def test_quartis_interpolacao_linear():
    anos = pd.DataFrame({"ano_epi": list(range(2018, 2024)), "excluido": False})
    s = pd.DataFrame({"ano_epi": list(range(2018, 2024)), "sem_epi": 10, "casos": [0, 1, 2, 3, 4, 10]})
    f = faixa_esperada(s, anos, semanas=(10,))
    assert f[["q1", "mediana", "q3"]].iloc[0].tolist() == [1.25, 2.5, 3.75]


def test_ufs_da_serie():
    area = ("AM", "RR")
    assert servicos.ufs_da_serie(cq.Filtro("DENG", 2020, 2020, ufs=("AM",)), area) == ("AM",)
    assert servicos.ufs_da_serie(cq.Filtro("DENG", 2020, 2020, municipios=("140010",)), area) == ("RR",)
    assert servicos.ufs_da_serie(cq.Filtro("DENG", 2020, 2020), area) == area


def test_filtro_da_serie():
    area = ("AM", "RR")
    assert servicos.filtro_da_serie(cq.Filtro("DENG", 2020, 2020), area).ufs == area
    com_uf = cq.Filtro("DENG", 2020, 2020, ufs=("AM",))
    com_mun = cq.Filtro("DENG", 2020, 2020, municipios=("140010",))
    assert servicos.filtro_da_serie(com_uf, area) == com_uf
    assert servicos.filtro_da_serie(com_mun, area) == com_mun


def test_ufs_da_serie_varios_municipios_e_codigo_desconhecido():
    area = ("AM", "RR")
    assert servicos.ufs_da_serie(cq.Filtro("DENG", 2020, 2020, municipios=("140010", "130260")), area) == ("AM", "RR")
    assert servicos.ufs_da_serie(cq.Filtro("DENG", 2020, 2020, municipios=("990010",)), area) == ()


def test_canal_sem_uf_conhecida_nao_tem_canal(monkeypatch):
    inv = {f"DENG_{a}": {"agravo": "DENG", "ano": a, "ufs": ["RR"]} for a in range(2010, 2021)}
    monkeypatch.setattr(processar, "ler_inventario", lambda: inv)  # sem "BR"
    f = cq.Filtro("DENG", 2020, 2020, municipios=("990010",))
    assert servicos.canal_endemico(f, ("RR",)) == (None, "sem_cobertura")


# ------------------------------------------------------------- alerta por município
@pytest.mark.parametrize("data, esperado", [
    (date(2026, 11, 12), (2026, 44, date(2026, 11, 1), date(2026, 11, 7))),
    (date(2026, 11, 8), (2026, 44, date(2026, 11, 1), date(2026, 11, 7))),
    (date(2026, 11, 7), (2026, 43, date(2026, 10, 25), date(2026, 10, 31))),
    (date(2021, 1, 6), (2020, 53, date(2020, 12, 27), date(2021, 1, 2))),
    (date(2026, 1, 10), (2025, 53, date(2025, 12, 28), date(2026, 1, 3))),
])
def test_semana_referencia(data, esperado):
    s = semana_referencia(data)
    assert (s["ano"], s["semana"], s["inicio"], s["fim"]) == esperado


def test_nivel_alerta():
    n = nivel_alerta(pd.Series([1, 5, 9, 1, 0]), pd.Series([2, 2, 2, 0, 0]), pd.Series([8, 8, 8, 0, 0]))
    assert n.tolist() == ["abaixo", "dentro", "acima", "acima", "dentro"]


def test_data_referencia_usa_a_ultima_notificacao(monkeypatch):
    monkeypatch.setattr(cq, "tem_dados", lambda a: True)
    monkeypatch.setattr(servicos, "data_dos_arquivos", lambda a: date(2026, 11, 20))
    monkeypatch.setattr(cq, "ultima_notificacao", lambda a: date(2026, 9, 15))
    assert data_referencia("DENG") == date(2026, 9, 15)
    monkeypatch.setattr(cq, "ultima_notificacao", lambda a: None)
    assert data_referencia("DENG") == date(2026, 11, 20)


def test_contagem_do_alerta_exclui_so_descartados():
    df = pd.DataFrame({"ano": 2026, "situacao": ["Confirmado", "Descartado", "Em aberto/Ign.", "Inconclusivo",
                                                 "Outra classificação", "Notificado"]})
    con = duckdb.connect()
    con.register("df", df)
    w, p = cq.Filtro("DENG", 2026, 2026, contagem="provaveis").where()
    assert con.execute(f"SELECT count(*) FROM df WHERE {w}", p).fetchone()[0] == 5


def test_semana_coberta():
    s = semana_referencia(date(2021, 1, 6))
    assert not semana_coberta(s, date(2021, 1, 6), [2020]) and semana_coberta(s, date(2021, 1, 6), [2020, 2021])
    s = semana_referencia(date(2026, 11, 12))
    assert semana_coberta(s, date(2026, 11, 12), [2026])


class _Mundo:
    """Dados sintéticos no lugar das consultas: {cod6: uf}, casos por (cod6, ano_epi, sem) e anos baixados por UF."""

    def __init__(self, mp, data, muns, casos, baixados):
        self.chamadas = []
        mp.setattr(servicos, "data_referencia", lambda a: data)
        mp.setattr(cq, "municipios_da_uf", lambda ufs: pd.DataFrame(
            [(c, f"M{c}", u) for c, u in muns.items() if not ufs or u in ufs], columns=["cod6", "municipio", "uf"]))
        mp.setattr(cq, "anos_notificacao_cobertos", lambda ag, ufs: baixados[ufs[0]])
        # chave (cod6, ano_epi, sem) ou (cod6, ano_epi, sem, ano de notificação); sem o último, é o ano_epi
        linhas = pd.DataFrame([(k[0], k[1], k[2], k[3] if len(k) > 3 else k[1], n) for k, n in casos.items()],
                              columns=["cod6", "ano_epi", "sem_epi", "ano", "casos"]).astype(
            {"ano_epi": int, "sem_epi": int, "ano": int, "casos": int})

        def no_filtro(f):  # como o SQL: o filtro é pelo ano de notificação
            return linhas[linhas.ano.between(f.ano_ini, f.ano_fim)]

        def por_semana(f, semanas):
            self.chamadas.append(f)
            d = no_filtro(f)
            return d[d.sem_epi.isin(semanas)].groupby(["cod6", "ano_epi", "sem_epi"], as_index=False)["casos"].sum()

        def totais(f):
            self.chamadas.append(f)
            return no_filtro(f).groupby(["cod6", "ano_epi"], as_index=False)["casos"].sum()
        mp.setattr(cq, "semana_por_municipio", por_semana)
        mp.setattr(cq, "totais_por_municipio", totais)


def _alerta(r, cod):
    return r.set_index("cod6").loc[cod]


def _hist(cod, anos, sem, valores):
    return {(cod, a, sem): v for a, v in zip(anos, valores, strict=True) if v}


def test_alerta_so_com_o_ano_da_semana_no_filtro(monkeypatch):
    _Mundo(monkeypatch, date(2026, 11, 12), {"140010": "RR"}, {}, {"RR": list(range(2018, 2027))})
    assert alerta_municipios(cq.Filtro("DENG", 2020, 2024), ("RR",))[0] is None


def test_alerta_semana_53_pega_o_ano_seguinte(monkeypatch):
    casos = _hist("140010", range(2013, 2020), 52, [0, 0, 1, 1, 1, 1, 1])
    casos[("140010", 2020, 53)] = 2
    casos[("140010", 2020, 53, 2021)] = 1   # notificado em 2021: a consulta tem que ir até 2021
    m = _Mundo(monkeypatch, date(2021, 1, 6), {"140010": "RR"}, casos, {"RR": list(range(2013, 2022))})
    s, r = alerta_municipios(cq.Filtro("DENG", 2016, 2021), ("RR",))
    assert s["semana"] == 53
    x = _alerta(r, "140010")
    assert (x.casos_semana, x.esperado_ate, x.alerta) == (3, 1, "acima") and x.q1 == 0.5
    assert m.chamadas[-1].ano_fim == 2021 and m.chamadas[-1].contagem == "provaveis"


def test_surto_localizado_muda_o_alerta_do_municipio(monkeypatch):
    anos = range(2019, 2026)
    casos = _hist("A", anos, 44, [2, 2, 20, 2, 2, 2, 2]) | _hist("B", anos, 44, [50] * 7)
    casos[("A", 2026, 44)] = casos[("B", 2026, 44)] = 20
    _Mundo(monkeypatch, date(2026, 11, 12), {"A": "RR", "B": "RR"}, casos, {"RR": list(range(2018, 2028))})
    _, r = alerta_municipios(cq.Filtro("DENG", 2026, 2026), ("RR",))
    assert (_alerta(r, "A").esperado_ate, _alerta(r, "A").alerta) == (2, "acima")   # sem 2021
    assert (_alerta(r, "B").esperado_ate, _alerta(r, "B").alerta) == (50, "abaixo")


def test_municipio_com_faixa_zero(monkeypatch):
    _Mundo(monkeypatch, date(2026, 11, 12), {"A": "RR"}, {("A", 2026, 44): 1}, {"RR": list(range(2018, 2028))})
    _, r = alerta_municipios(cq.Filtro("DENG", 2026, 2026), ("RR",))
    assert (_alerta(r, "A").alerta, _alerta(r, "A").faixa_zero) == ("acima", True)


def test_municipio_sem_casos_na_semana_com_historico(monkeypatch):
    casos = _hist("A", range(2019, 2026), 44, [1, 2, 3, 1, 2, 3, 2])
    _Mundo(monkeypatch, date(2026, 11, 12), {"A": "RR"}, casos, {"RR": list(range(2018, 2028))})
    _, r = alerta_municipios(cq.Filtro("DENG", 2026, 2026), ("RR",))
    assert (_alerta(r, "A").alerta, _alerta(r, "A").casos_semana, _alerta(r, "A").faixa_zero) == ("abaixo", 0, False)


def test_municipio_sem_historico_suficiente(monkeypatch):
    _Mundo(monkeypatch, date(2026, 11, 12), {"A": "RR"}, {("A", 2026, 44): 1}, {"RR": [2022, 2023, 2024, 2025, 2026]})
    s, r = alerta_municipios(cq.Filtro("DENG", 2026, 2026), ("RR",))
    assert s is None and r.empty
    # um município com histórico e outro sem: o sem histórico sai com alerta None
    _Mundo(monkeypatch, date(2026, 11, 12), {"A": "RR", "B": "AM"}, {},
           {"RR": list(range(2018, 2028)), "AM": [2024, 2025, 2026]})
    _, r = alerta_municipios(cq.Filtro("DENG", 2026, 2026), ("RR", "AM"))
    assert _alerta(r, "A").alerta == "dentro"
    assert r.set_index("cod6")["alerta"]["B"] is None


def test_municipio_sem_populacao_tem_alerta(monkeypatch):
    # nenhuma consulta de população é trocada: o alerta não a usa
    _Mundo(monkeypatch, date(2026, 11, 12), {"A": "RR"}, {}, {"RR": list(range(2018, 2028))})
    _, r = alerta_municipios(cq.Filtro("DENG", 2026, 2026), ("RR",))
    assert _alerta(r, "A").alerta == "dentro"


def test_municipio_fora_da_area_nao_aparece(monkeypatch):
    casos = {("130010", 2026, 44): 4}
    _Mundo(monkeypatch, date(2026, 11, 12), {"140010": "RR", "130010": "AM"}, casos, {"RR": list(range(2018, 2028))})
    _, r = alerta_municipios(cq.Filtro("DENG", 2026, 2026), ("RR",))
    assert r.cod6.tolist() == ["140010"]


def test_cobertura_pela_uf_do_municipio(monkeypatch):
    _Mundo(monkeypatch, date(2026, 11, 12), {"A": "RR", "B": "AM"}, {},
           {"RR": list(range(2018, 2027)), "AM": [2024, 2025, 2026]})
    _, r = alerta_municipios(cq.Filtro("DENG", 2026, 2026), ("AM", "RR"))
    assert r.set_index("cod6")["alerta"].to_dict() == {"A": "dentro", "B": None}


def test_semana_nao_baixada_na_uf_nao_vira_sem_alerta(monkeypatch):
    # histórico completo, mas o arquivo de 2026 não foi baixado: a semana atual não é conhecida
    _Mundo(monkeypatch, date(2026, 11, 12), {"A": "RR"}, {}, {"RR": list(range(2017, 2026))})
    _, r = alerta_municipios(cq.Filtro("DENG", 2026, 2026), ("RR",))
    assert r.set_index("cod6")["alerta"]["A"] is None


def test_cada_uf_usa_os_seus_anos_candidatos(monkeypatch):
    # RR completa: candidatos 2019-2025; AM com lacuna (sem 2023 e 2024): cobertos 2014-2021 e 2025, então
    # os 7 candidatos de AM são 2016-2021 e 2025, mais antigos que os de RR; a consulta tem que ir até 2016
    anos_rr = list(range(2018, 2027))
    anos_am = [2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2025, 2026]  # sem 2023 e 2024
    casos = _hist("R", range(2019, 2026), 44, [1] * 7)
    casos |= _hist("M", [2016, 2017, 2018, 2019, 2020], 44, [3] * 5)   # só nos anos antigos
    casos[("M", 2026, 44)] = 4
    m = _Mundo(monkeypatch, date(2026, 11, 12), {"R": "RR", "M": "AM"}, casos, {"RR": anos_rr, "AM": anos_am})
    _, r = alerta_municipios(cq.Filtro("DENG", 2026, 2026), ("AM", "RR"))
    assert m.chamadas[0].ano_ini == 2016 and m.chamadas[0].ano_fim == 2026
    assert _alerta(r, "M").esperado_ate == 3 and _alerta(r, "M").alerta == "acima"
    assert _alerta(r, "R").alerta == "abaixo"  # 0 casos contra faixa 1 a 1
