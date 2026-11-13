/* Avisos amarelos/azuis abaixo dos filtros (dados preliminares, avisos do agravo). */

import { estado } from "../nucleo/estado.js";
import { agravoAtual } from "../nucleo/filtros.js";
import { ico } from "../nucleo/icones.js";
import { $$, esc } from "../nucleo/util.js";

export function htmlAlertas() {
  const ag = agravoAtual(), f = estado.f, m = estado.meta;
  const avisos = [];
  const prelim = ag.preliminares.filter((a) => a >= f.ini && a <= f.fim);
  if (prelim.length) {
    const anos = prelim.length === 1 ? `de ${prelim[0]}` : `de ${prelim.slice(0, -1).join(", ")} e ${prelim.at(-1)}`;
    avisos.push(["prelim-" + prelim.join(), "", `Dados ${anos} são preliminares e podem mudar conforme os casos são investigados e encerrados.`]);
  }
  const ufsArea = f.ufs.length ? f.ufs : m.ufs;
  if (ag.aviso && (!ag.aviso_so_amazonia || ufsArea.some((u) => m.amazonia_legal.includes(u)))) {
    avisos.push(["aviso-" + ag.codigo, "info", ag.aviso]);
  }
  return avisos.filter(([k]) => !estado.dispensados.has(k)).map(([k, tipo, txt]) => `
    <div class="alerta ${tipo}" role="status">${ico(tipo === "info" ? "info" : "alerta")}<span>${esc(txt)}</span>
      <button class="fechar" data-dispensar="${k}" aria-label="Fechar aviso">${ico("fechar")}</button></div>`).join("");
}

export function ligarAlertas(raiz) {
  $$("[data-dispensar]", raiz).forEach((b) => b.onclick = () => {
    estado.dispensados.add(b.dataset.dispensar);
    b.closest(".alerta").remove();
  });
}
