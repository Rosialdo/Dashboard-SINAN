"""scripts/painel.sh com um docker e um git falsos (anotam as chamadas num arquivo)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32" or shutil.which("bash") is None, reason="precisa de bash")

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "painel.sh"

DOCKER_FALSO = r"""#!/bin/sh
echo "$*" >> "$FALSO_LOG"
case "$*" in
  *State.Health.Status*) echo "$FALSO_SAUDE" ;;
  *State.Status*) echo running ;;
  "compose ps -q"*) echo abc123 ;;
  "image inspect"*) [ -e "$FALSO_SEM_IMAGEM" ] && exit 1 ;;
  "compose up"*) if [ -e "$FALSO_UP_FALHA" ]; then rm -f "$FALSO_UP_FALHA"; exit 1; fi ;;
esac
exit 0
"""


class Projeto:
    def __init__(self, raiz: Path) -> None:
        self.raiz = raiz
        self.log = raiz / "chamadas.log"
        self.sem_imagem = raiz / "sem_imagem"
        self.up_falha = raiz / "up_falha"
        (raiz / "scripts").mkdir()
        shutil.copy(SCRIPT, raiz / "scripts" / "painel.sh")
        bin_ = raiz / "bin"
        bin_.mkdir()
        for nome, texto in (("docker", DOCKER_FALSO), ("git", '#!/bin/sh\necho "git $*" >> "$FALSO_LOG"\nexit 0\n')):
            (bin_ / nome).write_text(texto, encoding="utf-8")
            (bin_ / nome).chmod(0o755)
        self.ambiente = {**os.environ, "PATH": f"{bin_}{os.pathsep}{os.environ['PATH']}", "FALSO_LOG": str(self.log),
                         "FALSO_SAUDE": "healthy", "FALSO_SEM_IMAGEM": str(self.sem_imagem), "FALSO_UP_FALHA": str(self.up_falha)}

    def env(self, texto: str = "SINAN_HOSTS=painel.exemplo.br\n") -> None:
        (self.raiz / ".env").write_bytes(texto.encode())

    def rodar(self, *args: str, **extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(self.raiz / "scripts" / "painel.sh"), *args], env={**self.ambiente, **extra},
                              capture_output=True, text=True, timeout=30)

    def chamadas(self) -> list[str]:
        return self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []


def _saida(r: subprocess.CompletedProcess) -> str:
    return r.stdout + r.stderr


def _em_ordem(linhas: list[str], trechos: list[str]) -> bool:
    i = 0
    for linha in linhas:
        if i < len(trechos) and trechos[i] in linha:
            i += 1
    return i == len(trechos)


@pytest.fixture
def projeto(tmp_path):
    return Projeto(tmp_path)


def test_recusa_sem_env(projeto):
    r = projeto.rodar("status")
    assert r.returncode == 1
    assert "cp .env.exemplo .env" in _saida(r)
    assert not [c for c in projeto.chamadas() if c.startswith("compose")]


def test_ajuda_sem_env(projeto):
    r = projeto.rodar("ajuda")
    assert r.returncode == 0
    for sub in ("status", "iniciar", "parar", "reiniciar", "logs", "atualizar-dados", "implantar"):
        assert sub in r.stdout


def test_subcomando_desconhecido(projeto):
    projeto.env()
    r = projeto.rodar("voar")
    assert r.returncode == 2
    assert "atualizar-dados" in _saida(r)


def test_status_saudavel_sai_0(projeto):
    projeto.env()
    r = projeto.rodar("status")
    assert r.returncode == 0, _saida(r)


def test_status_painel_fora_do_ar(projeto):
    projeto.env()
    r = projeto.rodar("status", FALSO_SAUDE="unhealthy")
    assert r.returncode == 1
    assert "fora do ar" in _saida(r)


def test_atualizar_dados_repassa_forcar(projeto):
    projeto.env()
    assert projeto.rodar("atualizar-dados", "--forcar").returncode == 0
    assert "compose run --rm -T atualizar --forcar" in projeto.chamadas()
    assert projeto.rodar("atualizar-dados", "--anos", "2020").returncode == 2


def test_atualizar_dados_sem_imagem(projeto):
    projeto.env()
    projeto.sem_imagem.touch()
    r = projeto.rodar("atualizar-dados")
    assert r.returncode == 1
    assert "scripts/painel.sh iniciar" in _saida(r)
    assert not [c for c in projeto.chamadas() if c.startswith("compose run")]


def test_implantar_volta_a_imagem_anterior(projeto):
    projeto.env("SINAN_HOSTS=painel.exemplo.br\nSINAN_RAMO=develop\n")
    projeto.up_falha.touch()
    r = projeto.rodar("implantar")
    assert r.returncode == 1
    assert "versão anterior" in _saida(r)
    chamadas = projeto.chamadas()
    assert _em_ordem(chamadas, ["pull --ff-only origin develop", "tag sinan-painel:atual sinan-painel:anterior",
                                "compose build", "tag sinan-painel:anterior sinan-painel:atual"])
    assert not [c for c in chamadas if "image prune" in c]


def test_implantar_limpa_imagens_quando_da_certo(projeto):
    projeto.env('SINAN_HOSTS=painel.exemplo.br\r\nSINAN_RAMO="develop"\r\n')
    r = projeto.rodar("implantar")
    assert r.returncode == 0, _saida(r)
    chamadas = projeto.chamadas()
    assert any("pull --ff-only origin develop" in c for c in chamadas)
    assert chamadas[-1] == "image prune -f"


def test_implantar_recusa_ramo_estranho(projeto):
    projeto.env("SINAN_HOSTS=painel.exemplo.br\nSINAN_RAMO=teste\n")
    r = projeto.rodar("implantar")
    assert r.returncode == 1
    assert "'teste'" in _saida(r)
    assert not [c for c in projeto.chamadas() if "pull" in c]
