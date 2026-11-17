"""Arquivos de implantação com Docker (Dockerfile, compose, scripts do servidor)."""

from __future__ import annotations

from pathlib import Path

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
