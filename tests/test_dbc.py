"""Testes do descompressor de .DBC (sinan/dbc.py).

O resultado é comparado com a biblioteca independente ``datasus-dbc`` (MIT),
instalada só como dependência de desenvolvimento.
"""

from pathlib import Path

import datasus_dbc
import pytest

from sinan.dbc import dbc_para_dbf
from sinan.dbf import ler_cabecalho

DADOS = Path(__file__).parent / "fixtures"
AMOSTRA = DADOS / "ACBIBR06.dbc"  # acidentes biológicos 2006 (FINAIS), 28 KB


def test_resultado_igual_a_biblioteca_de_referencia(tmp_path):
    destino = dbc_para_dbf(AMOSTRA, tmp_path / "saida.dbf")
    esperado = datasus_dbc.decompress_bytes(AMOSTRA.read_bytes())
    assert destino.read_bytes() == esperado


def test_saida_e_um_dbf_valido(tmp_path):
    destino = dbc_para_dbf(AMOSTRA, tmp_path / "saida.dbf")
    cab = ler_cabecalho(destino)
    assert cab.n_registros > 0
    assert any(c.nome == "ID_AGRAVO" for c in cab.campos)
    tamanho_dados = destino.stat().st_size - cab.tamanho_cabecalho
    assert tamanho_dados >= cab.n_registros * cab.tamanho_registro


def test_arquivo_corrompido_gera_erro_e_nao_deixa_lixo(tmp_path):
    bruto = bytearray(AMOSTRA.read_bytes())
    tam_cabecalho = int.from_bytes(bruto[8:10], "little")
    corrompido = tmp_path / "ruim.dbc"
    # trunca o fluxo comprimido logo depois do cabeçalho
    corrompido.write_bytes(bytes(bruto[: tam_cabecalho + 4 + 50]))
    destino = tmp_path / "ruim.dbf"
    with pytest.raises(ValueError):
        dbc_para_dbf(corrompido, destino)
    assert not destino.exists()


def test_arquivo_vazio_gera_erro(tmp_path):
    vazio = tmp_path / "vazio.dbc"
    vazio.write_bytes(b"")
    with pytest.raises(ValueError):
        dbc_para_dbf(vazio, tmp_path / "vazio.dbf")
