"""Caminhos e configurações do projeto."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

PASTA_REFERENCIA = RAIZ / "referencia"
PASTA_TABNET = PASTA_REFERENCIA / "tabnet"
ARQ_MUNICIPIOS = PASTA_REFERENCIA / "municipios.csv"
ARQ_POPULACAO = PASTA_REFERENCIA / "populacao.csv"
ARQ_MAPA = PASTA_REFERENCIA / "municipios.geojson"



def _pasta_dados(ambiente: Mapping[str, str]) -> Path:
    """Pasta dos dados: ``SINAN_DADOS`` ou ``dados/`` dentro do projeto."""
    return Path(ambiente["SINAN_DADOS"]) if ambiente.get("SINAN_DADOS") else RAIZ / "dados"


def publico() -> bool:
    """Modo publicado (site aberto, só leitura). Lido só ao criar o servidor."""
    return os.environ.get("SINAN_MODO", "").strip().lower() == "publico"


def hosts_publicos() -> set[str]:
    """Domínios aceitos no modo publicado (``SINAN_HOSTS``, separados por vírgula, sem porta)."""
    hosts = {h.strip().lower() for h in os.environ.get("SINAN_HOSTS", "").split(",") if h.strip()}
    com_porta = [h for h in hosts if ":" in h]
    if com_porta:
        raise ValueError(f"SINAN_HOSTS não aceita porta: {', '.join(sorted(com_porta))}")
    return hosts


PASTA_DADOS = _pasta_dados(os.environ)
PASTA_BRUTOS = PASTA_DADOS / "brutos"        # .dbc baixados (apagados depois, por padrão)
PASTA_PARQUET = PASTA_DADOS / "parquet"      # dados prontos para o dashboard
ARQ_INVENTARIO = PASTA_DADOS / "inventario.json"
ARQ_LISTAGEM_FTP = PASTA_DADOS / "listagem_ftp.json"
ARQ_CONFIG = PASTA_DADOS / "configuracao.json"

FTP_HOST = "ftp.datasus.gov.br"
FTP_PASTAS = {
    "final": "/dissemin/publicos/SINAN/DADOS/FINAIS",
    "preliminar": "/dissemin/publicos/SINAN/DADOS/PRELIM",
}

UFS = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
    "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR",
    "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}
UF_COD = {sigla: cod for cod, sigla in UFS.items()}
AMAZONIA_LEGAL = {"AC", "AM", "AP", "MA", "MT", "PA", "RO", "RR", "TO"}

_ANO_ATUAL = date.today().year
CONFIG_PADRAO = {
    "ufs": ["RR"],
    "agravos": ["DENG", "CHIK", "ZIKA"],
    "anos": list(range(_ANO_ATUAL - 5, _ANO_ATUAL + 1)),
    "manter_brutos": False,
}


def carregar_config() -> dict:
    cfg = dict(CONFIG_PADRAO)
    try:
        cfg.update(json.loads(ARQ_CONFIG.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return cfg


def salvar_config(cfg: dict) -> None:
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    ARQ_CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
