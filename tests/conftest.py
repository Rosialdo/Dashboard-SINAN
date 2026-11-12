"""Ambiente de teste: uma pasta de dados temporária montada a partir da amostra
real ``fixtures/ACBIBR06.dbc`` (acidentes com material biológico, 2006).

Todos os caminhos de ``dados/`` são redirecionados para essa pasta, então os
testes nunca tocam nos dados baixados no computador.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from sinan import config, consultas, download, processar, web

AMOSTRA = Path(__file__).parent / "fixtures" / "ACBIBR06.dbc"
UFS_TESTE = ["PR", "SP"]


def _redirecionar(mp: pytest.MonkeyPatch, raiz: Path) -> None:
    caminhos = {
        "PASTA_DADOS": raiz,
        "PASTA_BRUTOS": raiz / "brutos",
        "PASTA_PARQUET": raiz / "parquet",
        "ARQ_INVENTARIO": raiz / "inventario.json",
        "ARQ_LISTAGEM_FTP": raiz / "listagem_ftp.json",
        "ARQ_CONFIG": raiz / "configuracao.json",
    }
    for modulo in (config, processar, consultas, download, web):
        for nome, valor in caminhos.items():
            if hasattr(modulo, nome):
                mp.setattr(modulo, nome, valor)


@pytest.fixture(scope="session")
def dados_teste(tmp_path_factory):
    """Processa a amostra (só PR e SP) e devolve a pasta de dados de teste."""
    raiz = tmp_path_factory.mktemp("dados")
    with pytest.MonkeyPatch.context() as mp:
        _redirecionar(mp, raiz)
        (raiz / "brutos").mkdir()
        dbc = raiz / "brutos" / AMOSTRA.name
        shutil.copy(AMOSTRA, dbc)
        info = {"arquivo": AMOSTRA.name, "situacao": "final", "tamanho": AMOSTRA.stat().st_size, "data_ftp": "01-01-07"}
        n = processar.processar_dbc(dbc, "ACBI", 2006, UFS_TESTE, info)
        (raiz / "configuracao.json").write_text(
            json.dumps({**config.CONFIG_PADRAO, "ufs": UFS_TESTE, "agravos": ["ACBI"], "anos": [2006]}),
            encoding="utf-8")
        web._limpar_cache()
        yield {"raiz": raiz, "registros": n}
        web._limpar_cache()


@pytest.fixture
def cliente(dados_teste):
    from starlette.testclient import TestClient

    with TestClient(web.app, base_url="http://localhost:8501") as c:
        yield c
