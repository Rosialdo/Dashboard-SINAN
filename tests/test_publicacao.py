"""Modo publicado (SINAN_MODO=publico): domínio configurável e só leitura."""

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from sinan import config
from sinan.api import criar_app

DOMINIO = "painel.exemplo.br"


@pytest.fixture
def cliente_publico(dados_teste, monkeypatch):
    monkeypatch.setenv("SINAN_MODO", "publico")
    monkeypatch.setenv("SINAN_HOSTS", DOMINIO)
    with TestClient(criar_app(), base_url=f"https://{DOMINIO}") as c:
        yield c


def test_publico_aceita_dominio_configurado(cliente_publico):
    r = cliente_publico.get("/api/meta", headers={"Origin": f"https://{DOMINIO}"})
    assert r.status_code == 200, r.text


def test_publico_recusa_outro_dominio(cliente_publico):
    assert cliente_publico.get("/api/meta", headers={"Host": "outro.br"}).status_code == 403


def test_publico_aceita_host_local_do_proxy(cliente_publico):
    r = cliente_publico.get("/api/meta", headers={"Host": "127.0.0.1:8501", "Origin": f"https://{DOMINIO}"})
    assert r.status_code == 200, r.text


def test_publico_recusa_post(cliente_publico):
    assert cliente_publico.post("/api/meta", json={}).status_code == 403


def test_publico_sem_hosts_nao_sobe(monkeypatch):
    monkeypatch.setenv("SINAN_MODO", "publico")
    monkeypatch.setenv("SINAN_HOSTS", "")
    with pytest.raises(RuntimeError, match="SINAN_HOSTS"):
        criar_app()


def test_hosts_normalizados(monkeypatch):
    monkeypatch.setenv("SINAN_HOSTS", " Painel.Exemplo.BR , ,b.br")
    assert config.hosts_publicos() == {"painel.exemplo.br", "b.br"}
    monkeypatch.setenv("SINAN_HOSTS", "a.br:443")
    with pytest.raises(ValueError):
        config.hosts_publicos()


def test_local_continua_recusando_dominio_de_fora(dados_teste, monkeypatch):
    monkeypatch.delenv("SINAN_MODO", raising=False)
    with TestClient(criar_app(), base_url=f"https://{DOMINIO}") as c:
        assert c.get("/api/meta").status_code == 403


def test_pasta_de_dados_pelo_ambiente():
    assert config._pasta_dados({"SINAN_DADOS": "/srv/x"}) == Path("/srv/x")
    assert config._pasta_dados({}) == config.RAIZ / "dados"


# ---------------------------------------------------------------- só leitura, sem fichas
def test_publico_sem_rotas_de_administracao(cliente_publico):
    assert cliente_publico.get("/api/dados").status_code == 404
    assert cliente_publico.get("/api/dados/status").status_code == 404


@pytest.mark.parametrize("url", ["/api/registros?agravo=ACBI", "/api/exportar?agravo=ACBI&formato=xlsx",
                                 "/api/exportar?agravo=ACBI&formato=csv", "/api/exportar?agravo=ACBI&formato=csv_completo"])
def test_publico_sem_fichas(cliente_publico, url):
    r = cliente_publico.get(url)
    assert r.status_code == 403
    assert r.json()["erro"] == "Não disponível na versão publicada do painel."


def test_publico_exporta_resumo_por_municipio(cliente_publico):
    r = cliente_publico.get("/api/exportar?agravo=ACBI&formato=municipios")
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]


def test_publico_sem_documentacao(cliente_publico):
    assert cliente_publico.get("/api/docs").status_code == 404
    assert cliente_publico.get("/api/openapi.json").status_code == 404


@pytest.mark.parametrize("rota", ["visao", "mapa", "perfil", "variavel"])
def test_publico_consultas_agregadas_funcionam(cliente_publico, rota):
    assert cliente_publico.get(f"/api/{rota}?agravo=ACBI").status_code == 200


