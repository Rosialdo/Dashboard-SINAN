/* Funções pequenas usadas em todo lugar: seletores, formatação e escape de HTML. */

export const $ = (s, el = document) => el.querySelector(s);
export const $$ = (s, el = document) => [...el.querySelectorAll(s)];

/** Número no formato brasileiro; vazio vira "–". */
export const fmt = (v, casas = 0) => (v === null || v === undefined || Number.isNaN(v)) ? "–"
  : new Intl.NumberFormat("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas }).format(v);

/** Escapa texto antes de colocar em HTML (evita quebrar a página com < > & aspas). */
export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/** Valor de uma variável CSS do tema atual (ex.: css("--serie-1")). */
export const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

/** Primeira letra maiúscula. */
export const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

/** Texto sem acentos e em minúsculas, para buscas. */
export const norm = (s) => String(s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** Data "AAAA-MM-DD" no formato brasileiro. */
export const dataBR = (v) => new Date(v + "T12:00").toLocaleDateString("pt-BR");
