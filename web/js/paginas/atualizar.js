/* Tela "Atualizar dados": escolher o que baixar, acompanhar o download e remover dados. */

import { erroHtml, esqueleto } from "../componentes/blocos.js";
import { api, postJSON } from "../nucleo/api.js";
import { ico } from "../nucleo/icones.js";
import { recarregarMeta } from "../nucleo/meta.js";
import { paginaAtual } from "../nucleo/navegacao.js";
import { $, $$, esc, fmt, norm } from "../nucleo/util.js";

let timerStatus = null;

export async function montar(raiz) {
  raiz.insertAdjacentHTML("beforeend", `<div id="atu">${esqueleto(400)}</div>`);
  let d;
  try { d = await api("/api/dados"); } catch (e) { $("#atu").innerHTML = erroHtml(e); return; }
  const sel = { ufs: new Set(d.config.ufs), agravos: new Set(d.config.agravos), anos: new Set(d.config.anos) };

  const desenhar = () => {
    $("#atu").innerHTML = htmlTela(d, sel);
    ligar();
    mostrarJob(d.job);
  };

  const alternar = (set, v) => set.has(v) ? set.delete(v) : set.add(v);
  const filtrarAg = (t) => {
    $$("#lista-ag label").forEach((l) => { l.style.display = !t || norm(l.textContent).includes(norm(t)) ? "" : "none"; });
  };

  const ligar = () => {
    $$("[data-s-uf]").forEach((b) => b.onclick = () => { alternar(sel.ufs, b.dataset.sUf); desenhar(); });
    $$("[data-s-ano]").forEach((b) => b.onclick = () => { alternar(sel.anos, +b.dataset.sAno); desenhar(); });
    $$("[data-s-ag]").forEach((c) => c.onchange = () => {
      alternar(sel.agravos, c.dataset.sAg);
      const busca = $("#busca-ag").value;
      desenhar();
      $("#busca-ag").value = busca;
      filtrarAg(busca);
    });
    $("#busca-ag").oninput = (e) => filtrarAg(e.target.value);
    $("#consultar").onclick = async (e) => {
      const botao = e.currentTarget;
      botao.disabled = true; botao.lastChild.textContent = "Consultando...";
      try { d = await postJSON("/api/dados/listar"); desenhar(); }
      catch (err) { $("#job").innerHTML = erroHtml(err); botao.disabled = false; botao.lastChild.textContent = "Consultar DATASUS"; }
    };
    $("#iniciar").onclick = async () => {
      try {
        const job = await postJSON("/api/dados/atualizar",
          { ufs: [...sel.ufs], agravos: [...sel.agravos], anos: [...sel.anos], forcar: $("#forcar").checked });
        $("#iniciar").disabled = true;
        mostrarJob(job);
        acompanhar();
      } catch (err) { $("#job").innerHTML = erroHtml(err); }
    };
    const rem = $("#remover");
    $$("[data-rem]").forEach((c) => c.onchange = () => { rem.disabled = !$$("[data-rem]:checked").length; });
    rem.onclick = async () => {
      const itens = $$("[data-rem]:checked").map((c) => c.dataset.rem);
      if (!confirm(`Remover ${itens.length} arquivo(s) do computador?`)) return;
      d = await postJSON("/api/dados/remover", { itens });
      await recarregarMeta();
      desenhar();
    };
  };

  /** Consulta o andamento a cada segundo até o download terminar. */
  const acompanhar = () => {
    clearInterval(timerStatus);
    timerStatus = setInterval(async () => {
      if (paginaAtual() !== "atualizar") { clearInterval(timerStatus); return; }
      const job = await api("/api/dados/status").catch(() => null);
      if (!job) return;
      mostrarJob(job);
      if (!job.rodando) {
        clearInterval(timerStatus);
        d = await api("/api/dados");
        await recarregarMeta();
        d.job = job;
        desenhar();
      }
    }, 1000);
  };

  desenhar();
  if (d.job.rodando) acompanhar();
}

