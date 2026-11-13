/* Tela "Outras variáveis": lista agrupada de campos da ficha e a distribuição do escolhido. */

import { barrasHtml } from "../componentes/barras.js";
import { erroHtml, esqueleto, vazioHtml } from "../componentes/blocos.js";
import { api } from "../nucleo/api.js";
import { estado } from "../nucleo/estado.js";
import { query, termo } from "../nucleo/filtros.js";
import { ico } from "../nucleo/icones.js";
import { $, $$, esc, fmt, norm } from "../nucleo/util.js";

export async function montar(raiz, pedido) {
  raiz.insertAdjacentHTML("beforeend", `
    <div class="grade g-vars">
      <section class="card card-corpo"><h2>Variáveis da ficha</h2>
        <p class="card-sub">Informações da ficha de notificação, por assunto</p>
        <div class="busca" style="margin-top:10px">${ico("busca")}<input id="busca-var" type="search" placeholder="Buscar variável..." style="width:100%" aria-label="Buscar variável"></div>
        <div class="lista-vars" id="lista-vars">${esqueleto(400)}</div></section>
      <section class="card card-corpo"><div class="card-titulo"><div><h2 id="var-titulo">Variável</h2><p class="card-sub" id="var-sub"></p></div></div>
        <div id="var-corpo">${esqueleto(360)}</div></section>
    </div>`);
  let lista;
  try { lista = await api(`/api/variaveis?agravo=${estado.f.agravo}`); } catch (e) { $("#var-corpo").innerHTML = erroHtml(e); return; }
  if (pedido !== estado.pedido) return;
  if (!lista.length) {
    $("#lista-vars").innerHTML = vazioHtml("Não há tabela de rótulos para este agravo.");
    $("#var-corpo").innerHTML = "";
    return;
  }
  // ao trocar de doença o mesmo id pode ser outra variável: volta para a primeira (a principal)
  if (estado.varAgravo !== estado.f.agravo || !lista.some((v) => v.id === estado.varId)) {
    estado.varId = lista[0].id;
    estado.varAgravo = estado.f.agravo;
  }
  let vez = 0; // ignora respostas de cliques antigos

  const desenharLista = (filtro = "") => {
    const achados = lista.filter((v) => !filtro || norm(`${v.nome} ${v.rotulo} ${v.campo} ${v.grupo}`).includes(norm(filtro)));
    let grupo = null;
    $("#lista-vars").innerHTML = achados.map((v) => {
      const cab = v.grupo !== grupo ? `<div class="vars-grupo">${esc(v.grupo)}</div>` : "";
      grupo = v.grupo;
      return `${cab}<button data-var="${v.id}" class="${v.id === estado.varId ? "ativo" : ""}"
        title="No TabNet: ${esc(v.rotulo)} (campo ${esc(v.campo)})">${esc(v.nome)}</button>`;
    }).join("") || vazioHtml("Nenhuma variável encontrada.");
    $$("[data-var]").forEach((b) => b.onclick = () => { estado.varId = +b.dataset.var; desenharLista($("#busca-var").value); carregar(); });
  };

  const carregar = async () => {
    $("#var-corpo").innerHTML = esqueleto(360);
    const minhaVez = ++vez;
    try {
      const d = await api(`/api/variavel?${query({ id: estado.varId })}`);
      if (minhaVez !== vez) return;
      const total = d.valores.reduce((s, r) => s + r.casos, 0);
      $("#var-titulo").textContent = d.rotulo;
      $("#var-sub").textContent = `${fmt(total)} ${termo()}`;
      $("#var-sub").title = `No TabNet: ${d.rotulo_tabnet} (campo ${d.campo})`;
      $("#var-corpo").innerHTML = barrasHtml(d.valores, total);
    } catch (e) { $("#var-corpo").innerHTML = erroHtml(e); }
  };

  $("#busca-var").oninput = (e) => desenharLista(e.target.value);
  desenharLista();
  carregar();
}
