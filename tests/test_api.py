"""API do dashboard e proteção do servidor local (sinan/api/)."""

import pandas as pd
import pytest
from conftest import UFS_TESTE
from starlette.testclient import TestClient

from sinan import consultas as cq
from sinan.api import app
from sinan.api.respostas import _converter


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


def test_mapa_traz_incidencia_suavizada(cliente, dados_teste):
    muns = cliente.get("/api/mapa?agravo=ACBI").json()["municipios"]
    com_pop = [m for m in muns if m["populacao"]]
    assert com_pop and all(m["incidencia_suavizada"] is not None for m in com_pop)
    assert all(m["incidencia_suavizada"] >= 0 for m in com_pop)


@pytest.mark.parametrize("extra", ["sexo=Masculino", "faixa=20-29", "local=not", "mun={cod}"])
def test_mapa_sem_suavizada_quando_filtro_nao_combina(cliente, dados_teste, extra):
    cod = cliente.get("/api/mapa?agravo=ACBI").json()["municipios"][0]["cod6"]
    muns = cliente.get(f"/api/mapa?agravo=ACBI&{extra.format(cod=cod)}").json()["municipios"]
    assert muns and all(m["incidencia_suavizada"] is None for m in muns)
    assert any(m["casos"] > 0 for m in muns)


@pytest.mark.parametrize("extra", ["sexo=Masculino", "faixa=20-29", "local=not"])
def test_mapa_sem_incidencia_quando_filtro_nao_combina(cliente, dados_teste, extra):
    muns = cliente.get(f"/api/mapa?agravo=ACBI&{extra}").json()["municipios"]
    assert muns and all(m["incidencia"] is None for m in muns)
    assert any(m["casos"] > 0 for m in muns)


@pytest.mark.parametrize("rota", ["mapa", "visao"])
def test_topo_sem_incidencia_na_contagem_por_notificacao(cliente, dados_teste, rota):
    ind = cliente.get(f"/api/{rota}?agravo=ACBI&local=not").json()["indicadores"]
    assert ind["notificacoes"] > 0 and ind["incidencia"] is None


def test_mapa_com_municipio_mantem_incidencia_bruta(cliente, dados_teste):
    cod = next(m["cod6"] for m in cliente.get("/api/mapa?agravo=ACBI").json()["municipios"] if m["populacao"])
    d = cliente.get(f"/api/mapa?agravo=ACBI&mun={cod}").json()
    muns = d["municipios"]
    assert muns and all(m["incidencia"] is not None and m["incidencia_suavizada"] is None for m in muns)
    assert d["indicadores"]["incidencia"] is not None  # o topo também continua com município escolhido


@pytest.fixture
def cache_limpo():
    from sinan.api import cache
    cache.limpar()
    yield
    cache.limpar()  # não deixa a tabela com população zero para os testes seguintes


def test_incidencia_bruta_sem_populacao_vira_vazio(cliente, dados_teste, cache_limpo, monkeypatch):
    from sinan import consultas as cq
    original = cq._q

    def pop_zero(sql, params=None):  # toda população 0: nenhuma taxa pode ser calculada
        df = original(sql, params)
        if "FROM pop" in sql and "pa" in df.columns:
            df[["populacao", "pa"]] = 0
        return df

    monkeypatch.setattr(cq, "_q", pop_zero)
    r = cliente.get("/api/mapa?agravo=ACBI")
    assert r.status_code == 200 and "Infinity" not in r.text
    muns = r.json()["municipios"]
    assert all(m["incidencia"] is None and m["incidencia_suavizada"] is None for m in muns)


def test_exportar_municipios_igual_ao_mapa(cliente, dados_teste):
    import io

    api = pd.DataFrame(cliente.get("/api/mapa?agravo=ACBI").json()["municipios"])
    r = cliente.get("/api/exportar?agravo=ACBI&formato=municipios")
    csv = pd.read_csv(io.BytesIO(r.content), sep=";", decimal=",", encoding="utf-8-sig")
    assert "Incidência suavizada por 100 mil hab./ano" in csv.columns
    assert list(csv["Incidência suavizada por 100 mil hab./ano"].round(6)) == \
        pytest.approx(list(api["incidencia_suavizada"].astype(float).round(6)), nan_ok=True)


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
    assert _converter(pd.NaT) is None
    assert _converter(pd.Timestamp("2024-01-02")) == "2024-01-02"


# ---------------------------------------------------------------- segurança
def test_bloqueia_host_externo(dados_teste):
    with TestClient(app, base_url="http://site-malicioso.com") as c:
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


# ---------------------------------------------------------------- FastAPI
def test_documentacao_da_api(cliente):
    esquema = cliente.get("/api/openapi.json").json()
    rotas = set(esquema["paths"])
    assert {"/api/meta", "/api/visao", "/api/mapa", "/api/perfil", "/api/variaveis", "/api/variavel",
            "/api/registros", "/api/exportar", "/api/dados", "/api/dados/atualizar", "/api/dados/remover"} <= rotas
    assert "/" not in rotas  # a página da interface não faz parte da API
    assert cliente.get("/api/docs").status_code == 200


