/* Menus que abrem ao clicar (período, mais filtros, exportar). */

import { estado } from "../nucleo/estado.js";
import { $, $$ } from "../nucleo/util.js";

/**
 * Liga o botão ao menu ``el``. Com ``manterAberto``, o menu continua aberto
 * depois que a tela é remontada (útil nos filtros, que remontam a cada clique).
 */
export function suspenso(el, botao, manterAberto = true) {
  if (!el) return;
  if (estado._reabrir === el.id) el.classList.add("aberto");
  botao.onclick = (e) => {
    e.stopPropagation();
    const abrir = !el.classList.contains("aberto");
    fecharSuspensos();
    if (abrir) { el.classList.add("aberto"); estado._reabrir = manterAberto ? el.id : null; }
  };
  $(".suspenso-menu", el).onclick = (e) => e.stopPropagation();
}

export function fecharSuspensos() {
  $$(".suspenso.aberto").forEach((s) => s.classList.remove("aberto"));
  estado._reabrir = null;
}

/** Fecha os menus ao clicar fora ou apertar Esc. Chamado uma vez ao iniciar. */
export function ligarFechamentoGlobal() {
  document.addEventListener("click", fecharSuspensos);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") fecharSuspensos(); });
}
