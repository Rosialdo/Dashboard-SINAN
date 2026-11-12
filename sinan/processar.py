"""Tratamento: .dbc nacional -> Parquet filtrado por UF, com colunas prontas.

Mantém todas as colunas originais (em texto, nomes em MAIÚSCULAS) e acrescenta
colunas derivadas (nomes em minúsculas) usadas pelo dashboard.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from . import agravos as cat
from .config import ARQ_INVENTARIO, PASTA_DADOS, PASTA_PARQUET, UF_COD, UFS
from .dbc import dbc_para_dbf
from .dbf import colunas_dbf, iterar_dbf
from .tabnet import Conversor, conversor_do_campo, ler_cnv

FAIXAS = ["<1", "1-4", "5-9", "10-14", "15-19", "20-29", "30-39",
          "40-49", "50-59", "60-69", "70-79", "80+"]
_LIMITES = [0, 1, 5, 10, 15, 20, 30, 40, 50, 60, 70, 80, 200]

SEXO = {"M": "Masculino", "F": "Feminino"}
RACA = {"1": "Branca", "2": "Preta", "3": "Amarela", "4": "Parda", "5": "Indígena"}
CAMPOS_HOSP = ["HOSPITALIZ", "ATE_HOSP", "HOSPITAL"]

# colunas derivadas e seus tipos (o mesmo esquema em todos os arquivos)
ESQUEMA_DERIVADO = {
    "agravo": pa.string(), "ano": pa.int16(),
    "data_notificacao": pa.date32(), "data_sintomas": pa.date32(), "data_referencia": pa.date32(),
    "ano_epi": pa.int16(), "sem_epi": pa.int8(), "mes": pa.int8(),
    "uf_not": pa.string(), "mun_not": pa.string(), "uf_res": pa.string(), "mun_res": pa.string(),
    "idade": pa.float32(), "faixa_etaria": pa.string(), "sexo": pa.string(), "raca": pa.string(),
    "classificacao": pa.string(), "situacao": pa.string(), "confirmado": pa.bool_(),
    "criterio_confirmacao": pa.string(), "evolucao_caso": pa.string(), "obito": pa.bool_(),
    "hospitalizado": pa.string(),
}


# ------------------------------------------------------------- utilitários
def _datas(s: pd.Series | None, n: int) -> pd.Series:
    if s is None:
        return pd.Series(pd.NaT, index=range(n), dtype="datetime64[ns]")
    d = pd.to_datetime(s, format="%Y%m%d", errors="coerce")
    limite = pd.Timestamp(date.today()) + pd.Timedelta(days=1)
    return d.where((d >= pd.Timestamp("1900-01-01")) & (d <= limite))


def semana_epidemiologica(d: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Ano e semana epidemiológica (semana de domingo a sábado; a semana 1 é a
    primeira com pelo menos 4 dias no ano, regra usada pelo Ministério da Saúde)."""
    dias_desde_domingo = (d.dt.day_of_week + 1) % 7
    quarta = d - pd.to_timedelta(dias_desde_domingo, unit="D") + pd.Timedelta(days=3)
    ano = quarta.dt.year
    semana = (quarta.dt.day_of_year - 1) // 7 + 1
    return ano, semana


def idade_em_anos(s: pd.Series | None, n: int) -> pd.Series:
    """NU_IDADE_N: 1º dígito é a unidade (1 hora, 2 dia, 3 mês, 4 ano)."""
    if s is None:
        return pd.Series(np.nan, index=range(n), dtype="float32")
    v = pd.to_numeric(s, errors="coerce")
    unidade, valor = v // 1000, v % 1000
    anos = np.select(
        [unidade == 4, unidade.isin([1, 2]), unidade == 3],
        [valor, 0.0, (valor / 12).clip(upper=0.99)],
        default=np.nan,
    ).astype("float64")
    anos = pd.Series(anos, index=s.index)
    return anos.where(anos <= 120)