@pytest.mark.parametrize("url", [
    "/api/visao?agravo=ACBI&contagem=xyz",
    "/api/visao?agravo=ACBI&local=outro",
    "/api/registros?agravo=ACBI&pagina=-1",
    "/api/variavel?agravo=ACBI&id=abc",
])
def test_validacao_em_portugues(cliente, url):
    r = cliente.get(url)
    assert r.status_code == 400
    assert r.json()["erro"].startswith("Parâmetro inválido.")


def test_corpo_invalido_no_post(cliente):
    r = cliente.post("/api/dados/atualizar", json={"agravos": ["DENG"], "anos": ["dois mil"], "ufs": ["RR"]})
    assert r.status_code == 400 and "anos" in r.json()["erro"]
    r = cliente.post("/api/dados/remover", content="isto não é json", headers={"Content-Type": "application/json"})
    assert r.status_code == 400



def test_paginas_sem_repeticao_nem_falta(dados_teste):
    """Muitos registros têm a mesma data; sem desempate na ordenação, linhas se
    repetiam entre as páginas e outras nunca apareciam."""

    from sinan import consultas as cq
    f = cq.Filtro("ACBI", 2006, 2006, contagem="todas")
    completo = cq.registros(f, limite=None).reset_index(drop=True)
    paginas = pd.concat([cq.registros(f, limite=50, inicio=i) for i in range(0, len(completo), 50)],
                        ignore_index=True)
    pd.testing.assert_frame_equal(paginas, completo)


def test_mesma_resposta_sempre(cliente):
    from sinan.api import cache
    respostas = set()
    for _ in range(3):
        cache.limpar()
        respostas.add(cliente.get("/api/registros?agravo=ACBI&contagem=todas&pagina=3").content)
        respostas.add(cliente.get("/api/perfil?agravo=ACBI").content)
    assert len(respostas) == 2  # uma resposta de registros e uma de perfil, sempre iguais


# ---------------------------------------------------------------- contorno do mapa
def test_geo_recusa_uf_desconhecida(cliente):
    r = cliente.get("/api/geo?ufs=ZZ")
    assert r.status_code == 400 and "UF" in r.json()["erro"]


def test_geo_memoria_limitada(cliente):
    from itertools import combinations

    from sinan import config
    from sinan.api.rotas import meta
    pares = list(combinations(sorted(config.UFS.values()), 2))[:50]
    for a, b in pares:
        assert cliente.get(f"/api/geo?ufs={a},{b}").status_code == 200
    assert len(meta._geo) <= 28


def test_geo_filtra_as_ufs_pedidas(cliente):
    feats = cliente.get("/api/geo?ufs=PR").json()["features"]
    assert feats and all(f["properties"]["cod6"].startswith("41") for f in feats)


def test_visao_sem_historico_nao_tem_canal(cliente, dados_teste):
    d = cliente.get("/api/visao", params={"agravo": "ACBI", "ini": 2006, "fim": 2006}).json()
    assert d["canal"] is None  # a amostra só tem 2006


def test_visao_traz_canal(cliente, dados_teste, cache_limpo, monkeypatch):
    # totais 8..12 (mediana 10, limite 15): nenhum ano anterior é epidêmico
    hist = pd.DataFrame({"ano_epi": list(range(1999, 2007)), "sem_epi": 10,
                         "casos": [8, 9, 10, 11, 12, 10, 9, 30]})
    monkeypatch.setattr(cq, "por_semana", lambda f: hist[hist.ano_epi.between(f.ano_ini, f.ano_fim)])
    recebido = []
    monkeypatch.setattr(cq, "anos_notificacao_cobertos",
                        lambda agravo, ufs: recebido.append(ufs) or list(range(1999, 2007)))
    d = cliente.get("/api/visao", params={"agravo": "ACBI", "ini": 2006, "fim": 2006}).json()
    assert recebido and recebido[0] and set(recebido[0]) == set(UFS_TESTE)  # as UFs da área
    assert d["canal"]["ano"] == 2006 and d["canal"]["anos"] == list(range(1999, 2006))
    assert d["canal"]["excluidos"] == []
    assert next(s for s in d["canal"]["semanas"] if s["sem_epi"] == 10)["mediana"] == 10


def test_canal_usa_os_7_anos_cobertos_mais_recentes(cliente, dados_teste, cache_limpo, monkeypatch):
    # cobertura 1995-1997 e 2001-2007: anos epidemiológicos 1995, 1996, 2001..2006
    hist = pd.DataFrame({"ano_epi": [1995, 1996, *range(2001, 2007)], "sem_epi": 10, "casos": 10})
    pedidos = []

    def por_semana(f):
        pedidos.append(f)
        return hist[hist.ano_epi.between(f.ano_ini, f.ano_fim)]
    monkeypatch.setattr(cq, "por_semana", por_semana)
    monkeypatch.setattr(cq, "anos_notificacao_cobertos",
                        lambda agravo, ufs: [1995, 1996, 1997, *range(2001, 2008)])
    d = cliente.get("/api/visao", params={"agravo": "ACBI", "ini": 2006, "fim": 2006}).json()
    assert d["canal"]["anos"] == [1995, 1996, 2001, 2002, 2003, 2004, 2005]
    s10 = next(s for s in d["canal"]["semanas"] if s["sem_epi"] == 10)
    assert s10["q1"] == s10["mediana"] == s10["q3"] == 10
    assert any(f.ano_ini == 1995 for f in pedidos)
