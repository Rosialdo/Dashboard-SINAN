"""Dashboard SINAN — abra com ABRIR_DASHBOARD.bat (ou: python iniciar.py)."""

from __future__ import annotations

import io
import json
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from sinan import agravos as cat
from sinan import consultas as cq
from sinan.config import (AMAZONIA_LEGAL, ARQ_INVENTARIO, ARQ_MAPA, UFS, carregar_config,
                          salvar_config)
from sinan.download import listagem_salva, listar_ftp
from sinan.pipeline import atualizar
from sinan.processar import FAIXAS, ler_inventario, remover
from sinan.tabnet import ler_cnv, ler_def

st.set_page_config(page_title="Dashboard SINAN", page_icon="📊", layout="wide")

# ----------------------------------------------------------- cores e formatos
AZUL, LARANJA, CINZA = "#2a78d6", "#eb6834", "#898781"
SEQUENCIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
ARBOVIROSES = {"DENG", "CHIK", "ZIKA"}
CONFIG_GRAFICO = {"displaylogo": False, "locale": "pt-BR",
                  "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"]}


def fmt(n, casas: int = 0) -> str:
    if n is None or pd.isna(n):
        return "–"
    return f"{n:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def layout(fig: go.Figure, altura: int = 360, **kw) -> go.Figure:
    opcoes = dict(height=altura, margin=dict(l=8, r=8, t=36, b=8), hovermode="closest",
                  legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None),
                  separators=",.")
    fig.update_layout(**{**opcoes, **kw})
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(rangemode="tozero")
    return fig


