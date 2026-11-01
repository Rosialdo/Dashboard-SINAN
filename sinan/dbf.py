"""Leitor rápido de arquivos DBF (dBase III), usado depois de descomprimir o .DBC.

Os arquivos nacionais do SINAN podem ter milhões de linhas (dengue 2024 tem
mais de 6 milhões). Em vez de ler linha a linha, este leitor mapeia o arquivo
em memória com numpy, filtra por UF em blocos e só converte para texto as
linhas que interessam.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator

import numpy as np
import pandas as pd


@dataclass
class Campo:
    nome: str
    tipo: str  # C = texto, D = data, N = número, L = lógico, ...
    tamanho: int
    offset: int  # posição dentro do registro (o byte 0 é o marcador de exclusão)


@dataclass
class CabecalhoDBF:
    n_registros: int
    tamanho_cabecalho: int
    tamanho_registro: int
    campos: list[Campo]


def ler_cabecalho(caminho: str | Path) -> CabecalhoDBF:
    with open(caminho, "rb") as fh:
        h = fh.read(32)
        if len(h) < 32:
            raise ValueError(f"Arquivo DBF inválido ou vazio: {caminho}")
        n, tam_cab, tam_reg = struct.unpack("<IHH", h[4:12])
        campos: list[Campo] = []
        offset = 1
        while True:
            fd = fh.read(32)
            if not fd or fd[0] == 0x0D:
                break
            nome = fd[:11].split(b"\0")[0].decode("latin-1").strip().upper()
            tipo = chr(fd[11])
            tamanho = fd[16]
            campos.append(Campo(nome, tipo, tamanho, offset))
            offset += tamanho
    return CabecalhoDBF(n, tam_cab, tam_reg, campos)


def _decodificar(bytes_col: np.ndarray) -> pd.Series:
    """Converte um array de bytes fixos em textos sem espaços (vazio -> None)."""
    s = pd.Series(bytes_col).str.decode("latin-1").str.strip()
    return s.where(s != "", None)


def _para_dataframe(dados: np.ndarray, campos: list[Campo]) -> pd.DataFrame:
    saida = {}
    for c in campos:
        bruto = np.ascontiguousarray(dados[:, c.offset:c.offset + c.tamanho]).view(f"S{c.tamanho}").ravel()
        saida[c.nome] = _decodificar(bruto)
    return pd.DataFrame(saida)


def iterar_dbf(
    caminho: str | Path,
    filtro: Callable[[dict[str, np.ndarray]], np.ndarray] | None = None,
    campos_filtro: Iterable[str] = (),
    bloco: int = 250_000,
    linhas_por_lote: int = 300_000,
    progresso: Callable[[float], None] | None = None,
) -> Iterator[pd.DataFrame]:
    """Lê o DBF em lotes, devolvendo DataFrames só com textos.

    ``filtro`` recebe um dicionário {campo: array de bytes} com os campos de
    ``campos_filtro`` e deve devolver uma máscara booleana das linhas a manter.
    Assim só as linhas filtradas são convertidas, o que é bem mais rápido.
    """
    cab = ler_cabecalho(caminho)
    por_nome = {c.nome: c for c in cab.campos}
    campos_filtro = [c for c in campos_filtro if c in por_nome]

    tamanho_arquivo = Path(caminho).stat().st_size
    n = min(cab.n_registros, (tamanho_arquivo - cab.tamanho_cabecalho) // cab.tamanho_registro)
    if n <= 0:
        return

    mm = np.memmap(caminho, dtype=np.uint8, mode="r", offset=cab.tamanho_cabecalho,
                   shape=(n, cab.tamanho_registro))
    try:
        pedacos: list[np.ndarray] = []
        acumulado = 0
        for inicio in range(0, n, bloco):
            fim = min(inicio + bloco, n)
            regs = mm[inicio:fim]
            manter = regs[:, 0] != ord("*")  # registros excluídos
            if filtro is not None:
                cols = {}
                for nome in campos_filtro:
                    c = por_nome[nome]
                    cols[nome] = np.ascontiguousarray(regs[:, c.offset:c.offset + c.tamanho]).view(f"S{c.tamanho}").ravel()
                manter &= filtro(cols)
            if manter.any():
                pedacos.append(np.array(regs[manter]))
                acumulado += int(manter.sum())
            if acumulado >= linhas_por_lote:
                yield _para_dataframe(np.concatenate(pedacos), cab.campos)
                pedacos, acumulado = [], 0
            if progresso:
                progresso(fim / n)
        if pedacos:
            yield _para_dataframe(np.concatenate(pedacos), cab.campos)
    finally:
        del mm


def colunas_dbf(caminho: str | Path) -> list[str]:
    return [c.nome for c in ler_cabecalho(caminho).campos]
