/* Dica flutuante (#tooltip) dos ícones "i" e dos municípios no mapa. */

import { $ } from "../nucleo/util.js";

export const dica = () => $("#tooltip");

/** Mostra ``html`` perto do ponto (x, y) da tela. */
export function mostrarDica(html, x, y) {
  const tip = dica();
  tip.innerHTML = html;
  tip.style.display = "block";
  tip.style.left = Math.min(window.innerWidth - tip.offsetWidth - 8, x) + "px";
  tip.style.top = y + "px";
}

export function esconderDica() { dica().style.display = "none"; }

/** Liga as dicas dos elementos com [data-tip]. Chamado uma vez ao iniciar. */
export function ligarDicas() {
  document.addEventListener("mouseover", (e) => {
    const alvo = e.target.closest("[data-tip]");
    const tip = dica();
    if (!alvo) { tip.style.display = "none"; return; }
    tip.textContent = alvo.dataset.tip;
    tip.style.display = "block";
    const r = alvo.getBoundingClientRect();
    tip.style.left = Math.min(window.innerWidth - tip.offsetWidth - 8, Math.max(8, r.left - 10)) + "px";
    tip.style.top = (r.bottom + 8) + "px";
  });
}
