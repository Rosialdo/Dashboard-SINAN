"""SRAG do SIVEP-Gripe (sinan/srag.py): conversão para o formato do painel."""

import json
import shutil
from datetime import date
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest
from conftest import escrever_amostra_srag

from sinan import download, pipeline, processar, srag


def test_para_sinan_converte_uf_municipio_data_e_idade():
    df = pd.DataFrame({"SG_UF_NOT": ["RR"], "SG_UF": ["RR"], "CO_MUN_NOT": ["140010"],
                       "CO_MUN_RES": ["140010"], "DT_SIN_PRI": ["2026-05-09"],
                       "DT_NOTIFIC": ["2026-05-12"], "TP_IDADE": ["2"], "NU_IDADE_N": ["3"]})
    s = srag.para_sinan(df)
    assert s.loc[0, ["SG_UF", "ID_MN_RESI", "DT_SIN_PRI", "NU_IDADE_N"]].tolist() == \
        ["14", "140010", "20260509", "3003"]  # dia 9 de maio, não 5 de setembro
    assert df.loc[0, "SG_UF"] == "RR"  # o original não é alterado


def test_para_sinan_aceita_data_em_texto_brasileiro_e_idade_vazia():
    df = pd.DataFrame({"SG_UF": ["RR"], "DT_SIN_PRI": ["09/05/2026"], "TP_IDADE": [None], "NU_IDADE_N": [None]})
    s = srag.para_sinan(df)
    assert s.loc[0, "DT_SIN_PRI"] == "20260509" and pd.isna(s.loc[0, "NU_IDADE_N"])


@pytest.mark.parametrize("antiga", [False, True])
def test_processar_srag_filtra_uf_e_deriva(dados_srag, tmp_path, antiga):
    amostra = escrever_amostra_srag(tmp_path / "amostra.parquet", antiga)
    n = srag.processar(amostra, 2026, ["RR"], {"arquivo": "INFLUD26-23-11-2026.parquet",
                       "situacao": "preliminar", "data_ftp": "23-11-2026"})
    t = pq.read_table(processar.caminho_parquet("SRAG", 2026)).to_pandas()
    assert n == len(t) == 3
    assert set(t["uf_res"]) == {"RR"} and t["SG_UF"].eq("RR").all()  # original em sigla
    assert t["CLASSI_FIN"].iloc[0] == "5" and t["classificacao"].iloc[0] == "SRAG por covid-19"
    assert t["classificacao"].iloc[2] == "Em investigação"
    assert (t["sem_epi"].astype(str) == t["SEM_PRI"]).all()  # mesma regra do SIVEP
    assert t["idade"].notna().all() and t["data_sintomas"].notna().all()
    assert t["idade"].iloc[1] == pytest.approx(0.25)  # 3 meses
    assert processar.ler_inventario()["SRAG_2026"]["data_ftp"] == "23-11-2026"


def test_processar_srag_uf_sem_casos_gera_arquivo_vazio(dados_srag, amostra_srag):
    assert srag.processar(amostra_srag, 2026, ["AC"]) == 0
    nomes = pq.read_schema(processar.caminho_parquet("SRAG", 2026)).names
    assert {"CLASSI_FIN", "SG_UF", "CO_MUN_RES", "hospitalizado"} <= set(nomes)  # originais + derivadas


# ----------------------------------------------------------- listagem e download
PAGINA = (Path(__file__).parent / "fixtures" / "srag_pagina.html").read_text(encoding="utf-8")
INFO_2026 = {"arquivo": "https://x/SRAG/2026/INFLUD26-23-11-2026.parquet", "situacao": "preliminar",
             "tamanho": 0, "data_ftp": "23-11-2026"}


class _Resposta:
    """Resposta falsa do urllib: entrega ``partes`` e depois levanta ``erro`` (se houver)."""

    def __init__(self, partes: list[bytes], tamanho: int, erro: Exception | None = None):
        self.partes, self.headers, self.erro = list(partes), {"Content-Length": str(tamanho)}, erro

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, n: int = -1) -> bytes:
        if self.partes:
            return self.partes.pop(0)
        if self.erro:
            raise self.erro
        return b""


def test_ler_listagem_na_pagina_real():
    lista = srag.ler_listagem(PAGINA)
    assert {"2019", "2024", "2026"} <= set(lista)
    assert lista["2026"]["arquivo"].startswith("https://s3.") and lista["2026"]["arquivo"].endswith(".parquet")
    assert lista["2026"]["situacao"] == "preliminar" and lista["2019"]["situacao"] == "final"
    assert lista["2026"]["data_ftp"] == "23-11-2026"


def test_ler_listagem_compara_datas_como_data():
    html = ('"url":"https://x/SRAG/2026/INFLUD26-16-12-2026.parquet" '
            '"url":"https://x/SRAG/2026/INFLUD26-23-11-2026.parquet"')
    assert srag.ler_listagem(html)["2026"]["data_ftp"] == "16-12-2026"


def test_paginas_tenta_o_ano_seguinte_primeiro():
    p = srag.paginas(date(2026, 11, 23))
    assert p[0].endswith("srag-2019-a-2027") and p[1].endswith("srag-2019-a-2026")
    assert len(p) == len(set(p)) == 2  # a constante é a mesma do ano atual


