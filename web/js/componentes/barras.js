/* Lista de barras horizontais com número e porcentagem (raça/cor, evolução, variáveis...). */

import { esc, fmt } from "../nucleo/util.js";

/** ``lista``: [{valor, casos}]. ``total`` padrão: soma dos casos. */
export function barrasHtml(lista, total) {
  const max = Math.max(1, ...lista.map((d) => d.casos));
  total = total || lista.reduce((s, d) => s + d.casos, 0) || 1;
  return `<div class="barras">${lista.map((d) => `
    <div class="barra-linha"><span class="barra-rotulo" title="${esc(d.valor)}">${esc(d.valor || "Não informado")}</span>
      <div class="barra-trilho"><div class="barra-valor-barra" style="width:${100 * d.casos / max}%"></div></div>
      <span class="barra-num"><b>${fmt(d.casos)}</b> · ${fmt(100 * d.casos / total, 1)}%</span></div>`).join("")}</div>`;
}
