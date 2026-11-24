from sinan import consultas as cq
from sinan import processar
from sinan.api.servicos import anos_epi_cobertos


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
