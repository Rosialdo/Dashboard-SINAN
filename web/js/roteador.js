/* Monta a tela atual: menu, cabeçalho, filtros, avisos, conteúdo da página e rodapé.

Para criar uma tela nova:
  1. crie paginas/minha-tela.js exportando ``montar(raiz, pedido)``;
  2. registre em PAGINAS (nucleo/estado.js) e em MONTADORES (abaixo).
*/

import { htmlAlertas, ligarAlertas } from "./componentes/alertas.js";
import { htmlCabecalho, htmlRodape, ligarExportar } from "./componentes/cabecalho.js";
import { htmlFiltros, ligarFiltros } from "./componentes/filtros.js";
import { limparGraficos } from "./componentes/graficos.js";
import { estado, PAGINAS } from "./nucleo/estado.js";
import { ico } from "./nucleo/icones.js";
import { nomeMarca } from "./nucleo/meta.js";
import { paginaAtual } from "./nucleo/navegacao.js";
import { $ } from "./nucleo/util.js";
import * as atualizar from "./paginas/atualizar.js";
import * as dados from "./paginas/dados.js";
import * as mapa from "./paginas/mapa.js";
import * as perfil from "./paginas/perfil.js";
import * as sobre from "./paginas/sobre.js";
import * as variaveis from "./paginas/variaveis.js";
import * as visao from "./paginas/visao.js";

const MONTADORES = {
  "visao-geral": visao.montar,
  "mapa": mapa.montar,
  "perfil": perfil.montar,
  "variaveis": variaveis.montar,
  "dados": dados.montar,
  "atualizar": atualizar.montar,
  "sobre": sobre.montar,
};

const NOTA_MAPA = "<b>Incidência</b> = casos ÷ soma da população dos anos selecionados × 100 mil "
  + "(população estimada pelo IBGE; anos sem estimativa são interpolados).";

export function montarMenu() {
  const atual = paginaAtual();
  let html = "", secao = "";
  for (const [id, p] of Object.entries(PAGINAS)) {
    if (p.secao !== secao) {
      if (secao) html += '<div class="nav-sep"></div>';
      secao = p.secao;
      html += `<div class="nav-secao">${secao}</div>`;
    }
    html += `<a class="nav-item ${id === atual ? "ativo" : ""}" href="#/${id}" ${id === atual ? 'aria-current="page"' : ""}>${ico(p.icone)}<span>${p.menu}</span></a>`;
  }
  $("#nav").innerHTML = html;
}

export async function render() {
  const id = paginaAtual();
  const pedido = ++estado.pedido; // respostas que chegarem depois de trocar de tela são ignoradas
  limparGraficos();
  montarMenu();
  $("#sidebar").classList.remove("aberta");
  document.title = `${PAGINAS[id].menu} · ${nomeMarca()}`;
  const raiz = $("#pagina");
  const p = PAGINAS[id];

  if (p.filtros && !estado.meta.agravos.length) {
    raiz.innerHTML = htmlCabecalho(id, false) + `<section class="card vazio">${ico("nuvem")}<h2>Ainda não há dados no computador</h2>
      <p>Baixe os dados do SINAN uma vez (precisa de internet). Depois o painel funciona offline.</p>
      <button class="btn btn-prim" onclick="location.hash='#/atualizar'">${ico("atualizar")}Ir para Atualizar dados</button></section>`;
    return;
  }
  raiz.innerHTML = htmlCabecalho(id, p.filtros) + (p.filtros ? htmlFiltros() + htmlAlertas() : "");
  if (p.filtros) { ligarFiltros(raiz); ligarAlertas(raiz); }
  ligarExportar(raiz);
  const conteudo = document.createElement("div");
  raiz.appendChild(conteudo);
  await MONTADORES[id](conteudo, pedido);
  if (pedido !== estado.pedido) return;
  raiz.insertAdjacentHTML("beforeend", htmlRodape(id === "mapa" ? NOTA_MAPA : ""));
}
