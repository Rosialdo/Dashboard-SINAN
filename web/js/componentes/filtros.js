/* Barra de filtros do topo das telas de análise. */

import { estado } from "../nucleo/estado.js";
import { agravoAtual, mudarFiltro } from "../nucleo/filtros.js";
import { ico } from "../nucleo/icones.js";
import { $, $$, esc } from "../nucleo/util.js";
import { suspenso } from "./suspenso.js";

const SEXOS = [["Feminino", "Feminino"], ["Masculino", "Masculino"], ["Ignorado", "Não informado"]];

export function htmlFiltros() {
  const m = estado.meta, f = estado.f, ag = agravoAtual();
  const opcAg = m.agravos.map((a) => `<option value="${a.codigo}" ${a.codigo === f.agravo ? "selected" : ""}>${esc(a.nome)}</option>`).join("");
  const ufsArea = f.ufs.length ? f.ufs : m.ufs;
  const muns = m.municipios.filter((x) => !ufsArea.length || ufsArea.includes(x.uf));
  const variasUf = new Set(muns.map((x) => x.uf)).size > 1;
  const opcMun = `<option value="">Todos</option>` + muns.map((x) =>
    `<option value="${x.cod6}" ${x.cod6 === f.mun ? "selected" : ""}>${esc(x.municipio)}${variasUf || f.mun === x.cod6 ? ` (${x.uf})` : ""}</option>`).join("");
  const extras = f.sexo.length + f.faixa.length + f.ufs.length;
  return `
  <section class="card filtros" aria-label="Filtros">
    <div class="campo campo-agravo"><label for="f-agravo">Agravo</label><select id="f-agravo" class="select">${opcAg}</select></div>
    <div class="campo campo-periodo"><span class="rotulo">Período</span>
      <div class="suspenso" id="periodo">
        <button class="select" id="periodo-btn" aria-haspopup="true">${f.ini === f.fim ? f.ini : `${f.ini} – ${f.fim}`}</button>
        <div class="suspenso-menu esq painel-periodo">
          <div class="linha">
            <div class="campo"><label for="f-ini">De</label><select id="f-ini" class="select">${ag.anos.map((a) => `<option ${a === f.ini ? "selected" : ""}>${a}</option>`).join("")}</select></div>
            <div class="campo"><label for="f-fim">Até</label><select id="f-fim" class="select">${ag.anos.map((a) => `<option ${a === f.fim ? "selected" : ""}>${a}</option>`).join("")}</select></div>
          </div>
          <div class="atalhos">
            <button class="chip" data-anos="1">Último ano</button>
            <button class="chip" data-anos="3">Últimos 3 anos</button>
            <button class="chip" data-anos="5">Últimos 5 anos</button>
            <button class="chip" data-anos="0">Todos</button>
          </div>
        </div>
      </div>
    </div>
    <div class="campo campo-mun"><label for="f-mun">Município</label><select id="f-mun" class="select">${opcMun}</select></div>
    <div class="campo campo-local"><label for="f-local">Contar por</label>
      <select id="f-local" class="select" title="Município de residência do paciente ou município onde o caso foi notificado">
        <option value="res" ${f.local === "res" ? "selected" : ""}>Residência</option>
        <option value="not" ${f.local === "not" ? "selected" : ""}>Notificação</option>
      </select></div>
    <div class="suspenso" id="mais">
      <button class="btn" id="mais-btn">${ico("funil")}Mais filtros${extras ? ` <span class="badge">${extras}</span>` : ""}</button>
      <div class="suspenso-menu esq painel-filtros">
        ${m.ufs.length > 1 ? `<div class="grupo"><span class="rotulo">UF</span><div class="chips">${m.ufs.map((u) =>
          `<button class="chip" data-uf="${u}" aria-pressed="${f.ufs.includes(u)}">${u}</button>`).join("")}</div></div>` : ""}
        <div class="grupo"><span class="rotulo">Sexo</span><div class="chips">${SEXOS.map(([s, r]) =>
          `<button class="chip" data-sexo="${s}" aria-pressed="${f.sexo.includes(s)}">${r}</button>`).join("")}</div></div>
        <div class="grupo"><span class="rotulo">Faixa etária (anos)</span><div class="chips">${m.faixas.map((s) =>
          `<button class="chip" data-faixa="${s}" aria-pressed="${f.faixa.includes(s)}">${s}</button>`).join("")}</div></div>
        <button class="btn-link" id="limpar-extras">Limpar estes filtros</button>
      </div>
    </div>
    ${htmlContagem(ag, f)}
  </section>`;
}

/** Botões Confirmados / Prováveis / Notificações. */
function htmlContagem(ag, f) {
  if (ag.todos_casos) return `<div class="filtros-fim"><span class="pilula">Toda notificação é um caso</span></div>`;
  const ops = [["confirmados", "Confirmados"]];
  if (ag.provaveis) ops.push(["provaveis", "Prováveis"]);
  ops.push(["todas", "Notificações"]);
  return `<div class="filtros-fim"><div class="segmentado" role="group" aria-label="Contar">${ops.map(([v, r]) =>
    `<button data-contagem="${v}" aria-pressed="${f.contagem === v}">${r}</button>`).join("")}</div></div>`;
}

export function ligarFiltros(raiz) {
  const f = estado.f;
  $("#f-agravo", raiz).onchange = (e) => mudarFiltro({ agravo: e.target.value, ini: null, fim: null });
  $("#f-mun", raiz).onchange = (e) => mudarFiltro({ mun: e.target.value });
  $("#f-local", raiz).onchange = (e) => mudarFiltro({ local: e.target.value });
  $("#f-ini", raiz).onchange = (e) => mudarFiltro({ ini: +e.target.value });
  $("#f-fim", raiz).onchange = (e) => mudarFiltro({ fim: +e.target.value });
  $$("[data-anos]", raiz).forEach((b) => b.onclick = () => {
    const anos = agravoAtual().anos, n = +b.dataset.anos;
    mudarFiltro({ ini: n ? anos[Math.max(0, anos.length - n)] : anos[0], fim: anos[anos.length - 1] });
  });
  $$("[data-contagem]", raiz).forEach((b) => b.onclick = () => mudarFiltro({ contagem: b.dataset.contagem }));
  const alternar = (lista, v) => lista.includes(v) ? lista.filter((x) => x !== v) : [...lista, v];
  $$("[data-sexo]", raiz).forEach((b) => b.onclick = () => mudarFiltro({ sexo: alternar(f.sexo, b.dataset.sexo) }));
  $$("[data-faixa]", raiz).forEach((b) => b.onclick = () => mudarFiltro({ faixa: alternar(f.faixa, b.dataset.faixa) }));
  $$("[data-uf]", raiz).forEach((b) => b.onclick = () => mudarFiltro({ ufs: alternar(f.ufs, b.dataset.uf), mun: "" }));
  const limpar = $("#limpar-extras", raiz);
  if (limpar) limpar.onclick = () => mudarFiltro({ sexo: [], faixa: [], ufs: [] });
  suspenso($("#periodo", raiz), $("#periodo-btn", raiz));
  suspenso($("#mais", raiz), $("#mais-btn", raiz));
}
