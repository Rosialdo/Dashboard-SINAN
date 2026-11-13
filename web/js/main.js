/* Dashboard SINAN: ponto de entrada da interface.

Sem framework e sem etapa de build: módulos JavaScript nativos + Plotly local.

  nucleo/       estado, filtros, API, utilidades (sem HTML)
  componentes/  pedaços de tela reutilizáveis (filtros, indicadores, gráficos...)
  paginas/      uma tela por arquivo, cada uma exporta montar(raiz, pedido)
  roteador.js   monta a tela atual
*/

import { erroHtml } from "./componentes/blocos.js";
import { ligarDicas } from "./componentes/dica.js";
import { redesenhar } from "./componentes/graficos.js";
import { ligarFechamentoGlobal } from "./componentes/suspenso.js";
import { definirRender, estado, guardar } from "./nucleo/estado.js";
import { recarregarMeta } from "./nucleo/meta.js";
import { $, $$ } from "./nucleo/util.js";
import { render } from "./roteador.js";

function aplicarTema(tema) {
  document.documentElement.dataset.theme = tema;
  guardar.gravar("tema", tema);
  try { localStorage.setItem("tema", tema); } catch (e) { /* sem armazenamento */ }
  $$(".tema button").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.tema === tema)));
  redesenhar(); // gráficos pegam as cores do tema novo
}

/** Qualquer erro inesperado aparece na tela, em vez de deixar a página em branco. */
function mostrarErroGlobal(e) {
  const el = $("#pagina");
  if (el) el.insertAdjacentHTML("afterbegin", erroHtml(`Erro na interface: ${e?.message || e}`));
}

async function iniciar() {
  window.addEventListener("error", (ev) => mostrarErroGlobal(ev.error || ev.message));
  window.addEventListener("unhandledrejection", (ev) => mostrarErroGlobal(ev.reason));
  definirRender(render);
  ligarFechamentoGlobal();
  ligarDicas();

  aplicarTema(document.documentElement.dataset.theme || "light");
  $$(".tema button").forEach((b) => b.onclick = () => aplicarTema(b.dataset.tema));
  $("#menu-abrir").onclick = () => $("#sidebar").classList.add("aberta");
  $("#menu-fechar").onclick = () => $("#sidebar").classList.remove("aberta");
  $("#sidebar-fundo").onclick = () => $("#sidebar").classList.remove("aberta");
  window.addEventListener("hashchange", () => { estado.mapaSel = null; render(); });

  try {
    await recarregarMeta();
  } catch (e) {
    $("#pagina").innerHTML = erroHtml("Não foi possível falar com o servidor do dashboard. Feche e abra de novo o ABRIR_DASHBOARD.bat.");
    return;
  }
  render();
}

iniciar();