def _mapear(conv: Conversor | None, serie: pd.Series | None, padrao: dict[str, str], n: int) -> pd.Series:
    if serie is None:
        return pd.Series("Ign/Branco", index=range(n), dtype="object")
    if conv is not None:
        return conv.mapear(serie)
    return serie.map(padrao).astype("object").fillna("Ign/Branco")


def _conversor(agravo: cat.Agravo, campo: str) -> Conversor | None:
    return conversor_do_campo(agravo.arquivo_def, campo)


def _uf_de(cod_uf: pd.Series | None, mun: pd.Series | None, n: int) -> pd.Series:
    base = cod_uf if cod_uf is not None else pd.Series(None, index=range(n), dtype="object")
    if mun is not None:
        base = base.fillna(mun.str[:2])
    return base.map(UFS)


def _sem_zeros(s: pd.Series) -> pd.Series:
    return s.str.lstrip("0").replace("", "0")


# ------------------------------------------------------------ derivadas
def derivar(df: pd.DataFrame, agravo: cat.Agravo, ano: int) -> pd.DataFrame:
    n = len(df)
    g = df.get
    out = pd.DataFrame(index=df.index)
    out["agravo"] = agravo.codigo
    out["ano"] = ano

    dt_not = _datas(g("DT_NOTIFIC"), n)
    dt_sin = _datas(g("DT_SIN_PRI"), n)
    dt_diag = _datas(g("DT_DIAG"), n)
    dt_ref = dt_sin.fillna(dt_diag).fillna(dt_not)
    out["data_notificacao"] = dt_not.dt.date
    out["data_sintomas"] = dt_sin.dt.date
    out["data_referencia"] = dt_ref.dt.date
    ano_epi, sem_epi = semana_epidemiologica(dt_ref)
    out["ano_epi"] = ano_epi.astype("Int16")
    out["sem_epi"] = sem_epi.astype("Int8")
    out["mes"] = dt_ref.dt.month.astype("Int8")

    out["mun_not"] = g("ID_MUNICIP")
    out["mun_res"] = g("ID_MN_RESI")
    out["uf_not"] = _uf_de(g("SG_UF_NOT"), g("ID_MUNICIP"), n)
    out["uf_res"] = _uf_de(g("SG_UF"), g("ID_MN_RESI"), n)

    idade = idade_em_anos(g("NU_IDADE_N"), n)
    out["idade"] = idade
    out["faixa_etaria"] = pd.cut(idade, _LIMITES, right=False, labels=FAIXAS).astype("object")
    out["sexo"] = (g("CS_SEXO") if "CS_SEXO" in df else pd.Series(None, index=df.index)).map(SEXO).fillna("Ignorado")
    out["raca"] = _mapear(ler_cnv("raça.cnv") or _conversor(agravo, "CS_RACA"), g("CS_RACA"), RACA, n)

    # classificação final e situação (confirmado / descartado / ...)
    classi = g("CLASSI_FIN")
    sem_classificacao = classi is None or classi.isna().all()
    conv_cl = _conversor(agravo, "CLASSI_FIN")
    if classi is not None:
        out["classificacao"] = _mapear(conv_cl, classi, {}, n)
    else:
        out["classificacao"] = "Sem classificação"

    if agravo.todos_casos or sem_classificacao:
        out["situacao"] = "Notificado"
        out["confirmado"] = True
    else:
        rot = out["classificacao"].str.lower()
        cod = _sem_zeros(classi.fillna(""))
        vazio = classi.isna() | rot.str.startswith("ign") | rot.str.contains("branco")
        descartado = rot.str.contains("descart")
        if agravo.codigo == "DENG":
            descartado |= cod.eq("13")  # 13 = chikungunya na ficha de dengue
        inconclusivo = rot.str.contains("inconclus")
        if agravo.confirmados is not None:
            confirmado = cod.isin({c.lstrip("0") for c in agravo.confirmados})
        else:
            confirmado = ~(vazio | descartado | inconclusivo | rot.str.startswith("código"))
        situacao = np.select(
            [confirmado, descartado, inconclusivo, vazio],
            ["Confirmado", "Descartado", "Inconclusivo", "Em aberto/Ign."],
            default="Outra classificação",
        )
        out["situacao"] = situacao
        out["confirmado"] = confirmado.values

    out["criterio_confirmacao"] = _mapear(_conversor(agravo, "CRITERIO"), g("CRITERIO"), {}, n) if "CRITERIO" in df else "Ign/Branco"

    campo_evo = agravo.campo_evolucao if agravo.campo_evolucao in df else "EVOLUCAO"
    if campo_evo in df:
        evo = _mapear(_conversor(agravo, campo_evo), df[campo_evo], {}, n)
        rot = evo.str.lower()
        out["evolucao_caso"] = evo
        out["obito"] = (rot.str.startswith("óbito") | rot.str.startswith("obito")) & \
            ~rot.str.contains("outra") & ~rot.str.contains("investiga")
    else:
        out["evolucao_caso"] = "Sem informação"
        out["obito"] = False

    campo_h = next((c for c in CAMPOS_HOSP if c in df), None)
    if campo_h:
        out["hospitalizado"] = df[campo_h].map({"1": "Sim", "2": "Não"}).fillna("Ign/Branco")
    else:
        out["hospitalizado"] = "Sem informação"
    return out


