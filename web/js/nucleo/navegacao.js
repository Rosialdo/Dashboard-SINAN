/* Endereço da tela atual (#/mapa, #/perfil...). */

import { estado, PAGINAS } from "./estado.js";

export function paginaAtual() {
  const h = location.hash.replace("#/", "").replace("#", "");
  return PAGINAS[h] && !oculta(h) ? h : "visao-geral";
}

/** Telas que o servidor mandou esconder (no site publicado: "dados" e "atualizar"). */
export function oculta(id) { return Boolean(estado.meta?.telas_ocultas?.includes(id)); }

export function irPara(id) { location.hash = `#/${id}`; }