function htmlTela(d, sel) {
  const anosDisp = [...new Set(d.catalogo.filter((c) => !sel.agravos.size || sel.agravos.has(c.codigo)).flatMap((c) => c.anos))].sort((a, b) => b - a);
  const anos = anosDisp.length ? anosDisp : Array.from({ length: 27 }, (_, i) => new Date().getFullYear() - i);
  const tamanho = d.catalogo.filter((c) => sel.agravos.has(c.codigo))
    .reduce((s, c) => s + [...sel.anos].reduce((t, a) => t + (c.tamanhos[a] || 0), 0), 0);
  const pronto = sel.ufs.size && sel.agravos.size && sel.anos.size;
  return `
    <section class="card card-corpo" style="margin-bottom:14px">
      <div class="passos">
        <div class="passo"><span class="n">1</span><div><b>Precisa de internet</b><br><span class="card-sub">Os arquivos vêm do FTP público do DATASUS.</span></div></div>
        <div class="passo"><span class="n">2</span><div><b>Filtra e guarda</b><br><span class="card-sub">Só as UFs escolhidas ficam no computador (pasta dados/).</span></div></div>
        <div class="passo"><span class="n">3</span><div><b>Depois, offline</b><br><span class="card-sub">O painel funciona sem internet.</span></div></div>
      </div>
    </section>
    <div class="grade g2">
      <section class="card card-corpo">
        <div class="card-titulo"><h2>O que baixar</h2>
          <button class="btn" id="consultar">${ico("atualizar")}Consultar DATASUS</button></div>
        <p class="card-sub">${d.listagem_em ? `Lista do DATASUS consultada em ${new Date(d.listagem_em).toLocaleString("pt-BR")}` : "Clique em “Consultar DATASUS” para ver os anos disponíveis."}</p>
        <div class="grupo" style="margin-top:14px"><span class="rotulo">UFs</span>
          <div class="opcoes-grade">${["BR", ...d.ufs].map((u) => `<button class="chip" data-s-uf="${u}" aria-pressed="${sel.ufs.has(u)}" title="${u === "BR" ? "Brasil inteiro (muito pesado)" : esc(d.ufs_nome[u])}">${u}</button>`).join("")}</div></div>
        <div class="grupo" style="margin-top:16px"><span class="rotulo">Anos</span>
          <div class="opcoes-grade anos">${anos.map((a) => `<button class="chip" data-s-ano="${a}" aria-pressed="${sel.anos.has(a)}">${a}</button>`).join("")}</div></div>
      </section>
      <section class="card card-corpo">
        <h2>Doenças e agravos</h2>
        <div class="busca" style="margin-top:12px">${ico("busca")}<input id="busca-ag" type="search" placeholder="Buscar agravo..." style="width:100%" aria-label="Buscar agravo"></div>
        <div class="lista-check" id="lista-ag">${d.catalogo.map((c) => `<label data-nome="${esc(c.nome.toLowerCase())}"><input type="checkbox" data-s-ag="${c.codigo}" ${sel.agravos.has(c.codigo) ? "checked" : ""}>${esc(c.nome)}<small>${c.codigo}</small></label>`).join("")}</div>
      </section>
    </div>
    <section class="card card-corpo" style="margin-bottom:14px">
      ${sel.ufs.has("BR") ? `<div class="alerta">${ico("alerta")}<span>Brasil inteiro gera arquivos grandes (a dengue de um único ano passa de 6 milhões de linhas). Prefira escolher UFs.</span></div>` : ""}
      <div class="card-titulo" style="align-items:center">
        <div><h2>${sel.agravos.size} agravo(s) · ${sel.anos.size} ano(s) · ${[...sel.ufs].join(", ") || "nenhuma UF"}</h2>
          <p class="card-sub">${tamanho ? `Download estimado: ${fmt(tamanho / 1e6)} MB (arquivos nacionais; depois de filtrados ficam bem menores e os originais são apagados).` : "Só baixa o que mudou desde a última vez."}</p></div>
        <div class="acoes-tabela"><label class="card-sub" style="display:flex;gap:8px;align-items:center"><input type="checkbox" id="forcar">Baixar de novo mesmo se atualizado</label>
          <button class="btn btn-prim" id="iniciar" ${pronto && !d.job.rodando ? "" : "disabled"}>${ico("nuvem")}Baixar e processar</button></div>
      </div>
      <div id="job"></div>
    </section>
    ${htmlInventario(d.inventario)}`;
}

function htmlInventario(inventario) {
  const status = { em_dia: '<span class="status ok">Em dia</span>', nova: '<span class="status nova">Há versão nova</span>' };
  return `
    <section class="card card-corpo" style="margin-bottom:14px">
      <div class="card-titulo"><div><h2>Dados no computador</h2><p class="card-sub">${inventario.length} arquivo(s)</p></div>
        <button class="btn" id="remover" disabled>Remover selecionados</button></div>
      ${inventario.length ? `<div class="tabela-wrap"><table><thead><tr><th></th><th>Agravo</th><th class="num">Ano</th><th>Dado</th><th class="num">Registros</th><th>UFs</th><th>No DATASUS</th><th>Baixado em</th></tr></thead>
        <tbody>${inventario.map((v) => `<tr><td><input type="checkbox" data-rem="${v.agravo}_${v.ano}" aria-label="Selecionar ${esc(v.nome)} ${v.ano}"></td><td>${esc(v.nome)}</td><td class="num">${v.ano}</td>
          <td>${v.situacao === "preliminar" ? "Preliminar" : "Final"}</td><td class="num">${fmt(v.registros)}</td><td>${esc(v.ufs.join(", "))}</td>
          <td>${status[v.status] || '<span class="status neutro">Não verificado</span>'}</td>
          <td>${new Date(v.processado_em).toLocaleString("pt-BR")}</td></tr>`).join("")}</tbody></table></div>`
        : `<div class="vazio">${ico("nuvem")}<h2>Nenhum dado ainda</h2><p>Escolha acima o que baixar.</p></div>`}
    </section>`;
}

/** Barra de progresso ou resultado do download. */
function mostrarJob(job) {
  const el = $("#job");
  if (!el) return;
  if (job.rodando) {
    el.innerHTML = `<div class="progresso"><div style="width:${(100 * job.fracao).toFixed(1)}%"></div></div>
      <div class="card-sub"><b style="color:var(--text)">${esc(job.tarefa)}</b> — ${esc(job.mensagem)}</div>`;
    return;
  }
  if (job.erro) { el.innerHTML = erroHtml(job.erro); return; }
  const r = job.resultado;
  if (!r) { el.innerHTML = ""; return; }
  const bloco = (tipo, tit, lista) => lista.length ? `<div class="alerta ${tipo}" style="align-items:flex-start">${ico(tipo === "erro" || tipo === "" ? "alerta" : "info")}<div><b>${tit}</b><br>${lista.map(esc).join("<br>")}</div></div>` : "";
  el.innerHTML = `<div style="margin-top:12px">${bloco("info", "Concluído", r.sucesso)}${bloco("info", "Já estavam atualizados", r.pulados)}
    ${bloco("", "Não existem no DATASUS", r.indisponiveis)}${bloco("erro", "Erros", r.erros)}</div>`;
}
