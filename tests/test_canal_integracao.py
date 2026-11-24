"""Canal endêmico com SQL real (DuckDB lendo Parquet sintéticos de vários anos de notificação)."""

import json

import pandas as pd
from conftest import _redirecionar

from sinan import consultas as cq
from sinan.api import cache, servicos


def _escrever(raiz, ano, linhas):
    """Um Parquet por ano de notificação; ``linhas`` = [(ano_epi, sem_epi, quantidade)]."""
    reg = [dict(ano=ano, ano_epi=ae, sem_epi=se, uf_res="RR", uf_not="RR", mun_res="140010", mun_not="140010",
                confirmado=True, situacao="Confirmado", sexo="Feminino", faixa_etaria="20 a 29 anos")
           for ae, se, n in linhas for _ in range(n)]
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
        canal = servicos.canal_endemico(cq.Filtro("DENG", 2026, 2026), ("RR",))
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
