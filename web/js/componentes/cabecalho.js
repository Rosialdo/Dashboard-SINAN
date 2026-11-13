/* Cabeçalho (título, subtítulo, botão Exportar) e rodapé das telas. */

import { baixar } from "../nucleo/api.js";
import { estado, PAGINAS } from "../nucleo/estado.js";
import { agravoAtual, areaNome, periodoTexto, query } from "../nucleo/filtros.js";
import { ico } from "../nucleo/icones.js";
import { nomeMarca } from "../nucleo/meta.js";
import { $, $$, esc } from "../nucleo/util.js";
import { fecharSuspensos, suspenso } from "./suspenso.js";

export function htmlCabecalho(id, comExportar) {
  const p = PAGINAS[id];
  const sub = p.filtros && estado.meta.agravos.length
    ? `<div class="subtitulo">${esc(agravoAtual().nome)} · ${esc(areaNome())} · ${periodoTexto()}</div>` : "";
  const exp = comExportar ? `
    <div class="suspenso" id="exportar">
      <button class="btn" id="exportar-btn">${ico("baixar")}Exportar ${ico("seta", 'style="width:16px;height:16px"')}</button>
      <div class="suspenso-menu">
        <button class="menu-opcao" data-exportar="xlsx">Planilha Excel (.xlsx)<small>Registros + resumos por município, semana e ano</small></button>
        <button class="menu-opcao" data-exportar="csv">CSV – colunas principais<small>Uma linha por notificação</small></button>
        <button class="menu-opcao" data-exportar="csv_completo">CSV – ficha completa<small>Todas as colunas originais do SINAN</small></button>
        <button class="menu-opcao" data-exportar="municipios">CSV – resumo por município<small>Casos, incidência e óbitos</small></button>
      </div>
    </div>` : "";
  return `
  <header class="cabecalho">
    <div>
      <p class="migalha">Painel<span>/</span>${p.menu}</p>
      <h1>${p.titulo}</h1>${sub}
    </div>${exp}
  </header>`;
}

/** Liga os botões [data-exportar] de ``raiz`` (menu do cabeçalho e botões soltos). */
export function ligarExportar(raiz) {
  const el = $("#exportar", raiz);
  if (el) suspenso(el, $("#exportar-btn", raiz), false);
  $$("[data-exportar]", raiz).forEach((b) => b.onclick = () => {
    fecharSuspensos();
    baixar(`/api/exportar?${query({ formato: b.dataset.exportar })}`);
  });
}

export function htmlRodape(esquerda) {
  const m = estado.meta;
  const quando = m.atualizado_em ? `Dados baixados em ${new Date(m.atualizado_em).toLocaleDateString("pt-BR")}` : "";
  return `<footer class="rodape"><span>${esquerda || quando}</span><span><b>${esc(nomeMarca())}</b> · Monitoramento para decisões em saúde</span></footer>`;
}
