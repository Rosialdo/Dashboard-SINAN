/* Informações gerais vindas do servidor (/api/meta) e o nome do painel. */

import { api } from "./api.js";
import { estado } from "./estado.js";
import { normalizarFiltros } from "./filtros.js";
import { $ } from "./util.js";

/** "Vigilância RR" quando há uma UF só; "Vigilância SINAN" nos outros casos. */
export function nomeMarca() {
  const m = estado.meta;
  if (!m || m.brasil || m.ufs.length !== 1) return "Vigilância SINAN";
  return `Vigilância ${m.ufs[0]}`;
}

/** Busca de novo o que existe no computador (depois de baixar ou remover dados). */
export async function recarregarMeta() {
  estado.meta = await api("/api/meta");
  $("#brand-nome").textContent = nomeMarca();
  normalizarFiltros();
}