def test_publico_erro_interno_sem_detalhes(dados_teste, monkeypatch):
    import re

    from sinan.api import cache, servicos

    def falha(*a, **k):
        raise RuntimeError("segredo")

    monkeypatch.setenv("SINAN_MODO", "publico")
    monkeypatch.setenv("SINAN_HOSTS", DOMINIO)
    monkeypatch.setattr(servicos, "indicadores", falha)
    cache.limpar()
    with TestClient(criar_app(), base_url=f"https://{DOMINIO}", raise_server_exceptions=False) as c:
        r = c.get("/api/visao?agravo=ACBI")
    cache.limpar()
    assert r.status_code == 500
    assert "segredo" not in r.text
    assert re.search(r"código [0-9a-f]{8}\b", r.json()["erro"])


def test_meta_informa_modo_publico(cliente_publico):
    d = cliente_publico.get("/api/meta").json()
    assert d["publico"] is True and d["telas_ocultas"] == ["dados", "atualizar"]


def test_meta_informa_modo_local(cliente):
    d = cliente.get("/api/meta").json()
    assert d["publico"] is False and d["telas_ocultas"] == []


# ---------------------------------------------------------------- variáveis sensíveis por município
@pytest.fixture
def municipio(cliente_publico):
    """Um município da amostra com casos."""
    return cliente_publico.get("/api/mapa?agravo=ACBI&contagem=todas").json()["municipios"][0]["cod6"]


def test_amostra_tem_variaveis_sensiveis(cliente_publico):
    from sinan.api import servicos
    campos = {v["campo"] for v in cliente_publico.get("/api/variaveis?agravo=ACBI").json()}
    assert campos & servicos.CAMPOS_SENSIVEIS, campos  # sem isso os testes abaixo não provariam nada


def test_publico_municipio_sem_obitos_nem_hospitalizacao(cliente_publico, municipio):
    d = cliente_publico.get(f"/api/visao?agravo=ACBI&contagem=todas&mun={municipio}").json()
    ind = d["indicadores"]
    assert ind["obitos"] is None and ind["letalidade"] is None and ind["hospitalizados"] is None
    assert ind["notificacoes"] > 0
    assert all("obitos" not in r for r in d["ano"])


def test_publico_estado_mostra_obitos(cliente_publico):
    ind = cliente_publico.get("/api/visao?agravo=ACBI&contagem=todas").json()["indicadores"]
    assert ind["obitos"] is not None


def test_publico_municipio_perfil_sem_evolucao(cliente_publico, municipio):
    d = cliente_publico.get(f"/api/perfil?agravo=ACBI&contagem=todas&mun={municipio}").json()
    assert d["evolucao"] is None and d["hospitalizado"] is None
    assert d["raca"] is not None


def test_publico_municipio_variavel_sensivel_escondida(cliente_publico, municipio):
    from sinan.api import servicos
    lista = cliente_publico.get("/api/variaveis?agravo=ACBI").json()
    sens = next(v for v in lista if v["campo"] in servicos.CAMPOS_SENSIVEIS)
    comum = next(v for v in lista if v["campo"] not in servicos.CAMPOS_SENSIVEIS)
    d = cliente_publico.get(f"/api/variavel?agravo=ACBI&contagem=todas&mun={municipio}&id={sens['id']}").json()
    assert d["valores"] == [] and "privacidade" in d["aviso"]
    assert cliente_publico.get(f"/api/variavel?agravo=ACBI&contagem=todas&mun={municipio}&id={comum['id']}").json()["valores"]
    assert cliente_publico.get(f"/api/variavel?agravo=ACBI&contagem=todas&id={sens['id']}").json()["valores"]


def test_publico_tabela_de_municipios_sem_obitos(cliente_publico):
    linhas = cliente_publico.get("/api/mapa?agravo=ACBI&contagem=todas").json()["municipios"]
    assert linhas and all("obitos" not in r for r in linhas)
    csv = cliente_publico.get("/api/exportar?agravo=ACBI&formato=municipios").content.decode("utf-8-sig")
    assert "Óbitos" not in csv.splitlines()[0]


def test_local_municipio_continua_com_tudo(cliente, municipio):
    d = cliente.get(f"/api/perfil?agravo=ACBI&contagem=todas&mun={municipio}").json()
    assert d["evolucao"] is not None and d["indicadores"]["obitos"] is not None
    assert "obitos" in cliente.get("/api/mapa?agravo=ACBI&contagem=todas").json()["municipios"][0]
