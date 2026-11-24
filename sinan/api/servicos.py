"""Cálculos usados por mais de uma rota (indicadores, municípios, variáveis da ficha)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

import numpy as np
import pandas as pd

from .. import agravos as cat
from .. import config, rotulos
from .. import consultas as cq
from ..processar import CAMPOS_HOSP, data_dos_arquivos, semana_epidemiologica
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


# ------------------------------------------------------------- canal endêmico


def anos_epi_cobertos(anos_notificacao: list[int]) -> list[int]:
    """Anos epidemiológicos Y com Y e Y+1 baixados (parte dos casos de Y chega em janeiro de Y+1)."""
    ok = set(anos_notificacao)
    return sorted(y for y in ok if y + 1 in ok)


CANAL_ANOS = 7          # anos anteriores usados como histórico
CANAL_MINIMO = 5        # menos anos válidos que isso: sem canal
CANAL_EPIDEMICO = 1.5   # ano com total acima disso x mediana é epidêmico


def anos_do_canal(totais: pd.DataFrame, ano_ref: int, cobertos: list[int] | pd.DataFrame) -> pd.DataFrame:
    """Anos do histórico de cada série, marcando os epidêmicos; só séries com anos suficientes."""
    cob = pd.DataFrame({"ano_epi": cobertos}) if isinstance(cobertos, list) else cobertos
    grupos = [c for c in cob.columns if c != "ano_epi"]
    ch = grupos or ["_g"]
    cob = cob.assign(_g=0) if not grupos else cob
    cand = cob[cob["ano_epi"] < ano_ref].sort_values([*ch, "ano_epi"]).groupby(ch).tail(CANAL_ANOS)
    tot = totais.assign(_g=0) if not grupos else totais
    cand = cand.merge(tot[[*ch, "ano_epi", "casos"]], on=[*ch, "ano_epi"], how="left")
    cand["casos"] = cand["casos"].fillna(0)
    med = cand.groupby(ch)["casos"].transform("median")  # uma vez, sobre os candidatos iniciais
    cand["excluido"] = (med > 0) & (cand["casos"] > CANAL_EPIDEMICO * med)
    validos = (~cand["excluido"]).groupby([cand[c] for c in ch]).transform("sum")
    cand = cand[validos >= CANAL_MINIMO]
    return cand[[*grupos, "ano_epi", "excluido"]].sort_values([*grupos, "ano_epi"]).reset_index(drop=True)


def faixa_esperada(semana: pd.DataFrame, anos: pd.DataFrame,
                   semanas: tuple[int, ...] = tuple(range(1, 54))) -> pd.DataFrame:
    """Quartis (lineares) dos casos por semana nos anos usados de cada série; semana sem registro vale 0."""
    grupos = [c for c in anos.columns if c not in ("ano_epi", "excluido")]
    ch = grupos or ["_g"]
    usados = anos.loc[~anos["excluido"], [*grupos, "ano_epi"]]
    if usados.empty:  # sem histórico suficiente
        return pd.DataFrame(columns=[*grupos, "sem_epi", "q1", "mediana", "q3"])
    sem = semana.assign(_g=0) if not grupos else semana
    usados = usados.assign(_g=0) if not grupos else usados
    calc = sorted({min(w, 52) for w in semanas})  # a 53 usa a faixa da 52
    base = usados.merge(pd.DataFrame({"sem_epi": calc}), how="cross")
    base = base.merge(sem[[*ch, "ano_epi", "sem_epi", "casos"]], on=[*ch, "ano_epi", "sem_epi"], how="left")
    base["casos"] = base["casos"].fillna(0)
    q = base.groupby([*ch, "sem_epi"])["casos"].quantile([0.25, 0.5, 0.75], interpolation="linear").unstack()
    q.columns = ["q1", "mediana", "q3"]
    q = q.reset_index().rename(columns={"sem_epi": "_s"})
    pedidas = pd.DataFrame({"sem_epi": list(semanas), "_s": [min(w, 52) for w in semanas]})
    q = q.merge(pedidas, on="_s").drop(columns="_s")
    return q[[*grupos, "sem_epi", "q1", "mediana", "q3"]].sort_values([*grupos, "sem_epi"]).reset_index(drop=True)


def ufs_da_serie(f: cq.Filtro, area: tuple[str, ...]) -> tuple[str, ...]:
    """UFs que a contagem da série cobre: as escolhidas, as dos municípios escolhidos ou a área."""
    if f.ufs:
        return f.ufs
    if f.municipios:
        return tuple(sorted({config.UFS[m[:2]] for m in f.municipios if m[:2] in config.UFS}))
    return area


def filtro_da_serie(f: cq.Filtro, area: tuple[str, ...]) -> cq.Filtro:
    """Sem UF nem município, restringe à área cuja cobertura é conferida."""
    return f if f.ufs or f.municipios else replace(f, ufs=area)


def canal_endemico(f: cq.Filtro, area: tuple[str, ...]) -> tuple[dict | None, str | None]:
    """(canal, motivo): faixa esperada por semana; sem ela, "sem_cobertura" (menos de 5 anos
    anteriores baixados) ou "poucos_anos_validos" (menos de 5 depois de tirar os epidêmicos)."""
    ano = f.ano_fim
    baixados = cq.anos_notificacao_cobertos(f.agravo, ufs_da_serie(f, area))
    candidatos = sorted(a for a in anos_epi_cobertos(baixados) if a < ano)[-CANAL_ANOS:]  # ano sem dado não vira zero
    if len(candidatos) < CANAL_MINIMO:
        return None, "sem_cobertura"
    sem = cq.por_semana(replace(filtro_da_serie(f, area), ano_ini=min(candidatos), ano_fim=ano))
    tot = sem.groupby("ano_epi", as_index=False)["casos"].sum()
    anos = anos_do_canal(tot, ano, candidatos)
    faixa = faixa_esperada(sem, anos)
    if faixa.empty:
        return None, "poucos_anos_validos"
    return {"ano": ano, "ano_coberto": ano in baixados,
            "anos": [int(a) for a in anos.loc[~anos["excluido"], "ano_epi"]],
            "excluidos": [int(a) for a in anos.loc[anos["excluido"], "ano_epi"]],
            "semanas": registros(faixa)}, None


# ------------------------------------------------------------- alerta por município
def data_referencia(agravo: str) -> date | None:
    """A mais antiga entre a data dos arquivos e a última notificação (a que existir)."""
    if not cq.tem_dados(agravo):  # sem arquivo baixado não há semana de referência
        return None
    return min((d for d in (data_dos_arquivos(agravo), cq.ultima_notificacao(agravo)) if d), default=None)


def semana_referencia(data: date) -> dict:
    """Semana epidemiológica (domingo a sábado) que contém ``data`` menos 7 dias: já terminou no calendário."""
    d = pd.Timestamp(data - timedelta(days=7))
    ano, semana = semana_epidemiologica(pd.Series([d]))
    inicio = (d - pd.Timedelta(days=(d.day_of_week + 1) % 7)).date()
    return {"ano": int(ano.iloc[0]), "semana": int(semana.iloc[0]), "inicio": inicio, "fim": inicio + timedelta(days=6)}


def semana_coberta(s: dict, data_ref: date, anos_notificacao: list[int]) -> bool:
    """Todos os anos de notificação em que caem fichas da semana estão baixados."""
    return set(range(s["inicio"].year, data_ref.year + 1)) <= set(anos_notificacao)


def nivel_alerta(casos: pd.Series, q1: pd.Series, q3: pd.Series) -> pd.Series:
    """"acima" (casos > q3), "abaixo" (casos < q1) ou "dentro" da faixa histórica."""
    return pd.Series(np.select([casos > q3, casos < q1], ["acima", "abaixo"], "dentro"), index=casos.index)


def alerta_municipios(f: cq.Filtro, area: tuple[str, ...]) -> tuple[dict | None, pd.DataFrame]:
    """(semana de referência, nível de cada município da área); ``alerta`` None quando falta histórico."""
    colunas = ["cod6", "casos_semana", "q1", "esperado_ate", "alerta", "alerta_motivo", "faixa_zero"]
    vazio = (None, pd.DataFrame(columns=colunas))
    data = data_referencia(f.agravo)
    if data is None:
        return vazio
    s = semana_referencia(data)
    ano, sem = s["ano"], s["semana"]
    if not f.ano_ini <= ano <= f.ano_fim:
        return vazio
    base = cq.municipios_da_uf(list(area))
    if f.municipios:
        base = base[base["cod6"].isin(f.municipios)]
    baixados = {uf: cq.anos_notificacao_cobertos(f.agravo, (uf,)) for uf in base["uf"].unique()}
    por_uf = pd.DataFrame([(uf, a) for uf, b in baixados.items() for a in anos_epi_cobertos(b)],
                          columns=["uf", "ano_epi"])
    cobertos = base[["cod6", "uf"]].merge(por_uf, on="uf")[["cod6", "ano_epi"]]
    cand = cobertos[cobertos["ano_epi"] < ano]
    if cand.empty:
        return vazio
    # a consulta começa no menor candidato de todas as UFs: ano não consultado não pode virar zero
    menor = int(cand.sort_values(["cod6", "ano_epi"]).groupby("cod6").tail(CANAL_ANOS)["ano_epi"].min())
    fh = replace(f, ano_ini=menor, ano_fim=ano, contagem="provaveis")
    semanas = (52, 53) if sem == 53 else (sem,)
    hist = cq.semana_por_municipio(fh, semanas)
    anos = anos_do_canal(cq.totais_por_municipio(fh), ano, cobertos)
    faixa = faixa_esperada(hist, anos, semanas=(sem,))
    if faixa.empty:
        return vazio
    atual = cq.semana_por_municipio(replace(f, ano_ini=s["inicio"].year, ano_fim=ano + 1, contagem="provaveis"), (sem,))
    atual = atual[(atual["ano_epi"] == ano) & (atual["sem_epi"] == sem)][["cod6", "casos"]]
    r = base[["cod6", "uf"]].merge(faixa[["cod6", "q1", "q3"]], on="cod6", how="left").merge(atual, on="cod6", how="left")
    semana_ok = r["uf"].map({uf: semana_coberta(s, data, b) for uf, b in baixados.items()}).astype(bool)
    # 0 só vale com a semana baixada; sem o arquivo, falta de dado não pode virar zero
    r["casos"] = r["casos"].fillna(0).astype(int).astype(object).where(semana_ok, None)
    ok = r["q3"].notna() & semana_ok
    r["alerta_motivo"] = pd.Series(np.select([r["q3"].isna(), ~semana_ok], ["sem_historico", "semana_nao_baixada"], ""),
                                   index=r.index).astype(object).where(lambda m: m != "", None)
    r["alerta"] = pd.Series(np.where(ok, nivel_alerta(r["casos"].fillna(0), r["q1"], r["q3"]), None), index=r.index, dtype=object)
    r["faixa_zero"] = ok & (r["q3"] == 0)
    r = r.rename(columns={"casos": "casos_semana", "q3": "esperado_ate"})
    return s, r[colunas].sort_values("cod6").reset_index(drop=True)


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
