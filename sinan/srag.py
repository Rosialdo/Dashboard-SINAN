"""SRAG (síndrome respiratória aguda grave) do SIVEP-Gripe, publicado no OpenDataSUS.

O arquivo nacional em Parquet é convertido para o mesmo formato dos agravos do SINAN:
colunas originais em texto (MAIÚSCULAS) e as colunas derivadas de ``processar.derivar``.
Este módulo não importa ``download`` (é o ``download`` que importa este).
"""

from __future__ import annotations

import re
import time
import urllib.request
from collections.abc import Callable, Iterator
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from . import agravos as cat
from .config import PASTA_BRUTOS, SRAG_PAGINA, UF_COD
from .processar import gravar_parquet, registrar_inventario

_PARQUET = re.compile(r'"url":"(https://[^"]+/SRAG/(\d{4})/INFLUD\d{2}-(\d{2}-\d{2}-\d{4})\.parquet)"')


# ----------------------------------------------------------- listagem e download
def paginas(hoje: date) -> list[str]:
    """Endereços da página do conjunto, do mais provável ao de reserva (o nome muda todo ano)."""
    base = SRAG_PAGINA.rsplit("-", 1)[0]
    return list(dict.fromkeys([f"{base}-{hoje.year + 1}", f"{base}-{hoje.year}", SRAG_PAGINA]))


def ler_listagem(html: str) -> dict[str, dict]:
    """Arquivos Parquet por ano, lidos do JSON embutido na página do OpenDataSUS."""
    achados: dict[str, tuple[datetime, str, str]] = {}
    for url, ano, data in _PARQUET.findall(html):
        quando = datetime.strptime(data, "%d-%m-%Y")
        if ano not in achados or quando > achados[ano][0]:
            achados[ano] = (quando, url, data)
    recentes = sorted(achados, reverse=True)[:2]
    # a situação é só para exibir: a decisão de baixar compara a data (pipeline.arquivo_mudou)
    return {ano: {"arquivo": url, "situacao": "preliminar" if ano in recentes else "final",
                  "tamanho": 0, "data_ftp": data}
            for ano, (_, url, data) in sorted(achados.items())}


def listar(hoje: date | None = None) -> dict[str, dict]:
    """Consulta o OpenDataSUS. A primeira página com arquivos vale; nenhuma -> ConnectionError."""
    erros = []
    for url in paginas(hoje or date.today()):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                lista = ler_listagem(r.read().decode("utf-8", "replace"))
        except OSError as e:
            erros.append(f"{url}: {e}")
            continue
        if lista:  # página que não existe redireciona para a lista geral, sem arquivos
            return lista
    raise ConnectionError(f"Não foi possível consultar o OpenDataSUS ({'; '.join(erros) or 'sem arquivos'}).")


def baixar(info: dict, progresso: Callable[[int, int], None] | None = None, tentativas: int = 4) -> Path:
    """Baixa o Parquet do SRAG; só fica com o nome final quando chega inteiro."""
    url = info["arquivo"]
    PASTA_BRUTOS.mkdir(parents=True, exist_ok=True)
    destino = PASTA_BRUTOS / url.rsplit("/", 1)[-1]
    parcial = destino.with_suffix(".parcial")
    ultimo_erro: Exception | None = None
    # shortcut: sem retomada (Range); se os anos grandes (2020–2021) falharem muito, retomar como em download.baixar_arquivo
    for tentativa in range(tentativas):
        try:
            with urllib.request.urlopen(url, timeout=120) as r, open(parcial, "wb") as fh:
                total = int(r.headers.get("Content-Length") or 0)
                recebido = 0
                while bloco := r.read(256 * 1024):
                    fh.write(bloco)
                    recebido += len(bloco)
                    if progresso:
                        progresso(recebido, total)
            if total and recebido != total:
                raise OSError("download incompleto")
            parcial.replace(destino)
            return destino
        except OSError as e:
            ultimo_erro = e
            parcial.unlink(missing_ok=True)
            if tentativa + 1 < tentativas:
                time.sleep(3 * (tentativa + 1))
    raise ConnectionError(f"Não foi possível baixar {destino.name}: {ultimo_erro}")


# ----------------------------------------------------------- conversão
# lotes pequenos: são ~190 colunas, e no Brasil inteiro um lote grande passaria de 1 GB em textos
LOTE = 20_000


