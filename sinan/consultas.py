"""Consultas do dashboard, feitas com DuckDB direto nos arquivos Parquet.

O DuckDB agrega milhões de linhas em segundos, então o dashboard continua
rápido mesmo com o Brasil inteiro carregado.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from datetime import date

import duckdb
import pandas as pd

from . import processar
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


def anos_notificacao_cobertos(agravo: str, ufs: tuple[str, ...]) -> list[int]:
    """Anos de notificação do inventário que têm todas as ``ufs`` (ou ``BR``), em ordem crescente."""
    cobertos = set()
    for item in processar.ler_inventario().values():
        presentes = set(item.get("ufs", []))
        # sem ufs pedidas, só o Brasil inteiro conta (subconjunto vazio cobriria tudo)
        if item.get("agravo") == agravo and ("BR" in presentes or (ufs and set(ufs) <= presentes)):
            cobertos.add(int(item["ano"]))
    return sorted(cobertos)


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


# (id, campos originais obrigatórios, coluna inicial, coluna final, limite em dias)
PRAZOS = (("notificacao", ("DT_SIN_PRI", "DT_NOTIFIC"), "data_sintomas", "data_notificacao", 7),
          ("digitacao", ("DT_NOTIFIC", "DT_DIGITA"), "data_notificacao", "DT_DIGITA", 7),
          ("investigacao", ("DT_NOTIFIC", "DT_INVEST"), "data_notificacao", "DT_INVEST", 2),
          ("encerramento", ("DT_NOTIFIC", "DT_ENCERRA"), "data_notificacao", "DT_ENCERRA", 60))


def _data_sql(coluna: str) -> str:
    """Expressão SQL que vira DATE ou NULL (coluna de texto ``DT_*``; só nomes de constantes)."""
    d = (f"coalesce(try_cast({coluna} AS DATE), "
         f"try_strptime(trim(CAST({coluna} AS VARCHAR)), ['%Y%m%d', '%d/%m/%Y'])::DATE)")
    # mesma faixa das datas derivadas (processar._datas): fora dela vale como ilegível
    return f"(CASE WHEN {d} BETWEEN DATE '1900-01-01' AND current_date + 1 THEN {d} END)"


def anos_sem_coluna(agravo: str, coluna: str) -> list[int]:
    """Anos cujo arquivo Parquet não tem a coluna (lê só o esquema)."""
    import pyarrow.parquet as pq
    agravo = validar_agravo(agravo)
    pasta = PASTA_PARQUET / agravo
    return sorted(int(a.stem.rsplit("_", 1)[1]) for a in pasta.glob(f"{agravo}_*.parquet")
                  if coluna not in pq.read_schema(a).names)


def qualidade(f: Filtro, data_arquivos: date | None = None) -> dict:
    """Notificações dentro do prazo, entre as fichas com as duas datas válidas (ver docs: Sobre os dados)."""
    f_todos = Filtro(**{**f.__dict__, "contagem": "todas"})
    w, p = f_todos.where()
    fonte = _fonte(f.agravo)
    existentes = set(colunas(f.agravo))
    referencia = data_arquivos or conexao().execute(f"SELECT max(data_notificacao) FROM {fonte}").fetchone()[0]
    cols, params, disponiveis = ["count(*)"], [], []
    for id_, campos, ini, fim, limite in PRAZOS:
        if not set(campos) <= existentes:
            continue
        dias = f"date_diff('day', {_data_sql(ini) if ini.startswith('DT_') else ini}, " \
               f"{_data_sql(fim) if fim.startswith('DT_') else fim})"
        cols += [f"count(*) FILTER (WHERE {dias} >= 0)", f"count(*) FILTER (WHERE {dias} BETWEEN 0 AND {limite})"]
        disponiveis.append(id_)
        if id_ == "encerramento":
            sem = ("NULLIF(trim(CAST(DT_ENCERRA AS VARCHAR)), '') IS NULL "
                   "AND date_diff('day', data_notificacao, ?) > 60")
            params.append(referencia)
            sem_anos = anos_sem_coluna(f.agravo, "DT_ENCERRA")
            if sem_anos:
                sem += f" AND ano NOT IN ({','.join('?' * len(sem_anos))})"
                params += sem_anos
            cols.append(f"count(*) FILTER (WHERE {sem})")
    linha = conexao().execute(f"SELECT {', '.join(cols)} FROM {fonte} WHERE {w}", params + p).fetchone()
    prazos, k = [], 1
    for id_, _, _, _, limite in PRAZOS:
        if id_ not in disponiveis:
            prazos.append({"id": id_, "limite": limite, "disponivel": False})
            continue
        base, no_prazo = linha[k], linha[k + 1]
        k += 2
        sem_enc = 0
        if id_ == "encerramento":
            sem_enc, k = linha[k], k + 1
            base += sem_enc  # sem data de encerramento há mais de 60 dias: fora do prazo
        prazos.append({"id": id_, "limite": limite, "disponivel": True, "base": base, "no_prazo": no_prazo,
                       "pct": round(100 * no_prazo / base, 1) if base else None, "sem_encerramento": sem_enc})
    return {"notificacoes": linha[0], "referencia": referencia, "prazos": prazos}


def por_semana(f: Filtro) -> pd.DataFrame:
    w, p = f.where()
    return _q(f"""SELECT ano_epi, sem_epi, count(*) casos FROM {_fonte(f.agravo)}
                  WHERE {w} AND ano_epi BETWEEN ? AND ? GROUP BY 1, 2 ORDER BY 1, 2""",
              p + [f.ano_ini, f.ano_fim])


def semana_por_municipio(f: Filtro, semanas: tuple[int, ...]) -> pd.DataFrame:
    """Casos por município, ano e semana epidemiológica; quem chama escolhe a linha (sem filtro de ``ano_epi``)."""
    w, p = f.where()
    return _q(f"""SELECT {f.col_mun} cod6, ano_epi, sem_epi, count(*) casos FROM {_fonte(f.agravo)}
                  WHERE {w} AND {f.col_mun} IS NOT NULL AND sem_epi IN ({','.join('?' * len(semanas))})
                  GROUP BY 1, 2, 3 ORDER BY 1, 2, 3""", p + list(semanas))


def totais_por_municipio(f: Filtro) -> pd.DataFrame:
    """Casos por município e ano epidemiológico (totais anuais)."""
    w, p = f.where()
    return _q(f"""SELECT {f.col_mun} cod6, ano_epi, count(*) casos FROM {_fonte(f.agravo)}
                  WHERE {w} AND {f.col_mun} IS NOT NULL GROUP BY 1, 2 ORDER BY 1, 2""", p)


def ultima_notificacao(agravo: str) -> date | None:
    return conexao().execute(f"SELECT max(data_notificacao) FROM {_fonte(agravo)}").fetchone()[0]


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
