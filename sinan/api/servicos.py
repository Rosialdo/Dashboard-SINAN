"""Cálculos usados por mais de uma rota (indicadores, municípios, variáveis da ficha)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .. import agravos as cat
from .. import consultas as cq
from .. import rotulos
from ..processar import CAMPOS_HOSP
from ..tabnet import VariavelDef, ler_def
from . import cache
from .respostas import registros

# ------------------------------------------------------------- privacidade
# no site publicado, com um município escolhido, estas informações não aparecem:
# num município pequeno elas poderiam identificar a pessoa (decisão de 19/11/2026)
CAMPOS_SENSIVEIS = {"CS_GESTANT", "DOENCA_TRA", "EVOLUCAO", "TPALTA_N", "SITUA_ENCE", *CAMPOS_HOSP}
AVISO_PRIVACIDADE = "Não mostrado no recorte por município, para proteger a privacidade das pessoas."


def sem_sensiveis(ind: dict) -> dict:
    """Indicadores sem óbitos, letalidade e hospitalização."""
    return {**ind, "obitos": None, "letalidade": None, "hospitalizados": None, "hosp_informado": 0}


# ------------------------------------------------------------- indicadores
def indicadores(f: cq.Filtro, area: tuple[str, ...]) -> dict:
    """Números do topo das telas: notificações, casos, incidência, letalidade..."""
    ind = cq.indicadores(f)
    # sem população que corresponda aos casos (sexo, faixa, notificação) não há incidência
    pop = cq.populacao(f, list(area)) if incidencia_disponivel(f) else 0.0
    casos = ind["notificacoes"] if f.contagem == "todas" else ind[f.contagem]
    ind["casos"] = casos
    ind["incidencia"] = casos * 1e5 / pop if pop else None
    ind["letalidade"] = 100 * ind["obitos"] / ind["confirmados"] if ind["confirmados"] else None
    ind["n_anos"] = f.ano_fim - f.ano_ini + 1
    return ind


# ------------------------------------------------------------- municípios
def taxa_suavizada(casos: pd.Series, pa: pd.Series) -> pd.Series:
    """Incidência por 100 mil hab./ano suavizada pelo método bayesiano empírico (Marshall, 1991)."""
    c = pd.to_numeric(casos, errors="coerce").astype(float)
    p = pd.to_numeric(pa, errors="coerce").astype(float)
    ok = np.isfinite(p) & (p > 0) & np.isfinite(c)
    if not ok.any():
        return pd.Series(float("nan"), index=casos.index)
    c, p = c[ok], p[ok]
    m = c.sum() / p.sum()  # taxa média da área
    r = c / p
    s2 = (p * (r - m) ** 2).sum() / p.sum()
    a = max(s2 - m / (p.sum() / len(p)), 0.0)
    peso = a / (a + m / p) if m > 0 else 0.0 * p  # m == 0: evita 0/0
    out = pd.Series(float("nan"), index=casos.index)
    out[ok] = (m + peso * (r - m)) * 1e5
    return out


def incidencia_disponivel(f: cq.Filtro) -> bool:
    """A população do denominador é a total do município, por residência: não vale com sexo, faixa ou notificação."""
    return f.por_residencia and not (f.sexo or f.faixas)


def suavizada_disponivel(f: cq.Filtro) -> bool:
    """A suavização também precisa da população de toda a área: não vale com município escolhido."""
    return incidencia_disponivel(f) and not f.municipios


def tabela_municipios(f: cq.Filtro, area: tuple[str, ...]) -> pd.DataFrame:
    """Todos os municípios da área (inclusive os sem casos), com casos e incidência."""
    dados = cq.por_municipio(f)
    base = cq.municipios_da_uf(list(area))
    if f.municipios:
        base = base[base["cod6"].isin(f.municipios)]
    t = base.merge(dados.drop(columns=["municipio", "uf", "populacao", "incidencia"]), on="cod6", how="left")
    t[["casos", "obitos"]] = t[["casos", "obitos"]].fillna(0).astype(int)
    pop = cq._q("SELECT cod6, avg(populacao) populacao, sum(populacao) pa FROM pop "
                "WHERE ano BETWEEN ? AND ? GROUP BY 1", [f.ano_ini, f.ano_fim])
    t = t.merge(pop, on="cod6", how="left")
    # sem população: vazio, não infinito
    t["incidencia"] = t["casos"] * 1e5 / t["pa"].where(t["pa"] > 0) if incidencia_disponivel(f) else None
    t["incidencia_suavizada"] = taxa_suavizada(t["casos"], t["pa"]) if suavizada_disponivel(f) else None
    return t.drop(columns="pa").sort_values(["casos", "incidencia", "cod6"], ascending=[False, False, True])


def nomes_municipios() -> dict[str, str]:
    """Código IBGE (6 dígitos) -> "Município (UF)"."""
    def calcular():
        df = cq._q("SELECT cod6, municipio || ' (' || uf || ')' n FROM mun")
        return dict(zip(df["cod6"], df["n"], strict=True))
    return cache.memo("nomes_mun", calcular)


def trocar_codigos_municipio(df: pd.DataFrame) -> pd.DataFrame:
    nomes = nomes_municipios()
    for col in ("mun_not", "mun_res"):
        if col in df:
            df[col] = df[col].map(lambda c: nomes.get(c, c))
    return df


# ------------------------------------------------------------- textos simples
# colunas derivadas que podem ter "Ign/Branco" e parecidos (ver rotulos.valor_simples)
COLS_TEXTO = ("sexo", "raca", "faixa_etaria", "classificacao", "situacao", "criterio_confirmacao",
              "evolucao_caso", "hospitalizado")


def simplificar(df: pd.DataFrame, ordenar: bool = True) -> pd.DataFrame:
    """Troca os rótulos de "sem resposta" por "Não informado" e soma os que viraram iguais."""
    if df.empty:
        return df
    df = df.assign(valor=df["valor"].map(rotulos.valor_simples))
    extras = {c: "min" for c in df.columns if c not in ("valor", "casos")}
    df = df.groupby("valor", as_index=False, sort=False).agg({"casos": "sum", **extras})
    return df.sort_values(["casos", "valor"], ascending=[False, True]) if ordenar else df


def contagem(f: cq.Filtro, coluna: str, ignorar_confirmado: bool = False) -> list[dict]:
    return registros(simplificar(cq.contagem(f, coluna, ignorar_confirmado)))


def textos_simples(df: pd.DataFrame) -> pd.DataFrame:
    for col in COLS_TEXTO:
        if col in df:
            df[col] = df[col].map(rotulos.valor_simples)
    return df


# ------------------------------------------------------------- variáveis da ficha
# geografia já está no mapa e nos filtros; ID_AGRAVO é igual em todas as linhas do arquivo
_CAMPOS_FORA = {"ID_AGRAVO", "ID_MUNICIP", "ID_MN_RESI", "ID_UNIDADE", "SG_UF", "SG_UF_NOT",
                "ID_REGIONA", "ID_RG_RESI", "ID_PAIS"}
_CNV_FORA = ("munic", "uf", "regiao", "rmetri", "nhe", "anos", "meses", "semana", "trime", "mun", "capital")


def variaveis(agravo: str) -> list[VariavelDef]:
    """Variáveis do .def do TabNet que existem nos dados baixados.

    A posição nesta lista é o ``id`` usado pela interface.
    """
    existentes = set(cq.colunas(agravo))
    lista = [v for v in ler_def(cat.obter(agravo).arquivo_def or "")
             if v.campo in existentes and v.campo not in _CAMPOS_FORA and not v.cnv.lower().startswith(_CNV_FORA)]
    # a ficha genérica (notindivinet.def) traz uma versão do campo para cada doença
    # ("Evolução AIDS Adulto", "Clas. Fin. PFA"...); fica só a de "Outros Agravos"
    genericos = {v.campo for v in lista if "outros agravos" in v.rotulo.lower()}
    return [v for v in lista if v.campo not in genericos or "outros agravos" in v.rotulo.lower()]


def lista_variaveis(agravo: str) -> list[dict]:
    """Variáveis com nome amigável e grupo, já na ordem em que aparecem na tela."""
    vs = variaveis(agravo)
    itens = [{"id": i, "nome": rotulos.nome_amigavel(v.rotulo, v.campo, v.cnv),
              "grupo": rotulos.grupo(v.rotulo, v.campo), "rotulo": v.rotulo, "campo": v.campo}
             for i, v in enumerate(vs)]
    # dois itens com o mesmo nome: acrescenta o rótulo do TabNet para diferenciar
    repetidos: dict[str, int] = {}
    for it in itens:
        repetidos[it["nome"]] = repetidos.get(it["nome"], 0) + 1
    for it in itens:
        if repetidos[it["nome"]] > 1:
            it["nome"] = f"{it['nome']} – {it['rotulo']}"
    ordem = {g: i for i, g in enumerate(rotulos.GRUPOS)}
    preferido = {i for i, v in enumerate(vs) if v.cnv.lower() in rotulos.PREFERIDOS}
    return sorted(itens, key=lambda it: (ordem.get(it["grupo"], len(ordem)), it["id"] not in preferido, it["id"]))
