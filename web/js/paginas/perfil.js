/* Tela "Perfil dos casos": pirâmide etária e distribuições (raça/cor, evolução...). */

import { barrasHtml } from "../componentes/barras.js";
import { erroHtml, esqueleto } from "../componentes/blocos.js";
import { definirRedesenho, layoutBase, plot } from "../componentes/graficos.js";
import { mostrarKpis } from "../componentes/kpis.js";
import { api } from "../nucleo/api.js";
import { estado } from "../nucleo/estado.js";
import { agravoAtual, query, termo } from "../nucleo/filtros.js";
import { $, cap, css, fmt } from "../nucleo/util.js";

const QUADROS = ["raca", "situacao", "classificacao", "evolucao", "criterio", "hospitalizado"];

export async function montar(raiz, pedido) {
  const ag = agravoAtual();
  const t = cap(termo());
  const quadro = (id, titulo, sub, alt = 200) =>
    `<section class="card card-corpo"><h2>${titulo}</h2><p class="card-sub">${sub}</p><div id="b-${id}">${esqueleto(alt)}</div></section>`;
  raiz.insertAdjacentHTML("beforeend", `
    <div id="kpis">${esqueleto(120)}</div>
    <div class="grade g2">
      <section class="card card-corpo"><div class="card-titulo"><h2>Pirâmide etária</h2>
        <div class="legenda"><span><span class="q" style="background:var(--serie-1)"></span>Masculino</span><span><span class="q" style="background:var(--serie-2)"></span>Feminino</span></div></div>
        <p class="card-sub">${t} por faixa etária (anos) e sexo</p><div id="g-pir" style="height:380px"></div></section>
      ${quadro("raca", "Raça/cor", t, 300)}
    </div>
    <div class="grade g2">
      ${ag.todos_casos ? "" : quadro("situacao", "Situação das notificações", "Todas as notificações, pela classificação final")}
      ${quadro("classificacao", "Classificação final", ag.todos_casos ? "Casos" : "Todas as notificações")}
      ${quadro("evolucao", "Evolução", t)}
      ${quadro("criterio", "Critério de confirmação", t)}
      ${quadro("hospitalizado", "Hospitalização", t, 160)}
    </div>`);
  let d;
  try { d = await api(`/api/perfil?${query()}`); } catch (e) { $("#kpis").innerHTML = erroHtml(e); return; }
  if (pedido !== estado.pedido) return;
  mostrarKpis(d.indicadores);
  for (const k of QUADROS) {
    const el = $(`#b-${k}`);
    if (el) el.innerHTML = d[k].length ? barrasHtml(d[k]) : `<p class="card-sub">Sem informação.</p>`;
  }
  const desenhar = () => piramide(d.piramide);
  desenhar();
  definirRedesenho(desenhar);
}

function piramide(linhas) {
  const faixas = estado.meta.faixas;
  const val = (sexo) => faixas.map((fx) => (linhas.find((r) => r.sexo === sexo && r.faixa_etaria === fx) || {}).casos || 0);
  const mas = val("Masculino"), fem = val("Feminino");
  const max = Math.max(1, ...mas, ...fem);
  const passo = Math.pow(10, Math.floor(Math.log10(max)));
  const lim = Math.ceil(max / passo) * passo;
  const ticks = [-lim, -lim / 2, 0, lim / 2, lim];
  plot($("#g-pir"), [
    { y: faixas, x: mas.map((v) => -v), customdata: mas, name: "Masculino", type: "bar", orientation: "h",
      marker: { color: css("--serie-1"), cornerradius: 3 }, hovertemplate: "Masculino, %{y}: %{customdata:,.0f}<extra></extra>" },
    { y: faixas, x: fem, customdata: fem, name: "Feminino", type: "bar", orientation: "h",
      marker: { color: css("--serie-2"), cornerradius: 3 }, hovertemplate: "Feminino, %{y}: %{customdata:,.0f}<extra></extra>" },
  ], layoutBase({ barmode: "relative", bargap: 0.14, margin: { l: 56, r: 12, t: 6, b: 30 },
    xaxis: { ...layoutBase().xaxis, tickvals: ticks, ticktext: ticks.map((v) => fmt(Math.abs(v))), range: [-lim * 1.05, lim * 1.05] },
    yaxis: { ...layoutBase().yaxis, showgrid: false, rangemode: undefined } }));
}