def test_listar_usa_a_primeira_pagina_com_arquivos(monkeypatch):
    pedidas = []

    def abrir(url, timeout):
        pedidas.append(url)
        corpo = PAGINA if url.endswith("2026") else "<html>lista geral, sem arquivos</html>"
        return _Resposta([corpo.encode()], len(corpo))

    monkeypatch.setattr(srag.urllib.request, "urlopen", abrir)
    assert srag.listar(date(2026, 11, 23))["2026"]["data_ftp"] == "23-11-2026"
    assert pedidas[0].endswith("2027")


def test_listar_sem_nenhuma_pagina_levanta_erro(monkeypatch):
    monkeypatch.setattr(srag.urllib.request, "urlopen", lambda url, timeout: _Resposta([b"<html/>"], 7))
    with pytest.raises(ConnectionError):
        srag.listar(date(2026, 11, 23))


def test_publicacao_conjunta_nao_manda_baixar_de_novo():
    salvo = {"data_ftp": "23-03-2026", "situacao": "final"}
    assert not pipeline.arquivo_mudou("SRAG", salvo, {"data_ftp": "23-03-2026", "situacao": "preliminar"})
    assert pipeline.arquivo_mudou("SRAG", salvo, {"data_ftp": "30-03-2026", "situacao": "final"})
    assert pipeline.arquivo_mudou("DENG", salvo, {"data_ftp": "23-03-2026", "situacao": "preliminar"})


def _salvar_listagem(arquivos: dict) -> None:
    download.PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    download.ARQ_LISTAGEM_FTP.write_text(json.dumps({"atualizado_em": "x", "arquivos": arquivos}), encoding="utf-8")


def _falha(*a, **k):
    raise ConnectionError("fora do ar")


def test_listar_ftp_mantem_srag_salvo_quando_o_opendatasus_falha(dados_srag, monkeypatch):
    _salvar_listagem({"SRAG": {"2026": {**INFO_2026, "data_ftp": "16-11-2026"}}})
    monkeypatch.setattr(download, "_listar_sinan", lambda: {"DENG": {"2024": {"data_ftp": "x"}}})
    monkeypatch.setattr(download.srag, "listar", _falha)
    lista = download.listar_ftp()
    assert lista["arquivos"]["SRAG"]["2026"]["data_ftp"] == "16-11-2026" and "DENG" in lista["arquivos"]
    assert lista["falhas"] == ["OpenDataSUS (SRAG)"]
    assert download.listagem_salva()["falhas"] == ["OpenDataSUS (SRAG)"]


def test_listar_ftp_atualiza_srag_quando_o_ftp_falha(dados_srag, monkeypatch):
    _salvar_listagem({"DENG": {"2024": {"data_ftp": "x"}}})
    monkeypatch.setattr(download, "_listar_sinan", _falha)
    monkeypatch.setattr(download.srag, "listar", lambda: {"2026": INFO_2026})
    lista = download.listar_ftp()
    assert lista["arquivos"]["SRAG"]["2026"]["data_ftp"] == "23-11-2026" and "DENG" in lista["arquivos"]
    assert lista["falhas"] == ["DATASUS (FTP)"]


def test_listar_ftp_falha_so_com_as_duas_fontes_fora(dados_srag, monkeypatch):
    monkeypatch.setattr(download, "_listar_sinan", _falha)
    monkeypatch.setattr(download.srag, "listar", _falha)
    with pytest.raises(ConnectionError):
        download.listar_ftp()


def test_baixar_interrompido_nao_deixa_arquivo_final(dados_srag, monkeypatch):
    monkeypatch.setattr(srag.urllib.request, "urlopen",
                        lambda url, timeout: _Resposta([b"x" * 40], 100, OSError("conexão caiu")))
    with pytest.raises(ConnectionError):
        srag.baixar({"arquivo": "https://x/SRAG/2026/INFLUD26-23-11-2026.parquet"}, tentativas=1)
    assert not (srag.PASTA_BRUTOS / "INFLUD26-23-11-2026.parquet").exists()


def test_baixar_completo(dados_srag, monkeypatch):
    monkeypatch.setattr(srag.urllib.request, "urlopen", lambda url, timeout: _Resposta([b"x" * 60, b"y" * 40], 100))
    caminho = srag.baixar({"arquivo": "https://x/SRAG/2026/INFLUD26-23-11-2026.parquet"}, tentativas=1)
    assert caminho.name == "INFLUD26-23-11-2026.parquet" and caminho.stat().st_size == 100


def test_atualizar_srag_usa_o_caminho_proprio(dados_srag, amostra_srag, monkeypatch):
    monkeypatch.setattr(pipeline, "listar_ftp", lambda: {"arquivos": {"SRAG": {"2026": INFO_2026}}})

    def baixar(info, progresso=None):
        srag.PASTA_BRUTOS.mkdir(parents=True, exist_ok=True)
        return Path(shutil.copy(amostra_srag, srag.PASTA_BRUTOS / "INFLUD26-23-11-2026.parquet"))

    monkeypatch.setattr(srag, "baixar", baixar)
    res = pipeline.atualizar(["SRAG"], [2026], ["RR"])
    assert res.erros == []
    assert res.sucesso == ["Síndrome respiratória aguda grave (SRAG) 2026: 3 registros"]
    assert not list(srag.PASTA_BRUTOS.glob("*.parquet"))  # o bruto é apagado
    assert pipeline.atualizar(["SRAG"], [2026], ["RR"]).pulados  # mesma data: não baixa de novo
