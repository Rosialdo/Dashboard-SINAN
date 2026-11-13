/* Blocos visuais simples: carregando, erro e tela vazia. */

import { ico } from "../nucleo/icones.js";
import { esc } from "../nucleo/util.js";

/** Retângulo cinza animado enquanto os dados chegam. */
export const esqueleto = (altura) => `<div class="esqueleto" style="height:${altura}px"></div>`;

/** Caixa vermelha com a mensagem de erro. */
export const erroHtml = (e) => `<div class="alerta erro">${ico("alerta")}<span>${esc(e?.message || e)}</span></div>`;

/** Texto cinza para listas vazias. */
export const vazioHtml = (texto) => `<p class="card-sub" style="padding:12px">${esc(texto)}</p>`;
