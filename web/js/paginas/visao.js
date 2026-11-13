/* Tela "Visão geral": indicadores e curvas por semana epidemiológica, ano e mês. */

import { erroHtml, esqueleto } from "../componentes/blocos.js";
import { definirRedesenho, layoutBase, plot } from "../componentes/graficos.js";
import { mostrarKpis } from "../componentes/kpis.js";
import { api } from "../nucleo/api.js";
import { estado } from "../nucleo/estado.js";
import { query, termo } from "../nucleo/filtros.js";
import { $, cap, css, fmt } from "../nucleo/util.js";

export async function montar(raiz, pedido) {
  raiz.insertAdjacentHTML("beforeend", `
    <div id="kpis">${esqueleto(120)}</div>
    <section class="card card-corpo" style="margin-bottom:14px">
      <div class="card-titulo"><div><h2 id="t-semana">Casos por semana epidemiológica</h2>
        <p class="card-sub">Semana do início dos sintomas (ou do diagnóstico/notificação quando não informado). As últimas semanas costumam estar incompletas por atraso de notificação.</p></div>
        <div class="legenda" id="leg-semana"></div></div>
      <div id="g-semana" class="grafico" style="height:300px"></div>
    </section>
    <div class="grade g2">
      <section class="card card-corpo"><h2 id="t-ano">Casos por ano de notificação</h2><div id="g-ano" class="grafico" style="height:240px"></div></section>
      <section class="card card-corpo"><h2 id="t-mes">Casos por mês de início dos sintomas</h2><div id="g-mes" class="grafico" style="height:240px"></div></section>
    </div>`);
  let d;
  try { d = await api(`/api/visao?${query()}`); } catch (e) { $("#kpis").innerHTML = erroHtml(e); return; }
  if (pedido !== estado.pedido) return;
  mostrarKpis(d.indicadores);
  const t = cap(termo());
  $("#t-semana").textContent = `${t} por semana epidemiológica`;
  $("#t-ano").textContent = `${t} por ano de notificação`;
  $("#t-mes").textContent = `${t} por mês de início dos sintomas`;

  const desenhar = () => {
    curvaSemanal(d.semana, t);
    plot($("#g-ano"), [{
      x: d.ano.map((r) => String(r.ano)), y: d.ano.map((r) => r.casos), type: "bar",
      marker: { color: css("--serie-1"), cornerradius: 4 }, text: d.ano.map((r) => fmt(r.casos)), textposition: "outside",
      textfont: { color: css("--text") }, cliponaxis: false, hovertemplate: "%{x}: %{y:,.0f}<extra></extra>",
    }], layoutBase({ bargap: 0.28, xaxis: { ...layoutBase().xaxis, type: "category", showgrid: false }, margin: { l: 44, r: 8, t: 22, b: 30 } }));
    plot($("#g-mes"), [{
      x: d.mes.map((r) => r.mes), y: d.mes.map((r) => r.casos), type: "bar",
      marker: { color: css("--serie-1"), cornerradius: 2 }, hovertemplate: "%{x|%m/%Y}: %{y:,.0f}<extra></extra>",
    }], layoutBase({ bargap: 0.18, xaxis: { ...layoutBase().xaxis, tickformat: "%m/%Y", showgrid: false, dtick: "M12" }, margin: { l: 44, r: 8, t: 10, b: 30 } }));
  };
  desenhar();
  definirRedesenho(desenhar);
}

/** Uma linha por ano; o último e o penúltimo em destaque, os demais em cinza. */
function curvaSemanal(semana, titulo) {
  const anos = [...new Set(semana.map((r) => r.ano_epi))].sort();
  const ult = anos.at(-1), pen = anos.at(-2);
  const corDe = (a) => a === ult ? "--serie-1" : a === pen ? "--serie-2" : "--serie-ctx";
  const traces = anos.map((a) => {
    const pts = semana.filter((r) => r.ano_epi === a);
    return { x: pts.map((r) => r.sem_epi), y: pts.map((r) => r.casos), name: String(a), type: "scatter", mode: "lines",
             line: { color: css(corDe(a)), width: a === ult ? 2.6 : a === pen ? 2 : 1.3 },
             hovertemplate: `${a}: %{y:,.0f}<extra></extra>` };
  });
  $("#leg-semana").innerHTML = anos.map((a) => `<span><i style="border-color:var(${corDe(a)})"></i>${a}</span>`).join("");
  plot($("#g-semana"), traces, layoutBase({
    hovermode: "x unified",
    xaxis: { ...layoutBase().xaxis, title: { text: "Semana epidemiológica", font: { size: 13 } }, range: [0.5, 53.5], dtick: 4, tick0: 4, showgrid: false },
    yaxis: { ...layoutBase().yaxis, title: { text: titulo, font: { size: 13 } } },
    margin: { l: 58, r: 12, t: 10, b: 46 },
  }));
}