def mostrar(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch", config=CONFIG_GRAFICO, theme="streamlit")


def barras_h(df: pd.DataFrame, col_rotulo: str, col_valor: str = "casos", altura: int | None = None,
             titulo: str = "") -> go.Figure:
    df = df.sort_values(col_valor)
    total = df[col_valor].sum() or 1
    texto = [f"{fmt(v)} ({fmt(100 * v / total, 1)}%)" for v in df[col_valor]]
    fig = go.Figure(go.Bar(
        x=df[col_valor], y=df[col_rotulo], orientation="h", marker_color=AZUL,
        marker_line_width=0, text=texto, textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x:,.0f}<extra></extra>"))
    layout(fig, altura or max(220, 34 * len(df) + 60), title=titulo, bargap=0.3)
    fig.update_xaxes(showticklabels=False, range=[0, df[col_valor].max() * 1.35 if len(df) else 1])
    return fig


def versao_dados() -> float:
    try:
        return ARQ_INVENTARIO.stat().st_mtime
    except OSError:
        return 0.0


@st.cache_data(show_spinner=False)
def consulta(nome: str, filtro: cq.Filtro, versao: float, *args):
    return getattr(cq, nome)(filtro, *args)


@st.cache_data(show_spinner=False)
def geojson_ufs(ufs: tuple[str, ...]) -> dict:
    geo = json.loads(ARQ_MAPA.read_text(encoding="utf-8"))
    codigos = {cod for cod, sigla in UFS.items() if sigla in ufs}
    geo["features"] = [f for f in geo["features"] if f["properties"]["cod6"][:2] in codigos]
    return geo


# ================================================================== PAINEL
def pagina_painel() -> None:
    disponiveis = cq.agravos_disponiveis()
    if not disponiveis:
        st.title("Dashboard SINAN")
        st.info("Ainda não há dados no computador. Vá em **⬇️ Baixar dados** no menu ao lado "
                "(só essa etapa precisa de internet).")
        return

    versao = versao_dados()
    cfg = carregar_config()
    sb = st.sidebar
    sb.header("Filtros")
    agravo_cod = sb.selectbox("Doença / agravo", disponiveis, format_func=cat.nome,
                              index=disponiveis.index("DENG") if "DENG" in disponiveis else 0)
    agravo = cat.obter(agravo_cod)
    anos = cq.anos(agravo_cod)
    if len(anos) > 1:
        ano_ini, ano_fim = sb.select_slider("Anos (de notificação)", options=anos, value=(anos[0], anos[-1]))
    else:
        ano_ini = ano_fim = anos[0]
        sb.caption(f"Ano disponível: {anos[0]}")

    local = sb.radio("Contar casos pelo município de", ["Residência", "Notificação"], horizontal=True,
                     help="Residência: onde o paciente mora (padrão dos boletins). "
                          "Notificação: onde o caso foi registrado.")
    por_res = local == "Residência"

    ufs_cfg = [u for u in cfg["ufs"] if u in UFS.values()]
    ufs_dados = cq.ufs_presentes(agravo_cod)
    if "BR" in cfg["ufs"]:
        opcoes_uf = sorted(ufs_dados)
        ufs = tuple(sb.multiselect("UF", opcoes_uf, placeholder="Todas"))
    else:
        opcoes_uf = ufs_cfg or ufs_dados[:1]
        ufs = tuple(sb.multiselect("UF", opcoes_uf, default=opcoes_uf)) if len(opcoes_uf) > 1 else tuple(opcoes_uf)
    ufs_area = list(ufs) or opcoes_uf

    mun_df = cq.municipios_da_uf(ufs_area)
    nomes_mun = dict(zip(mun_df["cod6"], mun_df["municipio"] + " (" + mun_df["uf"] + ")"))
    municipios = tuple(sb.multiselect("Municípios", list(nomes_mun), format_func=nomes_mun.get,
                                      placeholder="Todos"))

    if agravo.todos_casos:
        contagem = "todas"
        sb.caption("Para este agravo toda notificação já é um caso.")
    else:
        opcoes = {"Casos confirmados": "confirmados"}
        if agravo.codigo in ARBOVIROSES:
            opcoes["Casos prováveis"] = "provaveis"
        opcoes["Todas as notificações"] = "todas"
        contagem = opcoes[sb.radio(
            "Contar", list(opcoes),
            help="Confirmados: classificação final confirmada. Prováveis: todas as notificações exceto "
                 "as descartadas (medida usada nos boletins de arboviroses do Ministério da Saúde).")]

    with sb.expander("Mais filtros"):
        sexo = tuple(st.multiselect("Sexo", ["Feminino", "Masculino", "Ignorado"], placeholder="Todos"))
        faixas = tuple(st.multiselect("Faixa etária (anos)", FAIXAS, placeholder="Todas"))

    f = cq.Filtro(agravo_cod, ano_ini, ano_fim, por_res, ufs, municipios, contagem, sexo, faixas)
    termo = {"confirmados": "casos confirmados", "provaveis": "casos prováveis"}.get(
        contagem, "casos" if agravo.todos_casos else "notificações")

    # ------------------------------------------------------------ cabeçalho
    if municipios:
        area = ", ".join(nomes_mun[m].rsplit(" (", 1)[0] for m in municipios[:3]) + ("…" if len(municipios) > 3 else "")
    elif "BR" in cfg["ufs"] and not ufs:
        area = "Brasil"
    else:
        area = ", ".join(ufs_area)
    periodo = f"{ano_ini}" if ano_ini == ano_fim else f"{ano_ini} a {ano_fim}"
    st.title(f"{agravo.nome} · {area} · {periodo}")

    inv = ler_inventario()
    prelim = sorted(int(v["ano"]) for v in inv.values()
                    if v["agravo"] == agravo_cod and v.get("situacao") == "preliminar" and ano_ini <= int(v["ano"]) <= ano_fim)
    if prelim:
        st.caption(f"⚠️ Dados preliminares em {', '.join(map(str, prelim))}: os números ainda mudam "
                   "conforme os casos são investigados e encerrados.")
    if agravo.aviso and (agravo.codigo != "MALA" or set(ufs_area) & AMAZONIA_LEGAL):
        st.caption(f"ℹ️ {agravo.aviso}")

    # ----------------------------------------------------------- indicadores
    ind = consulta("indicadores", f, versao)
    pop = cq.populacao(f, ufs_area) if not (sexo or faixas) else 0
    casos = ind["notificacoes"] if contagem == "todas" else ind[contagem]
    c = st.columns(6)
    c[0].metric("Notificações", fmt(ind["notificacoes"]))
    if agravo.todos_casos:
        c[1].metric("Casos", fmt(ind["confirmados"]))
    else:
        pct = 100 * ind["confirmados"] / ind["notificacoes"] if ind["notificacoes"] else None
        c[1].metric("Confirmados", fmt(ind["confirmados"]),
                    help="Classificação final = confirmado.", delta=f"{fmt(pct, 1)}% das notificações" if pct is not None else None,
                    delta_color="off")
    n_anos = ano_fim - ano_ini + 1
    if pop:
        c[2].metric("Incidência", fmt(casos * 1e5 / pop, 1),
                    help=f"{termo.capitalize()} por 100 mil habitantes por ano "
                         f"(média do período; população IBGE).",
                    delta="por 100 mil hab./ano" if n_anos > 1 else "por 100 mil hab.", delta_color="off")
    else:
        c[2].metric("Incidência", "–", help="Não calculada com filtro de sexo/faixa etária.")
    c[3].metric("Óbitos pelo agravo", fmt(ind["obitos"]))
    letal = 100 * ind["obitos"] / ind["confirmados"] if ind["confirmados"] else None
    c[4].metric("Letalidade", f"{fmt(letal, 2)}%" if letal is not None else "–",
                help="Óbitos pelo agravo ÷ casos confirmados.")
    if ind["hosp_informado"]:
        c[5].metric("Hospitalizados", fmt(ind["hospitalizados"]),
                    delta=f"{fmt(100 * ind['hospitalizados'] / ind['hosp_informado'], 1)}% dos informados",
                    delta_color="off")
    else:
        ult = pd.to_datetime(ind["ultima_notificacao"], errors="coerce")
        c[5].metric("Última notificação", ult.strftime("%d/%m/%Y") if pd.notna(ult) else "–")

    if casos == 0:
        st.warning("Nenhum registro com esses filtros.")
        return

    abas = st.tabs(["📈 Evolução no tempo", "🗺️ Mapa e municípios", "👥 Perfil dos casos",
                    "🔎 Outras variáveis", "📄 Dados e download"])
    with abas[0]:
        aba_tempo(f, versao, termo)
    with abas[1]:
        aba_mapa(f, versao, termo, ufs_area)
    with abas[2]:
        aba_perfil(f, versao, termo, agravo)
    with abas[3]:
        aba_variaveis(f, versao, agravo)
    with abas[4]:
        aba_dados(f, versao, nomes_mun)


def aba_tempo(f: cq.Filtro, versao: float, termo: str) -> None:
    sem = consulta("por_semana", f, versao)
    st.subheader(f"Curva epidêmica: {termo} por semana epidemiológica")
    st.caption("Semana do início dos sintomas (ou do diagnóstico/notificação quando não informado). "
               "As últimas semanas costumam estar incompletas por atraso de notificação.")
    fig = go.Figure()
    anos_presentes = sorted(sem["ano_epi"].dropna().unique())
    for ano in anos_presentes:
        d = sem[sem["ano_epi"] == ano]
        if ano == anos_presentes[-1]:
            cor, larg = AZUL, 2.5
        elif len(anos_presentes) > 1 and ano == anos_presentes[-2]:
            cor, larg = LARANJA, 2
        else:
            cor, larg = CINZA, 1.2
        fig.add_trace(go.Scatter(x=d["sem_epi"], y=d["casos"], name=str(int(ano)), mode="lines",
                                 line=dict(color=cor, width=larg),
                                 hovertemplate=f"{int(ano)} · semana %{{x}}: %{{y:,.0f}}<extra></extra>"))
    layout(fig, 380, hovermode="x unified")
    fig.update_xaxes(title="Semana epidemiológica", range=[1, 53], dtick=4)
    fig.update_yaxes(title=termo.capitalize())
    mostrar(fig)

    col1, col2 = st.columns(2)
    with col1:
        anual = consulta("por_ano", f, versao)
        fig = go.Figure(go.Bar(x=anual["ano"].astype(str), y=anual["casos"], marker_color=AZUL,
                               text=[fmt(v) for v in anual["casos"]], textposition="outside",
                               cliponaxis=False, hovertemplate="%{x}: %{y:,.0f}<extra></extra>"))
        layout(fig, 320, title=f"{termo.capitalize()} por ano de notificação", bargap=0.35)
        fig.update_xaxes(type="category")
        mostrar(fig)
    with col2:
        mes = consulta("por_mes", f, versao)
        fig = go.Figure(go.Bar(x=mes["mes"], y=mes["casos"], marker_color=AZUL,
                               hovertemplate="%{x|%m/%Y}: %{y:,.0f}<extra></extra>"))
        layout(fig, 320, title=f"{termo.capitalize()} por mês (início dos sintomas)", bargap=0.15)
        fig.update_xaxes(tickformat="%m/%Y")
        mostrar(fig)


def aba_mapa(f: cq.Filtro, versao: float, termo: str, ufs_area: list[str]) -> None:
    dados = consulta("por_municipio", f, versao)
    base = cq.municipios_da_uf(ufs_area)
    if f.municipios:
        base = base[base["cod6"].isin(f.municipios)]
    tabela = base.merge(dados.drop(columns=["municipio", "uf"]), on="cod6", how="left")
    tabela[["casos", "obitos"]] = tabela[["casos", "obitos"]].fillna(0).astype(int)
    tabela = tabela.drop(columns=["populacao", "incidencia"], errors="ignore")
    popmap = cq._q("SELECT cod6, avg(populacao) populacao, sum(populacao) pa FROM pop "
                   "WHERE ano BETWEEN ? AND ? GROUP BY 1", [f.ano_ini, f.ano_fim])
    tabela = tabela.merge(popmap, on="cod6", how="left")
    tabela["incidencia"] = tabela["casos"] * 1e5 / tabela["pa"]

    tem_filtro_pessoa = bool(f.sexo or f.faixas)
    medida = "casos" if tem_filtro_pessoa else st.radio(
        "Colorir o mapa por", ["Incidência (por 100 mil hab./ano)", "Número de casos"],
        horizontal=True, label_visibility="collapsed")
    col_cor = "casos" if medida != "Incidência (por 100 mil hab./ano)" else "incidencia"

    if len(ufs_area) <= 6 or f.municipios:
        geo = geojson_ufs(tuple(ufs_area))
        fig = go.Figure(go.Choropleth(
            geojson=geo, featureidkey="properties.cod6", locations=tabela["cod6"], z=tabela[col_cor].fillna(0),
            colorscale=[[i / (len(SEQUENCIAL) - 1), c] for i, c in enumerate(SEQUENCIAL)],
            marker_line_color="rgba(255,255,255,0.8)", marker_line_width=0.6,
            customdata=tabela[["municipio", "casos", "incidencia"]].fillna(0).values,
            hovertemplate="<b>%{customdata[0]}</b><br>" + termo.capitalize() +
                          ": %{customdata[1]:,.0f}<br>Incidência: %{customdata[2]:,.1f}<extra></extra>",
            colorbar=dict(title=None, thickness=12, len=0.7)))
        fig.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
        layout(fig, 520, geo=dict(projection_type="mercator"))
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
        mostrar(fig)
    else:
        st.info("O mapa aparece quando até 6 UFs estão selecionadas.")

    st.subheader("Ranking de municípios")
    mostrar_tab = tabela.sort_values(["casos", "incidencia"], ascending=False)[
        ["municipio", "uf", "casos", "incidencia", "obitos", "populacao"]]
    st.dataframe(
        mostrar_tab, hide_index=True, width="stretch",
        column_config={
            "municipio": "Município", "uf": "UF",
            "casos": st.column_config.ProgressColumn(termo.capitalize(), format="%d",
                                                     max_value=int(mostrar_tab["casos"].max() or 1)),
            "incidencia": st.column_config.NumberColumn("Incidência /100 mil/ano", format="%.1f"),
            "obitos": st.column_config.NumberColumn("Óbitos", format="%d"),
            "populacao": st.column_config.NumberColumn("População (média)", format="%d"),
        })
    st.caption("Incidência = casos ÷ soma da população dos anos selecionados × 100 mil "
               "(população estimada pelo IBGE; anos sem estimativa são interpolados).")


def aba_perfil(f: cq.Filtro, versao: float, termo: str, agravo: cat.Agravo) -> None:
    col1, col2 = st.columns(2)
    with col1:
        pir = consulta("piramide", f, versao)
        fig = go.Figure()
        for sexo, cor, sinal in [("Masculino", AZUL, -1), ("Feminino", LARANJA, 1)]:
            d = pir[pir["sexo"] == sexo].set_index("faixa_etaria")[["casos"]].reindex(FAIXAS).fillna(0)
            fig.add_trace(go.Bar(y=FAIXAS, x=sinal * d["casos"], name=sexo, orientation="h",
                                 marker_color=cor, customdata=d["casos"],
                                 hovertemplate=f"{sexo}, %{{y}} anos: %{{customdata:,.0f}}<extra></extra>"))
        maximo = pir["casos"].max() if len(pir) else 1
        layout(fig, 420, title="Pirâmide etária (anos)", barmode="relative", bargap=0.15)
        fig.update_xaxes(tickvals=[-maximo, -maximo / 2, 0, maximo / 2, maximo],
                         ticktext=[fmt(maximo), fmt(maximo / 2), "0", fmt(maximo / 2), fmt(maximo)])
        mostrar(fig)
    with col2:
        raca = consulta("contagem", f, versao, "raca")
        mostrar(barras_h(raca, "valor", titulo="Raça/cor", altura=420))

    col1, col2 = st.columns(2)
    with col1:
        if agravo.todos_casos:
            d = consulta("contagem", f, versao, "classificacao")
            if d["valor"].nunique() > 1:
                mostrar(barras_h(d, "valor", titulo="Classificação"))
        else:
            d = consulta("contagem", f, versao, "situacao", True)
            mostrar(barras_h(d, "valor", titulo="Situação das notificações (todas)"))
            d = consulta("contagem", f, versao, "classificacao", True)
            mostrar(barras_h(d, "valor", titulo="Classificação final (todas as notificações)"))
    with col2:
        d = consulta("contagem", f, versao, "evolucao")
        mostrar(barras_h(d, "valor", titulo=f"Evolução ({termo})"))
        d = consulta("contagem", f, versao, "criterio")
        if d["valor"].nunique() > 1:
            mostrar(barras_h(d, "valor", titulo=f"Critério de confirmação ({termo})"))


def aba_variaveis(f: cq.Filtro, versao: float, agravo: cat.Agravo) -> None:
    st.caption("Qualquer variável da ficha de notificação, com os rótulos oficiais do TabNet/DATASUS.")
    existentes = set(cq.colunas(f.agravo))
    variaveis = [v for v in ler_def(agravo.arquivo_def or "") if v.campo in existentes
                 and not v.cnv.lower().startswith(("munic", "uf", "regiao", "rmetri", "nhe", "anos", "meses"))]
    if not variaveis:
        st.info("Não há tabela de rótulos para este agravo.")
        return
    nomes = {i: f"{v.rotulo}  ·  {v.campo}" for i, v in enumerate(variaveis)}
    escolha = st.selectbox("Variável", list(nomes), format_func=nomes.get)
    v = variaveis[escolha]
    conv = ler_cnv(v.cnv)
    d = consulta("contagem", f, versao, v.campo)
    d["valor"] = conv.mapear(d["valor"].replace("", None), v.inicio)
    d = d.groupby("valor", as_index=False)["casos"].sum()
    ordem = {r: i for i, r in enumerate(conv.rotulos)}
    d = d.sort_values("casos", ascending=False).head(30)
    mostrar(barras_h(d, "valor", titulo=v.rotulo))
    d["%"] = 100 * d["casos"] / d["casos"].sum()
    st.dataframe(d.assign(o=d["valor"].map(ordem)).sort_values("o").drop(columns="o"),
                 hide_index=True, width="stretch",
                 column_config={"valor": v.rotulo, "casos": "Registros",
                                "%": st.column_config.NumberColumn(format="%.1f%%")})


def aba_dados(f: cq.Filtro, versao: float, nomes_mun: dict) -> None:
    amostra = consulta("registros", f, versao, 1000)
    todos_mun = dict(zip(*cq._q("SELECT cod6, municipio || ' (' || uf || ')' n FROM mun").T.values))
    for col in ("mun_not", "mun_res"):
        amostra[col] = amostra[col].map(lambda c: todos_mun.get(c, c))
    st.caption(f"Mostrando até 1.000 registros mais recentes. Os botões baixam todos os registros filtrados.")
    st.dataframe(amostra, hide_index=True, width="stretch", height=420)

    c1, c2, c3 = st.columns(3)
    nome = f"sinan_{f.agravo}_{f.ano_ini}-{f.ano_fim}"
    if c1.button("Preparar planilha Excel"):
        tudo = cq.registros(f, limite=1_000_000)
        for col in ("mun_not", "mun_res"):
            tudo[col] = tudo[col].map(lambda c: todos_mun.get(c, c))
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            tudo.to_excel(w, index=False, sheet_name="dados")
            consulta("por_municipio", f, versao).to_excel(w, index=False, sheet_name="por_municipio")
            consulta("por_semana", f, versao).to_excel(w, index=False, sheet_name="por_semana")
        c1.download_button("⬇️ Baixar Excel", buf.getvalue(), f"{nome}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    if c2.button("Preparar CSV (colunas principais)"):
        csv = cq.registros(f, limite=None).to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
        c2.download_button("⬇️ Baixar CSV", csv, f"{nome}.csv", "text/csv")
    if c3.button("Preparar CSV (todas as colunas originais)"):
        csv = cq.registros(f, limite=None, todas_colunas=True).to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
        c3.download_button("⬇️ Baixar CSV completo", csv, f"{nome}_completo.csv", "text/csv")


# ============================================================ BAIXAR DADOS
def pagina_baixar() -> None:
    st.title("Baixar e atualizar dados")
    st.write("Esta é a **única parte que precisa de internet**. Os arquivos vêm do FTP público do "
             "DATASUS, são filtrados para as UFs escolhidas e ficam salvos na pasta `dados/`. "
             "Depois disso o painel funciona offline.")
    cfg = carregar_config()
    listagem = listagem_salva()

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Consultar o que existe no DATASUS", width="stretch"):
            with st.spinner("Consultando FTP do DATASUS..."):
                try:
                    listagem = listar_ftp()
                    st.success("Lista atualizada.")
                except Exception as e:
                    st.error(f"Sem conexão com o DATASUS: {e}")
        if listagem:
            st.caption(f"Lista consultada em {listagem['atualizado_em'].replace('T', ' ')}")

    arquivos = (listagem or {}).get("arquivos", {})
    codigos = sorted(set(cat.AGRAVOS) | set(arquivos), key=cat.nome)
    with col1:
        opcoes_uf = ["BR"] + sorted(UFS.values())
        ufs = st.multiselect("UFs", opcoes_uf, default=[u for u in cfg["ufs"] if u in opcoes_uf],
                             format_func=lambda u: "BR – Brasil inteiro (muito pesado)" if u == "BR" else u)
        agravos_sel = st.multiselect("Doenças / agravos", codigos, default=[a for a in cfg["agravos"] if a in codigos],
                                     format_func=lambda c: f"{cat.nome(c)} ({c})")
        anos_lista = sorted({int(a) for c in (agravos_sel or codigos) for a in arquivos.get(c, {})}, reverse=True) \
            or list(range(date.today().year, 1999, -1))
        anos_sel = st.multiselect("Anos", anos_lista, default=[a for a in cfg["anos"] if a in anos_lista])

    if agravos_sel and anos_sel and arquivos:
        tamanho = sum(arquivos.get(a, {}).get(str(y), {}).get("tamanho", 0) for a in agravos_sel for y in anos_sel)
        st.caption(f"Download estimado: **{fmt(tamanho / 1e6)} MB** (arquivos nacionais; depois de filtrados "
                   "ficam bem menores e os originais são apagados).")
    if "BR" in ufs:
        st.warning("Brasil inteiro gera arquivos grandes (dengue de um único ano passa de 6 milhões de linhas). "
                   "Prefira escolher UFs.")

    forcar = st.checkbox("Baixar de novo mesmo o que já está atualizado")
    if st.button("⬇️ Baixar e processar", type="primary", disabled=not (ufs and agravos_sel and anos_sel)):
        salvar_config({**cfg, "ufs": ufs, "agravos": agravos_sel, "anos": sorted(anos_sel)})
        barra = st.progress(0.0)
        texto = st.empty()

        def aviso(tarefa: str, frac: float, msg: str) -> None:
            barra.progress(min(max(frac, 0.0), 1.0))
            texto.markdown(f"**{tarefa}** — {msg}")

        try:
            res = atualizar(agravos_sel, anos_sel, ufs, cfg.get("manter_brutos", False), forcar, aviso)
        except ConnectionError as e:
            st.error(str(e))
            return
        st.cache_data.clear()
        if res.sucesso:
            st.success("Concluído:\n\n" + "\n".join(f"- {s}" for s in res.sucesso))
        if res.pulados:
            st.info("Já estavam atualizados: " + ", ".join(res.pulados))
        if res.indisponiveis:
            st.warning("Não existem no DATASUS: " + ", ".join(res.indisponiveis))
        if res.erros:
            st.error("Erros:\n\n" + "\n".join(f"- {s}" for s in res.erros))

    st.divider()
    st.subheader("Dados no computador")
    inv = ler_inventario()
    if not inv:
        st.caption("Nenhum dado baixado ainda.")
        return
    tab = pd.DataFrame(inv.values())
    tab["agravo_nome"] = tab["agravo"].map(cat.nome)
    tab["ufs"] = tab["ufs"].map(", ".join)

    def desatualizado(r) -> str:
        info = arquivos.get(r["agravo"], {}).get(str(r["ano"]))
        if not info:
            return "?"
        if info.get("data_ftp") != r.get("data_ftp") or info.get("situacao") != r.get("situacao"):
            return "Há versão nova"
        return "Em dia"
    tab["status"] = tab.apply(desatualizado, axis=1)
    tab = tab.sort_values(["agravo_nome", "ano"])
    st.dataframe(tab[["agravo_nome", "ano", "situacao", "registros", "ufs", "status", "processado_em"]],
                 hide_index=True, width="stretch",
                 column_config={"agravo_nome": "Agravo", "ano": st.column_config.NumberColumn("Ano", format="%d"),
                                "situacao": "Dado", "registros": "Registros", "ufs": "UFs",
                                "status": "No DATASUS", "processado_em": "Baixado em"})
    with st.expander("Remover dados"):
        chaves = st.multiselect("Escolha o que remover", list(inv),
                                format_func=lambda k: f"{cat.nome(inv[k]['agravo'])} {inv[k]['ano']}")
        if st.button("Remover selecionados", disabled=not chaves):
            for k in chaves:
                remover(inv[k]["agravo"], int(inv[k]["ano"]))
            st.cache_data.clear()
            st.rerun()


# ==================================================================== SOBRE
def pagina_sobre() -> None:
    st.title("Sobre os dados")
    st.markdown("""
**Fonte:** Sistema de Informação de Agravos de Notificação (SINAN), microdados públicos e anonimizados
do DATASUS/Ministério da Saúde (`ftp.datasus.gov.br/dissemin/publicos/SINAN`). População: IBGE
(estimativas anuais e Censo 2022). Rótulos das variáveis: arquivos oficiais do tabulador TabNet.

**Como os números são calculados**

- **Ano:** ano da notificação (igual ao arquivo do DATASUS e ao padrão do TabNet).
- **Semana epidemiológica:** semana (domingo a sábado) do início dos sintomas; quando não há essa data,
  usa a data de diagnóstico ou de notificação. A semana 1 é a primeira com ao menos 4 dias no ano.
- **Confirmado:** classificação final do caso. Para dengue: dengue, dengue com sinais de alarme e dengue
  grave (e as classificações antigas antes de 2014). Para chikungunya: código 13. Para os demais, o
  rótulo "confirmado" da ficha. Em agravos como tuberculose, hanseníase, violência e acidentes de
  trabalho, toda notificação já é um caso.
- **Óbito:** evolução "óbito pelo agravo" (não conta óbito por outras causas nem em investigação).
- **Letalidade:** óbitos pelo agravo ÷ casos confirmados × 100.
- **Incidência:** casos ÷ população × 100 mil. Com vários anos, é a média anual (casos ÷ soma da
  população de cada ano).
- **Residência x notificação:** por padrão os casos são contados no município onde a pessoa mora.

**Cuidados na interpretação**

- Dados dos anos mais recentes são **preliminares** e mudam a cada atualização do DATASUS.
- As últimas semanas sempre parecem menores por causa do atraso entre o início dos sintomas e o registro.
- Pequenos municípios têm incidências muito instáveis: poucos casos já mudam muito a taxa.
- Para conferir números, compare com o TabNet: <http://tabnet.datasus.gov.br>.
""")


paginas = {"📊 Painel": pagina_painel, "⬇️ Baixar dados": pagina_baixar, "ℹ️ Sobre os dados": pagina_sobre}
escolha = st.sidebar.radio("Menu", list(paginas), label_visibility="collapsed")
st.sidebar.divider()
paginas[escolha]()