def _data(s: pd.Series) -> pd.Series:
    """Texto AAAA-MM-DD ou dd/mm/aaaa -> AAAAMMDD (o formato do SINAN)."""
    d = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    d = d.fillna(pd.to_datetime(s, format="%d/%m/%Y", errors="coerce"))
    return d.dt.strftime("%Y%m%d").astype("object").where(d.notna(), None)


def para_sinan(df: pd.DataFrame) -> pd.DataFrame:
    """Cópia com os nomes e formatos que ``processar.derivar`` espera."""
    s = df.copy()
    for c in ("DT_NOTIFIC", "DT_SIN_PRI"):
        if c in s:
            s[c] = _data(s[c])
    for c in ("SG_UF_NOT", "SG_UF"):
        if c in s:
            s[c] = s[c].map(lambda v: UF_COD.get(v, v) if isinstance(v, str) else v)
    if "CO_MUN_NOT" in s:
        s["ID_MUNICIP"] = s["CO_MUN_NOT"]  # no SIVEP, ID_MUNICIP é o nome do município
    if "CO_MUN_RES" in s:
        s["ID_MN_RESI"] = s["CO_MUN_RES"]
    if "TP_IDADE" in s and "NU_IDADE_N" in s:
        # SIVEP: TP_IDADE 1 dia, 2 mês, 3 ano; SINAN: 1º dígito 2 dia, 3 mês, 4 ano
        idade = (pd.to_numeric(s["TP_IDADE"], errors="coerce") + 1) * 1000 + pd.to_numeric(s["NU_IDADE_N"], errors="coerce")
        s["NU_IDADE_N"] = idade.map(lambda v: None if pd.isna(v) else str(int(v)))
    return s


def _texto(col: pa.ChunkedArray | pa.Array) -> pa.Array:
    """Qualquer coluna -> texto; datas como AAAA-MM-DD e números sem ".0" no fim."""
    tipo = col.type
    if pa.types.is_temporal(tipo):
        return pc.strftime(col, format="%Y-%m-%d")
    texto = pc.cast(col, pa.string())
    if pa.types.is_decimal(tipo) or pa.types.is_floating(tipo):
        # decimal128(38,10) vira "1.0000000000"; sem isso os rótulos de chave "1" não pegam
        texto = pc.replace_substring_regex(texto, r"\.0+$", "")
    return texto


def _lotes(arquivo: pq.ParquetFile, ufs: list[str], progresso: Callable[[float, str], None]) -> Iterator[pd.DataFrame]:
    nomes = arquivo.schema_arrow.names
    campos_uf = [c for c in ("SG_UF", "SG_UF_NOT") if c in nomes]
    todo_brasil = "BR" in ufs
    if not todo_brasil and not campos_uf:
        raise ValueError("o arquivo do SRAG não tem campo de UF. Escolha \"BR\" (Brasil inteiro).")
    aceitos = pa.array(sorted({*ufs, *(UF_COD[u] for u in ufs if u in UF_COD)}))
    total, lidos = max(arquivo.metadata.num_rows, 1), 0
    for lote in arquivo.iter_batches(batch_size=LOTE):
        lidos += lote.num_rows
        progresso(lidos / total, "lendo registros")
        if not todo_brasil:
            mascara = None
            for c in campos_uf:
                m = pc.fill_null(pc.is_in(pc.cast(lote.column(c), pa.string()), value_set=aceitos), False)
                mascara = m if mascara is None else pc.or_(mascara, m)
            lote = lote.filter(mascara)
        if lote.num_rows:
            yield pa.table([_texto(lote.column(c)) for c in nomes], names=nomes).to_pandas()


def processar(
    caminho: Path,
    ano: int,
    ufs: list[str],
    info: dict | None = None,
    progresso: Callable[[float, str], None] | None = None,
) -> int:
    """Converte o Parquet nacional do SRAG no Parquet do painel. Devolve o número de registros."""
    avisar = progresso or (lambda f, m: None)
    arquivo = pq.ParquetFile(caminho)
    try:
        colunas = arquivo.schema_arrow.names
        total = gravar_parquet(((b, para_sinan(b)) for b in _lotes(arquivo, ufs, avisar)),
                               cat.obter("SRAG"), ano, colunas)
    finally:
        arquivo.close()  # no Windows, o arquivo aberto não pode ser apagado
    registrar_inventario("SRAG", ano, total, ufs, info or {}, caminho.name)
    avisar(1.0, "concluído")
    return total
