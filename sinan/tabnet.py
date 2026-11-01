"""Leitura dos rótulos oficiais do tabulador TabNet/TabWin do SINAN.

O DATASUS publica, para cada agravo, um arquivo ``.def`` que diz quais
variáveis podem ser tabuladas e qual arquivo ``.cnv`` traduz os códigos em
rótulos (ex.: CLASSI_FIN 5 -> "Descartado"). Usar esses arquivos garante que
o dashboard mostre os mesmos rótulos do TabNet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import pandas as pd

from .config import PASTA_TABNET

COL_CODIGOS = 59  # nos .cnv, os códigos começam sempre nesta coluna


@dataclass
class Conversor:
    nome: str
    largura: int
    rotulos: list[str] = field(default_factory=list)  # na ordem do arquivo
    regras: list[tuple[str, str, str | None]] = field(default_factory=list)  # (rótulo, ini, fim)

    def mapear(self, valores: pd.Series, inicio: int = 1) -> pd.Series:
        """Traduz uma série de códigos (texto) para rótulos.

        ``inicio`` é a posição (1 = primeiro caractere) usada pelo .def, por
        exemplo DT_NOTIFIC,5 pega o mês de uma data AAAAMMDD.
        """
        unicos = valores.dropna().unique().tolist()
        mapa = {v: self._rotulo(str(v)[inicio - 1:inicio - 1 + self.largura]) for v in unicos}
        vazio = self._rotulo("")
        return valores.map(mapa).where(valores.notna(), vazio)

    def _rotulo(self, codigo: str) -> str:
        cod = codigo.strip()
        achado = None
        # as linhas posteriores têm prioridade (ex.: "Ign/Branco ,0-9" e depois "1 Branca")
        for rotulo, ini, fim in self.regras:
            if _bate(cod, ini, fim):
                achado = rotulo
        if achado is None:
            return f"Código {cod}" if cod else "Ign/Branco"
        return achado


def _bate(cod: str, ini: str, fim: str | None) -> bool:
    if fim is None:
        if ini == cod:
            return True
        return ini.isdigit() and cod.isdigit() and int(ini) == int(cod)
    if not cod:
        return False
    if ini.isdigit() and fim.isdigit() and cod.isdigit():
        return int(ini) <= int(cod) <= int(fim)
    return ini <= cod <= fim


def _arquivo(nome: str) -> Path | None:
    p = PASTA_TABNET / nome.strip().lower()
    return p if p.exists() else None


@lru_cache(maxsize=None)
def ler_cnv(nome: str) -> Conversor | None:
    p = _arquivo(nome)
    if p is None:
        return None
    linhas = [l.rstrip("\r\n") for l in p.read_text(encoding="utf-8").splitlines()]
    linhas = [l for l in linhas if l.strip() and not l.lstrip().startswith(";")]
    if not linhas:
        return None
    cab = linhas[0].split()
    try:
        largura = int(cab[1])
    except (IndexError, ValueError):
        largura = 2
    conv = Conversor(nome.lower(), largura)
    for l in linhas[1:]:
        m = re.match(r"^\s*\d+\s{1,3}", l)
        if not m:
            continue
        if len(l) > COL_CODIGOS:
            rotulo = l[m.end():COL_CODIGOS].strip()
            codigos = l[COL_CODIGOS:]
        else:  # linha fora do padrão: separa pelo primeiro bloco de 2+ espaços
            partes = re.split(r"\s{2,}", l[m.end():].strip(), maxsplit=1)
            rotulo, codigos = partes[0], (partes[1] if len(partes) > 1 else "")
        if not rotulo:
            continue
        codigos = codigos.split(";")[0]
        if rotulo not in conv.rotulos:
            conv.rotulos.append(rotulo)
        for cod in codigos.split(","):
            if not cod.strip():
                conv.regras.append((rotulo, "", None))  # código em branco
                continue
            cod = cod.strip()
            if "-" in cod:
                ini, fim = cod.split("-", 1)
                conv.regras.append((rotulo, ini.strip(), fim.strip()))
            else:
                conv.regras.append((rotulo, cod, None))
    return conv


@dataclass
class VariavelDef:
    rotulo: str
    campo: str
    inicio: int
    cnv: str


@lru_cache(maxsize=None)
def ler_def(nome: str) -> list[VariavelDef]:
    p = _arquivo(nome)
    if p is None:
        return []
    variaveis: list[VariavelDef] = []
    vistos: set[tuple[str, int, str]] = set()
    padrao = re.compile(r"^[XLCSTDxlcstd]([^,;]+?)\s*,\s*([A-Za-z0-9_]+)\s*,\s*(\d+)\s*,\s*([^,;\s]+\.cnv)", re.I)
    for l in p.read_text(encoding="utf-8").splitlines():
        m = padrao.match(l.strip())
        if not m:
            continue
        rotulo, campo, inicio, cnv = m.group(1).strip(), m.group(2).upper(), int(m.group(3)), m.group(4)
        chave = (campo, inicio, cnv.lower())
        if chave in vistos or _arquivo(cnv) is None:
            continue
        vistos.add(chave)
        variaveis.append(VariavelDef(rotulo, campo, inicio, cnv))
    return variaveis


def conversor_do_campo(arquivo_def: str | None, campo: str) -> Conversor | None:
    """Conversor declarado no .def para um campo inteiro (posição 1).

    Quando há mais de um, vale o último: nos .def do SINAN o último costuma
    ser o mais atual (ex.: "Conf.Desc pos2010") ou o genérico ("Outros agravos").
    """
    if not arquivo_def:
        return None
    achado = None
    for v in ler_def(arquivo_def):
        if v.campo == campo and v.inicio == 1:
            achado = v
    return ler_cnv(achado.cnv) if achado else None
