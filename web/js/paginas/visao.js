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
    if (d.contagens_ocultas) {
      $("#leg-semana").innerHTML = "";
      $("#g-semana").style.height = "auto";
      $("#g-semana").innerHTML = `<p class="card-sub">No site publicado, a curva por semana de um município não é mostrada, para proteger a privacidade. Veja a curva da UF ou use o painel instalado no computador.</p>`;
    } else curvaSemanal(d.semana, t, d.canal);
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
function curvaSemanal(semana, titulo, canal) {
  const anos = [...new Set(semana.map((r) => r.ano_epi))].sort();
  const ult = anos.at(-1), pen = anos.at(-2);
  const corDe = (a) => a === ult ? "--serie-1" : a === pen ? "--serie-2" : "--serie-ctx";
  const faixa = canal ? [
    { x: canal.semanas.map((r) => r.sem_epi), y: canal.semanas.map((r) => r.q1), type: "scatter", mode: "lines",
      line: { width: 0 }, hoverinfo: "skip", showlegend: false },
    { x: canal.semanas.map((r) => r.sem_epi), y: canal.semanas.map((r) => r.q3), type: "scatter", mode: "lines",
      line: { width: 0 }, fill: "tonexty", fillcolor: css("--faixa"), showlegend: false,
      customdata: canal.semanas.map((r) => `${fmt(r.q1, 1)} a ${fmt(r.q3, 1)}`), hovertemplate: "Faixa histórica: de %{customdata}<extra></extra>" },
    { x: canal.semanas.map((r) => r.sem_epi), y: canal.semanas.map((r) => r.mediana), type: "scatter", mode: "lines",
      line: { color: css("--faixa-linha"), width: 1.4, dash: "dash" }, hoverinfo: "skip", showlegend: false },
  ] : [];
  const traces = anos.map((a) => {
    const pts = semana.filter((r) => r.ano_epi === a);
    return { x: pts.map((r) => r.sem_epi), y: pts.map((r) => r.casos), name: String(a), type: "scatter", mode: "lines",
             line: { color: css(corDe(a)), width: a === ult ? 2.6 : a === pen ? 2 : 1.3 },
             hovertemplate: `${a}: %{y:,.0f}<extra></extra>` };
  });
  const fx = canal ? `<span><span class="q faixa"></span>Faixa histórica (anos usados: ${canal.anos.join(", ")}${canal.excluidos.length ? `; fora por terem muito mais casos: ${canal.excluidos.join(", ")}` : ""})</span><span><i style="border-color:var(--faixa-linha);border-top-style:dashed"></i>Mediana</span>` : "";
  $("#leg-semana").innerHTML = fx + anos.map((a) => `<span><i style="border-color:var(${corDe(a)})"></i>${a}</span>`).join("");
  const sub = $("#t-semana").parentElement.querySelector(".card-sub");
  sub.querySelector(".aviso-faixa")?.remove();
  if (!canal) sub.insertAdjacentHTML("beforeend", ` <span class="aviso-faixa">Faixa histórica indisponível: são precisos 5 anos anteriores completos baixados.</span>`);
  plot($("#g-semana"), [...faixa, ...traces], layoutBase({
    hovermode: "x unified",
    xaxis: { ...layoutBase().xaxis, title: { text: "Semana epidemiológica", font: { size: 13 } }, range: [0.5, 53.5], dtick: 4, tick0: 4, showgrid: false },
    yaxis: { ...layoutBase().yaxis, title: { text: titulo, font: { size: 13 } } },
    margin: { l: 58, r: 12, t: 10, b: 46 },
  }));
}
