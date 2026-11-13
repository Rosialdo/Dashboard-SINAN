/* Quadros de indicadores do topo (notificações, confirmados, incidência...). */

import { agravoAtual, termo } from "../nucleo/filtros.js";
import { ico } from "../nucleo/icones.js";
import { cap, dataBR, esc, fmt } from "../nucleo/util.js";

/** Um quadro. ``ajuda`` aparece no ícone "i". */
export function kpi(rotulo, valor, ajuda, sub = "", pilula = "") {
  return `<div class="card kpi"><div class="kpi-rotulo">${rotulo}
    <span class="info" data-tip="${esc(ajuda)}" tabindex="0" aria-label="${esc(ajuda)}">${ico("info")}</span></div>
    <div class="kpi-valor">${valor}</div>${sub ? `<div class="kpi-sub">${sub}</div>` : ""}${pilula ? `<span class="pilula">${pilula}</span>` : ""}</div>`;
}

/** Os seis quadros, a partir de ``indicadores`` da API. */
export function htmlKpis(ind) {
  const ag = agravoAtual();
  const t = termo();
  const pct = ind.notificacoes ? 100 * ind.confirmados / ind.notificacoes : null;
  const conf = ag.todos_casos
    ? kpi("Casos", fmt(ind.confirmados), "Para este agravo toda notificação é um caso.")
    : kpi("Confirmados", fmt(ind.confirmados), "Notificações com classificação final confirmada.", "",
          pct !== null ? `${fmt(pct, 1)}% das notificações` : "");
  const inc = ind.incidencia === null
    ? kpi("Incidência", "–", "Não é calculada quando há filtro de sexo ou faixa etária (não há população por esses grupos).")
    : kpi("Incidência", fmt(ind.incidencia, 1), `${cap(t)} por 100 mil habitantes${ind.n_anos > 1 ? " por ano (média do período)" : ""}. População: IBGE.`,
          ind.n_anos > 1 ? "por 100 mil hab./ano" : "por 100 mil hab.");
  const hosp = ind.hosp_informado
    ? kpi("Hospitalizados", fmt(ind.hospitalizados), "Casos confirmados com hospitalização registrada.", "",
          `${fmt(100 * ind.hospitalizados / ind.hosp_informado, 1)}% dos informados`)
    : kpi("Última notificação", ind.ultima_notificacao ? dataBR(ind.ultima_notificacao) : "–",
          "Data da notificação mais recente nos dados filtrados.");
  return `<section class="kpis" aria-label="Indicadores">
    ${kpi("Notificações", fmt(ind.notificacoes), "Total de fichas notificadas no período e área, qualquer que seja a classificação.")}
    ${conf}${inc}
    ${kpi("Óbitos", fmt(ind.obitos), "Óbitos pelo agravo notificado entre os casos confirmados (não inclui óbito por outras causas).")}
    ${kpi("Letalidade", ind.letalidade === null ? "–" : `${fmt(ind.letalidade, 2)}%`, "Óbitos pelo agravo ÷ casos confirmados × 100.")}
    ${hosp}
  </section>`;
}

/** Preenche o #kpis da tela com os indicadores. */
export function mostrarKpis(ind) {
  const el = document.querySelector("#kpis");
  if (el) el.innerHTML = htmlKpis(ind);
}
