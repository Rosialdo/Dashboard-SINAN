import pandas as pd

from sinan import consultas as cq
from sinan import processar
from sinan.api.servicos import anos_do_canal, anos_epi_cobertos, faixa_esperada


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
