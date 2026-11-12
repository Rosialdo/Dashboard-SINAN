"""Descompressão de arquivos .DBC do DATASUS para .DBF.

Formato do .DBC: o cabeçalho do DBF sem compressão, 4 bytes de CRC e, em
seguida, os registros comprimidos com o PKWare Data Compression Library
("implode").

O descompressor abaixo é uma tradução para Python + Numba do ``blast.c`` de
Mark Adler (zlib/contrib/blast, versão 1.3). Ele substitui o ``pyreaddbc``,
que é AGPL-3.0 e não atende à política de licenças do projeto (licenças permissivas apenas).

Esta é uma versão ALTERADA do original, distribuída sob a mesma licença zlib:

    Copyright (C) 2003, 2012, 2013 Mark Adler

    This software is provided 'as-is', without any express or implied
    warranty.  In no event will the author be held liable for any damages
    arising from the use of this software.

    Permission is granted to anyone to use this software for any purpose,
    including commercial applications, and to alter it and redistribute it
    freely, subject to the following restrictions:

    1. The origin of this software must not be misrepresented; you must not
       claim that you wrote the original software. If you use this software
       in a product, an acknowledgment in the product documentation would be
       appreciated but is not required.
    2. Altered source versions must be plainly marked as such, and must not be
       misrepresented as being the original software.
    3. This notice may not be removed or altered from any source distribution.

Alterações em relação ao original: tradução para Python/Numba; a saída é
escrita direto num arquivo mapeado em memória (``numpy.memmap``), em vez de uma
janela circular de 4 KB, o que mantém o uso de RAM baixo mesmo no maior
arquivo do SINAN (dengue 2024: 287 MB comprimido, 2,1 GB descomprimido).
"""

from __future__ import annotations

import os
import struct
from pathlib import Path

import numpy as np
from numba import njit

MAXBITS = 13  # maior tamanho de código Huffman no formato

# Tabelas do blast.c: tamanhos dos códigos em forma compacta (4 bits baixos =
# tamanho, 4 bits altos = repetições - 1).
_LITLEN = (
    11, 124, 8, 7, 28, 7, 188, 13, 76, 4, 10, 8, 12, 10, 12, 10, 8, 23, 8,
    9, 7, 6, 7, 8, 7, 6, 55, 8, 23, 24, 12, 11, 7, 9, 11, 12, 6, 7, 22, 5,
    7, 24, 6, 11, 9, 6, 7, 22, 7, 11, 38, 7, 9, 8, 25, 11, 8, 11, 9, 12,
    8, 12, 5, 38, 5, 38, 5, 11, 7, 5, 6, 21, 6, 10, 53, 8, 7, 24, 10, 27,
    44, 253, 253, 253, 252, 252, 252, 13, 12, 45, 12, 45, 12, 61, 12, 45,
    44, 173,
)
_LENLEN = (2, 35, 36, 53, 38, 23)
_DISTLEN = (2, 20, 53, 230, 247, 151, 248)
_BASE = np.array([3, 2, 4, 5, 6, 7, 8, 9, 10, 12, 16, 24, 40, 72, 136, 264], dtype=np.int64)
_EXTRA = np.array([0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8], dtype=np.int64)

# Códigos de erro devolvidos pelo descompressor
_ERROS = {
    -1: "cabeçalho de literais inválido",
    -2: "tamanho de dicionário inválido",
    -3: "distância aponta para antes do início dos dados",
    -4: "arquivo comprimido terminou antes do fim",
    -5: "resultado maior que o tamanho previsto no cabeçalho do DBF",
    -9: "código Huffman inválido",
}


def _construir(compacto: tuple[int, ...]) -> tuple[np.ndarray, np.ndarray]:
    """Monta a tabela Huffman canônica (contagem por tamanho + símbolos)."""
    tamanhos: list[int] = []
    for b in compacto:
        tamanhos.extend([b & 15] * ((b >> 4) + 1))
    contagem = np.zeros(MAXBITS + 1, dtype=np.int64)
    for t in tamanhos:
        contagem[t] += 1
    offs = np.zeros(MAXBITS + 2, dtype=np.int64)
    for t in range(1, MAXBITS + 1):
        offs[t + 1] = offs[t] + contagem[t]
    simbolos = np.zeros(len(tamanhos), dtype=np.int64)
    for s, t in enumerate(tamanhos):
        if t:
            simbolos[offs[t]] = s
            offs[t] += 1
    return contagem, simbolos


_LIT_CNT, _LIT_SYM = _construir(_LITLEN)
_LEN_CNT, _LEN_SYM = _construir(_LENLEN)
_DIST_CNT, _DIST_SYM = _construir(_DISTLEN)


