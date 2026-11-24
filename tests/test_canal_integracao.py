"""Canal endêmico com SQL real (DuckDB lendo Parquet sintéticos de vários anos de notificação)."""

import json
from datetime import date

import pandas as pd
import pytest
from conftest import _redirecionar

from sinan import consultas as cq
from sinan.api import cache, servicos


def _escrever(raiz, ano, linhas):
    """Um Parquet por ano de notificação; ``linhas`` = [(ano_epi, sem_epi, quantidade[, município[, situação]])]."""
    padrao = ("140010", "Confirmado")
    reg = [dict(ano=ano, ano_epi=ae, sem_epi=se, uf_res="RR", uf_not="RR", mun_res=mun, mun_not=mun,
                confirmado=sit == "Confirmado", situacao=sit, sexo="Feminino", faixa_etaria="20 a 29 anos")
           for ae, se, n, mun, sit in (tuple(lin) + padrao[len(lin) - 3:] for lin in linhas)
           for _ in range(n)]
    pasta = raiz / "parquet" / "DENG"
    pasta.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(reg).to_parquet(pasta / f"DENG_{ano}.parquet")


def test_canal_com_parquet_de_varios_anos(tmp_path, monkeypatch):
    _redirecionar(monkeypatch, tmp_path)
    cache.limpar()
    anos = [2015, 2016, 2017, 2018, 2020, 2021, 2022, 2023, 2024, 2025, 2026]  # 2019 não baixado
    for a in anos:
        _escrever(tmp_path, a, [(a, 10, 4)] + ([(a - 1, 52, 2)] if a in (2021, 2022, 2023) else []))
    (tmp_path / "inventario.json").write_text(json.dumps(
        {f"DENG_{a}": {"agravo": "DENG", "ano": a, "ufs": ["RR"]} for a in anos}), encoding="utf-8")
    try:
        canal, motivo = servicos.canal_endemico(cq.Filtro("DENG", 2026, 2026), ("RR",))
        assert motivo is None and canal["ano_coberto"] is True  # o arquivo de notificação de 2026 está baixado
        sem = {s["sem_epi"]: s for s in canal["semanas"]}
        # 2018 (sem o arquivo de 2019) e 2015/2016 (fora dos 7 mais recentes) não entram
        assert canal["anos"] == [2017, 2020, 2021, 2022, 2023, 2024, 2025]
        assert canal["excluidos"] == []  # 2020 a 2022 têm 6 casos, limite 1,5 x 4 = 6: não passa
        assert sem[10]["q1"] == sem[10]["mediana"] == sem[10]["q3"] == 4  # nenhum zero de ano não coberto
        # tardios (2 casos na semana 52) vêm dos arquivos de 2021, 2022 e 2023: semana 52 = 0,0,0,0,2,2,2
        tardios = cq.por_semana(cq.Filtro("DENG", 2017, 2026))
        assert tardios[(tardios.ano_epi == 2021) & (tardios.sem_epi == 52)]["casos"].tolist() == [2]
        assert (sem[52]["q1"], sem[52]["mediana"], sem[52]["q3"]) == (0, 0, 2)  # posições 1,5 / 3 / 4,5
    finally:
        cache.limpar()


def test_alerta_com_parquet_de_varios_anos(tmp_path, monkeypatch):
    _redirecionar(monkeypatch, tmp_path)
    cache.limpar()
    a, b = cq.municipios_da_uf(["RR"])["cod6"].iloc[:2]
    anos = list(range(2019, 2027))
    for ano in anos:
        linhas = [(ano, 44, 1, a, "Confirmado")]
        if ano == 2026:  # 4 confirmados + 1 em aberto contam (5); o descartado fica fora
            linhas = [(ano, 44, 4, a, "Confirmado"), (ano, 44, 1, a, "Em aberto/Ign."), (ano, 44, 1, a, "Descartado")]
        _escrever(tmp_path, ano, linhas)
    (tmp_path / "inventario.json").write_text(json.dumps(
        {f"DENG_{x}": {"agravo": "DENG", "ano": x, "ufs": ["RR"]} for x in anos}), encoding="utf-8")
    monkeypatch.setattr(servicos, "data_referencia", lambda ag: date(2026, 11, 12))
    try:
        s, r = servicos.alerta_municipios(cq.Filtro("DENG", 2026, 2026), ("RR",))
        r = r.set_index("cod6")
        assert (s["ano"], s["semana"]) == (2026, 44)
        assert r.loc[a, ["casos_semana", "q1", "esperado_ate"]].tolist() == [5, 1, 1]
        assert r.loc[a, "alerta"] == "acima" and not r.loc[a, "faixa_zero"]
        assert r.loc[b, ["casos_semana", "esperado_ate"]].tolist() == [0, 0]
        assert r.loc[b, "alerta"] == "dentro" and r.loc[b, "faixa_zero"]
    finally:
        cache.limpar()


@pytest.mark.parametrize("data, sem, ano_epi, anos, hist_sem, atual", [
    # semana 1 de 2025 (29/12/2024 a 04/01/2025): 2 fichas notificadas em dezembro de 2024 e 3 em janeiro
    (date(2025, 1, 8), 1, 2025, range(2018, 2026), 1, {2024: 2, 2025: 3}),
    # semana 53 de 2020 (27/12/2020 a 02/01/2021): 2 fichas notificadas em 2020 e 1 em 2021
    (date(2021, 1, 6), 53, 2020, range(2013, 2022), 52, {2020: 2, 2021: 1}),
])
def test_alerta_soma_as_fichas_da_semana_nos_dois_anos(tmp_path, monkeypatch, data, sem, ano_epi, anos, hist_sem, atual):
    _redirecionar(monkeypatch, tmp_path)
    cache.limpar()
    a = cq.municipios_da_uf(["RR"])["cod6"].iloc[0]
    for ano in anos:
        linhas = [(ano, hist_sem, 1, a, "Confirmado")] if ano < ano_epi else []
        if ano in atual:
            linhas.append((ano_epi, sem, atual[ano], a, "Confirmado"))
        _escrever(tmp_path, ano, linhas)
    (tmp_path / "inventario.json").write_text(json.dumps(
        {f"DENG_{x}": {"agravo": "DENG", "ano": x, "ufs": ["RR"]} for x in anos}), encoding="utf-8")
    monkeypatch.setattr(servicos, "data_referencia", lambda ag: data)
    try:
        s, r = servicos.alerta_municipios(cq.Filtro("DENG", ano_epi - 1, data.year), ("RR",))
        assert (s["ano"], s["semana"]) == (ano_epi, sem)
        x = r.set_index("cod6").loc[a]
        assert (x.casos_semana, x.esperado_ate, x.alerta) == (3 if sem == 53 else 5, 1, "acima")
    finally:
        cache.limpar()
