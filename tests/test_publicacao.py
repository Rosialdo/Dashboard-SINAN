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
