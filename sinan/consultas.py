"""Consultas do dashboard, feitas com DuckDB direto nos arquivos Parquet.

O DuckDB agrega milhões de linhas em segundos, então o dashboard continua
rápido mesmo com o Brasil inteiro carregado.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass

import duckdb
import pandas as pd

from .config import ARQ_MUNICIPIOS, ARQ_POPULACAO, PASTA_PARQUET

_local = threading.local()
_base: duckdb.DuckDBPyConnection | None = None
_base_lock = threading.Lock()

# códigos de agravo são siglas curtas (DENG, CHIK, LERD...). Validar evita que
# um parâmetro da URL entre no SQL ou no caminho dos arquivos.
_CODIGO = re.compile(r"^[A-Z0-9]{2,8}$")


class AgravoInvalido(ValueError):
    """Código de agravo fora do formato ou sem dados baixados."""


def _sql_texto(valor: str) -> str:
    return "'" + valor.replace("'", "''") + "'"


def _conexao_base() -> duckdb.DuckDBPyConnection:
    """Banco em memória com as tabelas de referência, criado uma única vez."""
    global _base
    with _base_lock:
        if _base is None:
            con = duckdb.connect()
            con.execute(f"CREATE TABLE mun AS SELECT * FROM read_csv({_sql_texto(ARQ_MUNICIPIOS.as_posix())}, all_varchar=true)")
            con.execute(f"""CREATE TABLE pop AS SELECT cod6, CAST(ano AS INTEGER) AS ano,
                            CAST(populacao AS BIGINT) AS populacao
                            FROM read_csv({_sql_texto(ARQ_POPULACAO.as_posix())}, types={{'cod6': 'VARCHAR'}})""")
            _base = con
        return _base


def conexao() -> duckdb.DuckDBPyConnection:
    """Um cursor por thread, todos ligados ao mesmo banco (o servidor atende em várias threads)."""
    con = getattr(_local, "con", None)
    if con is None:
        con = _conexao_base().cursor()
        _local.con = con
    return con


def validar_agravo(agravo: str) -> str:
    agravo = (agravo or "").upper()
    if not _CODIGO.match(agravo):
        raise AgravoInvalido(f"Código de agravo inválido: {agravo!r}")
    return agravo


def agravos_disponiveis() -> list[str]:
    if not PASTA_PARQUET.exists():
        return []
    return sorted(p.name for p in PASTA_PARQUET.iterdir() if p.is_dir() and any(p.glob("*.parquet")))


def tem_dados(agravo: str) -> bool:
    return any((PASTA_PARQUET / validar_agravo(agravo)).glob("*.parquet"))


def _fonte(agravo: str, posicao: bool = False) -> str:
    """Leitura dos Parquet do agravo. ``posicao=True`` acrescenta as colunas
    ``filename`` e ``file_row_number``, que identificam cada linha de forma única."""
    agravo = validar_agravo(agravo)
    if not tem_dados(agravo):
        raise AgravoInvalido(f"Não há dados baixados de {agravo}. Use a tela \"Baixar dados\".")
    extra = ", filename=true, file_row_number=true" if posicao else ""
    return f"read_parquet({_sql_texto((PASTA_PARQUET / agravo).as_posix() + '/*.parquet')}, union_by_name=true{extra})"


def colunas(agravo: str) -> list[str]:
    return [r[0] for r in conexao().execute(f"DESCRIBE SELECT * FROM {_fonte(agravo)}").fetchall()]


@dataclass(frozen=True)
class Filtro:
    agravo: str
    ano_ini: int
    ano_fim: int
    por_residencia: bool = True
    ufs: tuple[str, ...] = ()
    municipios: tuple[str, ...] = ()
    contagem: str = "confirmados"  # "confirmados", "provaveis" (exceto descartados) ou "todas"
    sexo: tuple[str, ...] = ()
    faixas: tuple[str, ...] = ()

    @property
    def col_uf(self) -> str:
        return "uf_res" if self.por_residencia else "uf_not"

    @property
    def col_mun(self) -> str:
        return "mun_res" if self.por_residencia else "mun_not"

    def where(self) -> tuple[str, list]:
        cond, params = ["ano BETWEEN ? AND ?"], [self.ano_ini, self.ano_fim]
        if self.ufs:
            cond.append(f"{self.col_uf} IN ({','.join('?' * len(self.ufs))})")
            params += list(self.ufs)
        if self.municipios:
            cond.append(f"{self.col_mun} IN ({','.join('?' * len(self.municipios))})")
            params += list(self.municipios)
        if self.contagem == "confirmados":
            cond.append("confirmado")
        elif self.contagem == "provaveis":
            cond.append("situacao <> 'Descartado'")
        if self.sexo:
            cond.append(f"sexo IN ({','.join('?' * len(self.sexo))})")
            params += list(self.sexo)
        if self.faixas:
            cond.append(f"faixa_etaria IN ({','.join('?' * len(self.faixas))})")
            params += list(self.faixas)
        return " AND ".join(cond), params


def _q(sql: str, params: list | None = None) -> pd.DataFrame:
    return conexao().execute(sql, params or []).df()


def anos(agravo: str) -> list[int]:
    df = _q(f"SELECT DISTINCT ano FROM {_fonte(agravo)} ORDER BY ano")
    return [int(a) for a in df["ano"]]


def ufs_presentes(agravo: str) -> list[str]:
    df = _q(f"""SELECT uf, count(*) n FROM (SELECT uf_res uf FROM {_fonte(agravo)}
                UNION ALL SELECT uf_not FROM {_fonte(agravo)}) WHERE uf IS NOT NULL
                GROUP BY uf ORDER BY n DESC""")
    return df["uf"].tolist()


def municipios_da_uf(ufs: list[str]) -> pd.DataFrame:
    if not ufs:
        return _q("SELECT cod6, municipio, uf FROM mun ORDER BY municipio")
    return _q(f"SELECT cod6, municipio, uf FROM mun WHERE uf IN ({','.join('?' * len(ufs))}) ORDER BY municipio", ufs)


def populacao(f: Filtro, ufs_base: list[str]) -> float:
    """Soma da população dos anos selecionados (pessoas-ano) da área filtrada."""
    if f.municipios:
        cond, params = f"cod6 IN ({','.join('?' * len(f.municipios))})", list(f.municipios)
    else:
        ufs = list(f.ufs) or ufs_base
        cond = f"cod6 IN (SELECT cod6 FROM mun WHERE uf IN ({','.join('?' * len(ufs))}))"
        params = ufs
    df = _q(f"SELECT sum(populacao) p FROM pop WHERE ano BETWEEN ? AND ? AND {cond}",
            [f.ano_ini, f.ano_fim] + params)
    return float(df["p"].iloc[0] or 0)


def indicadores(f: Filtro) -> dict:
    # os indicadores mostram notificações e confirmados juntos, então ignoram esse filtro
    f_todos = Filtro(**{**f.__dict__, "contagem": "todas"})
    w2, p2 = f_todos.where()
    df = _q(f"""SELECT count(*) notificacoes,
                       count(*) FILTER (WHERE confirmado) confirmados,
                       count(*) FILTER (WHERE situacao <> 'Descartado') provaveis,
                       count(*) FILTER (WHERE situacao = 'Descartado') descartados,
                       count(*) FILTER (WHERE situacao IN ('Em aberto/Ign.', 'Inconclusivo')) em_aberto,
                       count(*) FILTER (WHERE obito AND confirmado) obitos,
                       count(*) FILTER (WHERE hospitalizado = 'Sim' AND confirmado) hospitalizados,
                       count(*) FILTER (WHERE hospitalizado IN ('Sim','Não') AND confirmado) hosp_informado,
                       max(data_notificacao) ultima_notificacao
                FROM {_fonte(f.agravo)} WHERE {w2}""", p2)
    return df.iloc[0].to_dict()


def por_semana(f: Filtro) -> pd.DataFrame:
    w, p = f.where()
    return _q(f"""SELECT ano_epi, sem_epi, count(*) casos FROM {_fonte(f.agravo)}
                  WHERE {w} AND ano_epi BETWEEN ? AND ? GROUP BY 1, 2 ORDER BY 1, 2""",
              p + [f.ano_ini, f.ano_fim])


def por_mes(f: Filtro) -> pd.DataFrame:
    w, p = f.where()
    return _q(f"""SELECT date_trunc('month', data_referencia) mes, count(*) casos FROM {_fonte(f.agravo)}
                  WHERE {w} AND data_referencia IS NOT NULL AND year(data_referencia) BETWEEN ? AND ?
                  GROUP BY 1 ORDER BY 1""", p + [f.ano_ini - 1, f.ano_fim])


def por_municipio(f: Filtro) -> pd.DataFrame:
    w, p = f.where()
    return _q(f"""
        WITH c AS (
            SELECT {f.col_mun} cod6, count(*) casos, count(*) FILTER (WHERE obito) obitos
            FROM {_fonte(f.agravo)} WHERE {w} AND {f.col_mun} IS NOT NULL GROUP BY 1),
        pp AS (SELECT cod6, sum(populacao) pessoas_ano, avg(populacao) pop_media
               FROM pop WHERE ano BETWEEN ? AND ? GROUP BY 1)
        SELECT c.cod6, coalesce(m.municipio, 'Código ' || c.cod6) municipio, m.uf,
               c.casos, c.obitos, pp.pop_media populacao,
               c.casos * 100000.0 / nullif(pp.pessoas_ano, 0) incidencia
        FROM c LEFT JOIN mun m USING (cod6) LEFT JOIN pp USING (cod6)
        ORDER BY c.casos DESC, c.cod6""", p + [f.ano_ini, f.ano_fim])


def por_ano(f: Filtro) -> pd.DataFrame:
    w, p = f.where()
    return _q(f"""SELECT ano, count(*) casos, count(*) FILTER (WHERE obito) obitos
                  FROM {_fonte(f.agravo)} WHERE {w} GROUP BY 1 ORDER BY 1""", p)


def contagem(f: Filtro, coluna: str, ignorar_confirmado: bool = False) -> pd.DataFrame:
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", coluna):
        raise ValueError(f"Nome de coluna inválido: {coluna!r}")
    filtro = Filtro(**{**f.__dict__, "contagem": "todas"}) if ignorar_confirmado else f
    w, p = filtro.where()
    return _q(f"""SELECT coalesce(CAST("{coluna}" AS VARCHAR), '') valor, count(*) casos
                  FROM {_fonte(f.agravo)} WHERE {w} GROUP BY 1 ORDER BY 2 DESC, 1""", p)


def piramide(f: Filtro) -> pd.DataFrame:
    w, p = f.where()
    return _q(f"""SELECT faixa_etaria, sexo, count(*) casos FROM {_fonte(f.agravo)}
                  WHERE {w} AND faixa_etaria IS NOT NULL AND sexo IN ('Masculino','Feminino')
                  GROUP BY 1, 2 ORDER BY 1, 2""", p)


_COLUNAS_TABELA = """ano, data_notificacao, data_sintomas, sem_epi, uf_not, mun_not,
    uf_res, mun_res, idade, faixa_etaria, sexo, raca, classificacao, situacao, criterio_confirmacao,
    evolucao_caso, hospitalizado"""


def registros(f: Filtro, limite: int | None = 1000, todas_colunas: bool = False, inicio: int = 0) -> pd.DataFrame:
    w, p = f.where()
    cols = "* EXCLUDE (filename, file_row_number)" if todas_colunas else _COLUNAS_TABELA
    lim = f"LIMIT {int(limite)} OFFSET {max(0, int(inicio))}" if limite else ""
    # o desempate pela posição no arquivo deixa a ordem sempre igual: sem ele,
    # registros com a mesma data trocavam de lugar e se repetiam entre as páginas
    return _q(f"""SELECT {cols} FROM {_fonte(f.agravo, posicao=True)} WHERE {w}
                  ORDER BY data_notificacao DESC NULLS LAST, filename, file_row_number {lim}""", p)


def total_registros(f: Filtro) -> int:
    w, p = f.where()
    return int(_q(f"SELECT count(*) n FROM {_fonte(f.agravo)} WHERE {w}", p)["n"].iloc[0])
