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
