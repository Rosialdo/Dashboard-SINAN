"""API do dashboard e proteção do servidor local (sinan/web.py)."""

import pytest
from starlette.testclient import TestClient

from sinan import web


def test_pagina_inicial(cliente):
    r = cliente.get("/")
    assert r.status_code == 200 and "<html" in r.text


def test_meta(cliente):
    d = cliente.get("/api/meta").json()
    assert [a["codigo"] for a in d["agravos"]] == ["ACBI"]
    assert d["agravos"][0]["anos"] == [2006]
    assert set(d["ufs"]) == {"PR", "SP"}


@pytest.mark.parametrize("rota", ["visao", "mapa", "perfil"])
def test_paineis(cliente, dados_teste, rota):
    r = cliente.get(f"/api/{rota}?agravo=ACBI")
    assert r.status_code == 200, r.text
    ind = r.json()["indicadores"]
    assert ind["notificacoes"] > 0
    assert ind["incidencia"] is not None


def test_registros_paginados(cliente, dados_teste):
    p0 = cliente.get("/api/registros?agravo=ACBI&pagina=0").json()
    p1 = cliente.get("/api/registros?agravo=ACBI&pagina=1").json()
    assert p0["total"] > 0 and p0["por_pagina"] == 50
    assert len(p0["linhas"]) == min(50, p0["total"])
    assert p0["linhas"] != p1["linhas"]


def test_variaveis(cliente):
    lista = cliente.get("/api/variaveis?agravo=ACBI").json()
    assert lista
    d = cliente.get(f"/api/variavel?agravo=ACBI&id={lista[0]['id']}").json()
    assert d["valores"]


@pytest.mark.parametrize("formato", ["csv", "municipios", "xlsx"])
def test_exportar(cliente, formato):
    r = cliente.get(f"/api/exportar?agravo=ACBI&formato={formato}")
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]


def test_erros_amigaveis(cliente):
    r = cliente.get("/api/visao?agravo=DENG")  # sem dados baixados
    assert r.status_code == 400 and "Não há dados" in r.json()["erro"]
    r = cliente.get("/api/visao?agravo=DE'NG")
    assert r.status_code == 400 and "inválido" in r.json()["erro"]
    r = cliente.get("/api/visao?agravo=ACBI&ini=abc")
    assert r.status_code == 400
    r = cliente.get("/api/exportar?agravo=ACBI&formato=exe")
    assert r.status_code == 400


def test_conversao_json_de_nat():
    import pandas as pd
    assert web._conv(pd.NaT) is None
    assert web._conv(pd.Timestamp("2024-01-02")) == "2024-01-02"


# ---------------------------------------------------------------- segurança
def test_bloqueia_host_externo(dados_teste):
    with TestClient(web.app, base_url="http://site-malicioso.com") as c:
        assert c.get("/api/meta").status_code == 403


def test_bloqueia_origem_externa(cliente):
    r = cliente.get("/api/meta", headers={"Origin": "http://site-malicioso.com"})
    assert r.status_code == 403


def test_post_precisa_ser_json(cliente):
    # um formulário de outro site só consegue mandar text/plain ou form sem pedir permissão
    for tipo in ("text/plain", "application/x-www-form-urlencoded", "multipart/form-data"):
        r = cliente.post("/api/dados/remover", content='{"itens": []}', headers={"Content-Type": tipo})
        assert r.status_code == 403, tipo


def test_post_da_propria_pagina_funciona(cliente):
    r = cliente.post("/api/dados/remover", json={"itens": []},
                     headers={"Origin": "http://localhost:8501"})
    assert r.status_code == 200


@pytest.mark.parametrize("item", ["../../etc_2020", "ACBI_20x6", "acbi/../x_2006", 123])
def test_remover_valida_itens(cliente, item):
    r = cliente.post("/api/dados/remover", json={"itens": [item]})
    assert r.status_code == 400


def test_atualizar_valida_entrada(cliente):
    assert cliente.post("/api/dados/atualizar", json={"agravos": ["DENG"], "anos": [2024], "ufs": ["XX"]}).status_code == 400
    assert cliente.post("/api/dados/atualizar", json={"agravos": ["DE'NG"], "anos": [2024], "ufs": ["RR"]}).status_code == 400
    assert cliente.post("/api/dados/atualizar", json={"agravos": [], "anos": [], "ufs": []}).status_code == 400
