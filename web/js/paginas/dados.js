/* Tela "Dados e exportação": botões de download e tabela paginada dos registros. */

import { erroHtml, esqueleto } from "../componentes/blocos.js";
import { ligarExportar } from "../componentes/cabecalho.js";
import { api } from "../nucleo/api.js";
import { estado } from "../nucleo/estado.js";
import { query, termo } from "../nucleo/filtros.js";
import { ico } from "../nucleo/icones.js";
import { $, dataBR, esc, fmt } from "../nucleo/util.js";

const COLUNAS = [["data_notificacao", "Notificação"], ["data_sintomas", "Início sintomas"], ["sem_epi", "Sem. epi."],
                 ["mun_res", "Município de residência"], ["mun_not", "Município de notificação"], ["idade", "Idade"],
                 ["sexo", "Sexo"], ["raca", "Raça/cor"], ["classificacao", "Classificação"],
                 ["criterio_confirmacao", "Critério"], ["evolucao_caso", "Evolução"], ["hospitalizado", "Hospitalizado"]];

function celula(coluna, valor) {
  if (valor === null || valor === undefined) return "";
  if (coluna.startsWith("data_")) return dataBR(valor);
  if (coluna === "idade") return valor < 1 ? "< 1" : fmt(Math.floor(valor));
  return esc(valor);
}

export async function montar(raiz, pedido) {
  raiz.insertAdjacentHTML("beforeend", `
    <section class="card card-corpo" style="margin-bottom:14px">
      <h2>Baixar os dados filtrados</h2><p class="card-sub">Os arquivos respeitam todos os filtros acima.</p>
      <div class="passos" style="margin-top:12px">
        <button class="btn" data-exportar="xlsx" style="justify-content:flex-start">${ico("baixar")}Planilha Excel (.xlsx)</button>
        <button class="btn" data-exportar="csv" style="justify-content:flex-start">${ico("baixar")}CSV – colunas principais</button>
        <button class="btn" data-exportar="csv_completo" style="justify-content:flex-start">${ico("baixar")}CSV – ficha completa do SINAN</button>
      </div>
    </section>
    <section class="card card-corpo" style="margin-bottom:14px">
      <div class="card-titulo"><div><h2>Registros</h2><p class="card-sub" id="regs-sub"></p></div></div>
      <div id="regs">${esqueleto(400)}</div>
    </section>`);
  ligarExportar(raiz);

  const carregar = async (pagina) => {
    let d;
    try { d = await api(`/api/registros?${query({ pagina })}`); } catch (e) { $("#regs").innerHTML = erroHtml(e); return; }
    if (pedido !== estado.pedido) return;
    const ini = d.pagina * d.por_pagina;
    const paginas = Math.max(1, Math.ceil(d.total / d.por_pagina));
    $("#regs-sub").textContent = `${fmt(d.total)} ${termo()} · mais recentes primeiro`;
    $("#regs").innerHTML = `<div class="tabela-wrap"><table><thead><tr>${COLUNAS.map(([, r]) => `<th>${r}</th>`).join("")}</tr></thead>
      <tbody>${d.linhas.map((l) => `<tr>${COLUNAS.map(([c]) => `<td class="${c === "idade" || c === "sem_epi" ? "num" : ""}">${celula(c, l[c])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>
      <div class="paginacao"><span>${fmt(ini + 1)}–${fmt(Math.min(ini + d.por_pagina, d.total))} de ${fmt(d.total)}</span>
        <div class="btns"><button class="btn" id="pag-ant" ${d.pagina === 0 ? "disabled" : ""}>Anterior</button>
        <span style="align-self:center">Página ${d.pagina + 1} de ${paginas}</span>
        <button class="btn" id="pag-prox" ${d.pagina + 1 >= paginas ? "disabled" : ""}>Próxima</button></div></div>`;
    $("#pag-ant").onclick = () => carregar(d.pagina - 1);
    $("#pag-prox").onclick = () => carregar(d.pagina + 1);
  };
  carregar(0);
}
