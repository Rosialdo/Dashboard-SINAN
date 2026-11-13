/* Gráficos com Plotly: estilo padrão, registro para limpar e redesenho ao trocar o tema. */

import { css } from "../nucleo/util.js";

const CFG = { displayModeBar: false, responsive: true, locale: "pt-BR" };
const graficos = [];
let _redesenhar = null;

/** Layout base (cores do tema, eixos, fonte). ``extra`` sobrescreve o que precisar. */
export function layoutBase(extra = {}) {
  const fonte = { family: getComputedStyle(document.body).fontFamily, size: 13, color: css("--text-2") };
  return Object.assign({
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", font: fonte,
    margin: { l: 48, r: 12, t: 10, b: 40 }, showlegend: false, separators: ",.",
    hoverlabel: { bgcolor: css("--text"), bordercolor: css("--text"), font: { color: css("--bg"), size: 13, family: fonte.family } },
    xaxis: { gridcolor: css("--grid"), linecolor: css("--eixo"), zeroline: false, tickfont: { color: css("--text-2") }, fixedrange: true },
    yaxis: { gridcolor: css("--grid"), linecolor: css("--eixo"), zeroline: false, rangemode: "tozero", tickfont: { color: css("--text-2") },
             fixedrange: true, separatethousands: true },
  }, extra);
}

/** Desenha (ou atualiza) um gráfico em ``el``. */
export function plot(el, traces, layout) {
  Plotly.react(el, traces, layout, CFG);
  if (!graficos.includes(el)) graficos.push(el);
}

/** Libera os gráficos da tela anterior. Chamado pelo roteador ao trocar de tela. */
export function limparGraficos() {
  _redesenhar = null;
  graficos.forEach((g) => { try { Plotly.purge(g); } catch (e) { /* já removido */ } });
  graficos.length = 0;
}

/** A tela registra como se redesenhar quando o tema (claro/escuro) muda. */
export function definirRedesenho(fn) { _redesenhar = fn; }
export function redesenhar() { if (_redesenhar) _redesenhar(); }
