"""Arquivos de implantação com Docker (Dockerfile, compose, scripts do servidor)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


def _estagio_final() -> str:
    texto = (RAIZ / "Dockerfile").read_text(encoding="utf-8")
    return texto[texto.rindex("\nFROM ") :]


def test_imagem_final_sem_compilador_e_sem_root():
    final = _estagio_final()
    assert "USER sinan" in final
    assert "WORKDIR /app" in final
    for proibido in ("uv sync", "gcc", "build-essential"):
        assert proibido not in final


def test_imagem_usa_lock_sem_dev():
    assert "uv sync --frozen --no-dev --no-install-project" in (RAIZ / "Dockerfile").read_text(encoding="utf-8")


def test_imagem_nao_guarda_ip():
    cmd = [linha for linha in _estagio_final().splitlines() if linha.startswith("CMD")]
    assert cmd and "--no-access-log" in cmd[0]


def test_dockerignore_deixa_fora_segredos_e_dados():
    linhas = [l.strip() for l in (RAIZ / ".dockerignore").read_text(encoding="utf-8").splitlines()]
    uteis = [l for l in linhas if l and not l.startswith("#")]
    assert uteis[0] == "*"
    excecoes = {l[1:].rstrip("/") for l in uteis if l.startswith("!")}
    assert not excecoes & {".env", "dados", ".venv", ".git", "tests", "docs"}


# ---------------------------------------------------------------- compose

SEM_DOCKER = pytest.mark.skipif(shutil.which("docker") is None, reason="sem Docker")
SEM_BASH_FLOCK = pytest.mark.skipif(
    sys.platform == "win32" or not (shutil.which("bash") and shutil.which("flock")), reason="precisa de bash e flock")


def _compose_config(tmp_path: Path, env: str) -> subprocess.CompletedProcess:
    arq = tmp_path / ".env"
    arq.write_text(env, encoding="utf-8")
    ambiente = {k: v for k, v in os.environ.items() if not k.startswith("SINAN_")}
    return subprocess.run(
        ["docker", "compose", "--profile", "ferramentas", "--env-file", str(arq), "config", "--format", "json"],
        cwd=RAIZ, env=ambiente, capture_output=True, text=True)


@pytest.fixture
def compose(tmp_path):
    r = _compose_config(tmp_path, "SINAN_HOSTS=painel.exemplo.br\n")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _alvos(servico: dict) -> dict[str, str]:
    return {v["target"]: v["source"] for v in servico.get("volumes", [])}


@SEM_DOCKER
def test_compose_painel_so_na_rede_interna(compose):
    p = compose["services"]["painel"]
    assert not p.get("ports")
    assert set(p["networks"]) == {"interna"}
    assert compose["networks"]["interna"]["internal"] is True
    assert p["restart"] == "unless-stopped"
    assert p.get("mem_limit")
    assert _alvos(p)["/dados"] == "dados"
    assert any("/api/meta" in parte for parte in p["healthcheck"]["test"])
    assert p["environment"]["SINAN_MODO"] == "publico"
    assert p["environment"]["SINAN_DADOS"] == "/dados"
    assert p["environment"]["SINAN_HOSTS"] == "painel.exemplo.br"


@SEM_DOCKER
def test_compose_proxy_unica_porta_aberta(compose):
    com_portas = {nome for nome, s in compose["services"].items() if s.get("ports")}
    assert com_portas == {"proxy"}
    assert sorted(p["published"] for p in compose["services"]["proxy"]["ports"]) == ["443", "80"]


@SEM_DOCKER
def test_compose_atualizar_so_sob_demanda(compose):
    a = compose["services"]["atualizar"]
    assert a["profiles"] == ["ferramentas"]
    assert a["image"] == compose["services"]["painel"]["image"] == "sinan-painel:atual"
    assert a["pull_policy"] == "never"
    assert a["entrypoint"] == ["bash", "scripts/atualizar_servidor.sh"]
    assert _alvos(a)["/dados"] == "dados"
    assert set(a["networks"]) == {"default"}


@SEM_DOCKER
def test_compose_logs_com_rotacao(compose):
    for nome in ("painel", "atualizar", "proxy"):
        assert compose["services"][nome]["logging"]["options"] == {"max-size": "10m", "max-file": "3"}, nome


@SEM_DOCKER
def test_compose_sem_dominio_falha(tmp_path):
    r = _compose_config(tmp_path, "")
    assert r.returncode != 0
    assert "SINAN_HOSTS" in r.stderr


# ---------------------------------------------------------------- atualização

SCRIPT = RAIZ / "scripts" / "atualizar_servidor.sh"


def test_atualizacao_calcula_anos():
    texto = SCRIPT.read_text(encoding="utf-8")
    assert '--anos "$((ANO - 5))-$ANO"' in texto
    assert "flock -n" in texto
    assert "UV" not in texto


def _rodar_atualizacao(tmp_path: Path) -> subprocess.CompletedProcess:
    bin_ = tmp_path / "bin"
    bin_.mkdir(exist_ok=True)
    falso = bin_ / "python"
    falso.write_text("#!/bin/sh\necho baixando\nexit 3\n", encoding="utf-8")
    falso.chmod(0o755)
    dados = tmp_path / "dados"
    dados.mkdir(exist_ok=True)
    ambiente = {**os.environ, "PATH": f"{bin_}{os.pathsep}{os.environ['PATH']}", "SINAN_DADOS": str(dados)}
    return subprocess.run(["bash", str(SCRIPT)], env=ambiente, capture_output=True, text=True, timeout=30)


@SEM_BASH_FLOCK
def test_atualizacao_registra_fim_mesmo_com_erro(tmp_path):
    r = _rodar_atualizacao(tmp_path)
    assert r.returncode == 3, r.stderr
    assert "baixando" in r.stdout
    log = (tmp_path / "dados" / "atualizacao.log").read_text(encoding="utf-8")
    assert "início" in log
    assert "fim (código 3)" in log


@SEM_BASH_FLOCK
def test_atualizacao_recusa_execucao_dupla(tmp_path):
    (tmp_path / "dados").mkdir()
    trava = tmp_path / "dados" / ".atualizando"
    outro = subprocess.Popen(["flock", str(trava), "sleep", "5"])
    try:
        for _ in range(50):  # espera o outro processo pegar a trava
            if subprocess.run(["flock", "-n", str(trava), "true"]).returncode != 0:
                break
            time.sleep(0.05)
        r = _rodar_atualizacao(tmp_path)
    finally:
        outro.kill()
        outro.wait()
    assert r.returncode == 1
    assert "Já existe uma atualização em andamento." in r.stderr