@njit(cache=True, nogil=True)
def _blast(entrada, pos_in, saida, pos_out,
           lit_cnt, lit_sym, len_cnt, len_sym, dist_cnt, dist_sym, base, extra):
    """Descomprime ``entrada[pos_in:]`` em ``saida[pos_out:]``.

    Devolve a posição final na saída, ou um código de erro negativo.
    """
    n_in = entrada.shape[0]
    n_out = saida.shape[0]
    inicio = pos_out
    bitbuf = 0
    bitcnt = 0

    # --- cabeçalho do fluxo: literais codificados? e tamanho do dicionário
    while bitcnt < 16:
        if pos_in >= n_in:
            return -4
        bitbuf |= np.int64(entrada[pos_in]) << bitcnt
        pos_in += 1
        bitcnt += 8
    lit = bitbuf & 255
    dic = (bitbuf >> 8) & 255
    bitbuf >>= 16
    bitcnt -= 16
    if lit > 1:
        return -1
    if dic < 4 or dic > 6:
        return -2

    while True:
        # um bit: 1 = cópia (tamanho, distância), 0 = literal
        if bitcnt < 1:
            if pos_in >= n_in:
                return -4
            bitbuf |= np.int64(entrada[pos_in]) << bitcnt
            pos_in += 1
            bitcnt += 8
        flag = bitbuf & 1
        bitbuf >>= 1
        bitcnt -= 1

        if flag:
            # --- símbolo de tamanho (Huffman com bits invertidos)
            code = 0
            first = 0
            index = 0
            symbol = -1
            for ln in range(1, MAXBITS + 1):
                if bitcnt < 1:
                    if pos_in >= n_in:
                        return -4
                    bitbuf |= np.int64(entrada[pos_in]) << bitcnt
                    pos_in += 1
                    bitcnt += 8
                code |= (bitbuf & 1) ^ 1
                bitbuf >>= 1
                bitcnt -= 1
                count = len_cnt[ln]
                if code < first + count:
                    symbol = len_sym[index + code - first]
                    break
                index += count
                first += count
                first <<= 1
                code <<= 1
            if symbol < 0:
                return -9
            ne = extra[symbol]
            while bitcnt < ne:
                if pos_in >= n_in:
                    return -4
                bitbuf |= np.int64(entrada[pos_in]) << bitcnt
                pos_in += 1
                bitcnt += 8
            length = base[symbol] + (bitbuf & ((1 << ne) - 1))
            bitbuf >>= ne
            bitcnt -= ne
            if length == 519:  # código de fim
                break

            # --- distância
            shift = 2 if length == 2 else dic
            code = 0
            first = 0
            index = 0
            symbol = -1
            for ln in range(1, MAXBITS + 1):
                if bitcnt < 1:
                    if pos_in >= n_in:
                        return -4
                    bitbuf |= np.int64(entrada[pos_in]) << bitcnt
                    pos_in += 1
                    bitcnt += 8
                code |= (bitbuf & 1) ^ 1
                bitbuf >>= 1
                bitcnt -= 1
                count = dist_cnt[ln]
                if code < first + count:
                    symbol = dist_sym[index + code - first]
                    break
                index += count
                first += count
                first <<= 1
                code <<= 1
            if symbol < 0:
                return -9
            while bitcnt < shift:
                if pos_in >= n_in:
                    return -4
                bitbuf |= np.int64(entrada[pos_in]) << bitcnt
                pos_in += 1
                bitcnt += 8
            dist = (symbol << shift) + (bitbuf & ((1 << shift) - 1)) + 1
            bitbuf >>= shift
            bitcnt -= shift
            if dist > pos_out - inicio:
                return -3
            if pos_out + length > n_out:
                return -5
            # cópia byte a byte (as regiões podem se sobrepor)
            for _ in range(length):
                saida[pos_out] = saida[pos_out - dist]
                pos_out += 1
        else:
            if lit:
                code = 0
                first = 0
                index = 0
                symbol = -1
                for ln in range(1, MAXBITS + 1):
                    if bitcnt < 1:
                        if pos_in >= n_in:
                            return -4
                        bitbuf |= np.int64(entrada[pos_in]) << bitcnt
                        pos_in += 1
                        bitcnt += 8
                    code |= (bitbuf & 1) ^ 1
                    bitbuf >>= 1
                    bitcnt -= 1
                    count = lit_cnt[ln]
                    if code < first + count:
                        symbol = lit_sym[index + code - first]
                        break
                    index += count
                    first += count
                    first <<= 1
                    code <<= 1
                if symbol < 0:
                    return -9
            else:
                while bitcnt < 8:
                    if pos_in >= n_in:
                        return -4
                    bitbuf |= np.int64(entrada[pos_in]) << bitcnt
                    pos_in += 1
                    bitcnt += 8
                symbol = bitbuf & 255
                bitbuf >>= 8
                bitcnt -= 8
            if pos_out >= n_out:
                return -5
            saida[pos_out] = symbol
            pos_out += 1
    return pos_out


def dbc_para_dbf(origem: str | Path, destino: str | Path) -> Path:
    """Descomprime ``origem`` (.dbc) em ``destino`` (.dbf) e devolve o destino."""
    origem, destino = Path(origem), Path(destino)
    with open(origem, "rb") as fh:
        cab = fh.read(12)
    if len(cab) < 12:
        raise ValueError(f"Arquivo DBC inválido ou vazio: {origem}")
    n_registros, tam_cabecalho, tam_registro = struct.unpack("<IHH", cab[4:12])

    # Tamanho máximo da saída: cabeçalho + registros + marcador de fim (0x1A).
    capacidade = tam_cabecalho + n_registros * tam_registro + 1

    entrada = np.memmap(origem, dtype=np.uint8, mode="r")
    saida = np.memmap(destino, dtype=np.uint8, mode="w+", shape=(capacidade,))
    try:
        saida[:tam_cabecalho] = entrada[:tam_cabecalho]
        fim = _blast(entrada, tam_cabecalho + 4, saida, tam_cabecalho,
                     _LIT_CNT, _LIT_SYM, _LEN_CNT, _LEN_SYM, _DIST_CNT, _DIST_SYM,
                     _BASE, _EXTRA)
        saida.flush()
    finally:
        # libera os mapeamentos (no Windows, sem isso o arquivo fica preso)
        del saida, entrada

    if fim < 0:
        destino.unlink(missing_ok=True)
        raise ValueError(f"Falha ao descomprimir {origem.name}: {_ERROS.get(int(fim), fim)}")
    if fim < capacidade:
        os.truncate(destino, fim)
    return destino
