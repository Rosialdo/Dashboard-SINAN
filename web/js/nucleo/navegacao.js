/* Endereço da tela atual (#/mapa, #/perfil...). */

import { PAGINAS } from "./estado.js";

export function paginaAtual() {
  const h = location.hash.replace("#/", "").replace("#", "");
  return PAGINAS[h] ? h : "visao-geral";
}

export function irPara(id) { location.hash = `#/${id}`; }