def _tabela_arrow(df: pd.DataFrame, derivadas: pd.DataFrame, colunas_brutas: list[str]) -> pa.Table:
    arrays, campos = [], []
    for c in colunas_brutas:
        valores = df[c] if c in df else pd.Series(None, index=df.index, dtype="object")
        arrays.append(pa.array(valores, type=pa.string(), from_pandas=True))
        # o DuckDB não diferencia maiúsculas: uma coluna original com o mesmo nome
        # de uma derivada (ex.: EVOLUCAO x evolucao) ganharia prioridade e confundiria
        nome = f"{c}_ORIGINAL" if c.lower() in ESQUEMA_DERIVADO else c
        campos.append(pa.field(nome, pa.string()))
    for nome, tipo in ESQUEMA_DERIVADO.items():
        col = derivadas[nome]
        if hasattr(col, "dtype") and str(col.dtype) in ("Int8", "Int16"):
            col = col.astype("object").where(col.notna(), None)
        arrays.append(pa.array(col, type=tipo, from_pandas=True))
        campos.append(pa.field(nome, tipo))
    return pa.Table.from_arrays(arrays, schema=pa.schema(campos))


# ------------------------------------------------------------- inventário
def ler_inventario() -> dict:
    try:
        return json.loads(ARQ_INVENTARIO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _salvar_inventario(inv: dict) -> None:
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    ARQ_INVENTARIO.write_text(json.dumps(inv, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def caminho_parquet(agravo: str, ano: int) -> Path:
    return PASTA_PARQUET / agravo / f"{agravo}_{ano}.parquet"


# nomes antigos das colunas derivadas (versão 1.0), que colidiam com as originais
_RENOMEAR_V1 = {"dt_notific": "data_notificacao", "dt_sintomas": "data_sintomas", "dt_ref": "data_referencia",
                "criterio": "criterio_confirmacao", "evolucao": "evolucao_caso"}


def migrar_arquivos() -> int:
    """Atualiza Parquets gravados pela versão 1.0 para os nomes de colunas atuais."""
    migrados = 0
    if not PASTA_PARQUET.exists():
        return 0
    for arq in PASTA_PARQUET.glob("*/*.parquet"):
        nomes = pq.read_schema(arq).names
        if not any(n in _RENOMEAR_V1 for n in nomes):
            continue
        tabela = pq.read_table(arq)
        tabela = tabela.rename_columns([_RENOMEAR_V1.get(n, n) for n in tabela.column_names])
        temporario = arq.with_suffix(".tmp")
        pq.write_table(tabela, temporario, compression="zstd")
        temporario.replace(arq)
        migrados += 1
    return migrados


def remover(agravo: str, ano: int) -> None:
    caminho_parquet(agravo, ano).unlink(missing_ok=True)
    inv = ler_inventario()
    inv.pop(f"{agravo}_{ano}", None)
    _salvar_inventario(inv)


# ------------------------------------------------------------- principal
def processar_dbc(
    caminho_dbc: Path,
    agravo_cod: str,
    ano: int,
    ufs: list[str],
    info_ftp: dict | None = None,
    progresso: Callable[[float, str], None] | None = None,
) -> int:
    """Converte um .dbc em Parquet. Devolve o número de registros gravados."""
    agravo = cat.obter(agravo_cod)
    avisar = progresso or (lambda f, m: None)
    caminho_dbf = caminho_dbc.with_suffix(".dbf")
    avisar(0.0, "descompactando")
    dbc_para_dbf(caminho_dbc, caminho_dbf)

    try:
        colunas = colunas_dbf(caminho_dbf)
        todo_brasil = "BR" in ufs
        codigos = {UF_COD[u].encode() for u in ufs if u in UF_COD}

        def filtro(cols: dict[str, np.ndarray]) -> np.ndarray:
            mascara = None
            for campo, arr in cols.items():
                prefixos = np.char.strip(arr) if campo.startswith("SG_UF") else np.char.ljust(arr, 6).astype("S2")
                m = np.isin(prefixos, list(codigos))
                mascara = m if mascara is None else (mascara | m)
            return mascara

        campos_filtro = [c for c in ("SG_UF", "SG_UF_NOT") if c in colunas] or \
                        [c for c in ("ID_MN_RESI", "ID_MUNICIP") if c in colunas]
        if not todo_brasil and not campos_filtro:
            raise ValueError("o arquivo não tem campo de UF nem de município, então não dá para "
                             "filtrar por UF. Escolha \"BR\" (Brasil inteiro) para este agravo.")

        destino = caminho_parquet(agravo.codigo, ano)
        destino.parent.mkdir(parents=True, exist_ok=True)
        temporario = destino.with_suffix(".tmp")
        escritor = None
        total = 0
        lotes = iterar_dbf(
            caminho_dbf,
            filtro=None if todo_brasil else filtro,
            campos_filtro=campos_filtro,
            progresso=lambda f: avisar(f, "lendo registros"),
        )
        try:
            for lote in lotes:
                lote = lote.reset_index(drop=True)
                tabela = _tabela_arrow(lote, derivar(lote, agravo, ano), colunas)
                if escritor is None:
                    escritor = pq.ParquetWriter(temporario, tabela.schema, compression="zstd")
                escritor.write_table(tabela)
                total += len(lote)
            if escritor is None:  # nenhum registro para as UFs escolhidas
                vazio = pd.DataFrame(columns=colunas, dtype="object")
                tabela = _tabela_arrow(vazio, derivar(vazio, agravo, ano), colunas)
                escritor = pq.ParquetWriter(temporario, tabela.schema, compression="zstd")
                escritor.write_table(tabela)
        except BaseException:
            if escritor is not None:
                escritor.close()
                escritor = None
            temporario.unlink(missing_ok=True)
            raise
        finally:
            lotes.close()  # libera o arquivo mapeado (no Windows, senão não dá para apagar)
            if escritor is not None:
                escritor.close()
        temporario.replace(destino)
    finally:
        caminho_dbf.unlink(missing_ok=True)

    inv = ler_inventario()
    info = info_ftp or {}
    inv[f"{agravo.codigo}_{ano}"] = {
        "agravo": agravo.codigo,
        "ano": ano,
        "registros": total,
        "ufs": sorted(ufs),
        "situacao": info.get("situacao", "?"),
        "arquivo": info.get("arquivo", caminho_dbc.name),
        "data_ftp": info.get("data_ftp", ""),
        "processado_em": datetime.now().isoformat(timespec="seconds"),
    }
    _salvar_inventario(inv)
    avisar(1.0, "concluído")
    return total
