/* Dashboard SINAN — interface (sem dependências externas além do Plotly local). */
"use strict";

// ================================================================ ícones
const I = {
  visao: '<path d="M4 20V10M9.3 20V4M14.6 20v-8M20 20v-5"/>',
  mapa: '<path d="M12 21s-7-6.1-7-11.5A7 7 0 0 1 19 9.5C19 14.9 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
  perfil: '<circle cx="12" cy="8" r="4"/><path d="M4 21c.8-4 4-6 8-6s7.2 2 8 6"/>',
  vars: '<path d="M4 20V13M9.3 20V8M14.6 20V4M20 20v-9"/>',
  baixar: '<path d="M12 3v12M7 10l5 5 5-5M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4"/>',
  atualizar: '<path d="M20 11a8 8 0 0 0-14.9-3.9L3 9.5M4 13a8 8 0 0 0 14.9 3.9L21 14.5"/><path d="M3 4v5.5h5.5M21 20v-5.5h-5.5"/>',
  sobre: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.01"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 7.6v.01"/>',
  alerta: '<path d="M12 3 2 21h20L12 3z" fill="currentColor" stroke="none"/><path d="M12 10v5M12 18v.01" stroke="#fff" stroke-width="2.2"/>',
  fechar: '<path d="M6 6l12 12M18 6 6 18"/>',
  seta: '<path d="m6 9 6 6 6-6"/>',
  direita: '<path d="m9 6 6 6-6 6"/>',
  funil: '<path d="M3 4h18l-7 8.5V19l-4 2v-8.5L3 4z"/>',
  busca: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  mais: '<path d="M12 5v14M5 12h14"/>',
  menos: '<path d="M5 12h14"/>',
  tela: '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
  nuvem: '<path d="M7 18a5 5 0 1 1 .9-9.9A6 6 0 0 1 19.5 10 4 4 0 0 1 18 18H7z"/><path d="M12 11v6M9.5 14.5 12 17l2.5-2.5"/>',
};
const ico = (n, extra = "") => `<svg viewBox="0 0 24 24" ${extra}>${I[n]}</svg>`;

// ================================================================ estado
const PAGINAS = {
  "visao-geral": { titulo: "Evolução epidemiológica", menu: "Visão geral", icone: "visao", secao: "ANÁLISE", filtros: true },
  "mapa": { titulo: "Distribuição territorial", menu: "Mapa e municípios", icone: "mapa", secao: "ANÁLISE", filtros: true },
  "perfil": { titulo: "Perfil dos casos", menu: "Perfil dos casos", icone: "perfil", secao: "ANÁLISE", filtros: true },
  "variaveis": { titulo: "Outras variáveis", menu: "Outras variáveis", icone: "vars", secao: "ANÁLISE", filtros: true },
  "dados": { titulo: "Dados e exportação", menu: "Dados e exportação", icone: "baixar", secao: "ANÁLISE", filtros: true },
  "atualizar": { titulo: "Atualizar dados", menu: "Atualizar dados", icone: "atualizar", secao: "GESTÃO" },
  "sobre": { titulo: "Sobre os dados", menu: "Sobre os dados", icone: "sobre", secao: "GESTÃO" },
};

const guardar = {
  ler(k, padrao) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : padrao; } catch (e) { return padrao; } },
  gravar(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* sem armazenamento */ } },
};

const estado = {
  meta: null,
  f: Object.assign({ agravo: "", ini: null, fim: null, mun: "", local: "res", contagem: "confirmados",
                     sexo: [], faixa: [], ufs: [] }, guardar.ler("filtros", {})),
  dispensados: new Set(),
  pedido: 0,
  varId: 0,
  mapaSel: null,
};

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const nf = new Intl.NumberFormat("pt-BR");
const fmt = (v, casas = 0) => (v === null || v === undefined || Number.isNaN(v)) ? "–"
  : new Intl.NumberFormat("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas }).format(v);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

async function api(caminho, opcoes) {
  const r = await fetch(caminho, opcoes);
  const dados = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(dados.erro || `Erro ${r.status}`);
  return dados;
}

// ================================================================ tema
function aplicarTema(tema) {
  document.documentElement.dataset.theme = tema;
  guardar.gravar("tema", tema);
  try { localStorage.setItem("tema", tema); } catch (e) { /* ok */ }
  $$(".tema button").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.tema === tema)));
  window.dispatchEvent(new Event("tema"));
}

// ================================================================ navegação
function paginaAtual() {
  const h = location.hash.replace("#/", "").replace("#", "");
  return PAGINAS[h] ? h : "visao-geral";
}

function montarMenu() {
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

function irPara(id) { location.hash = `#/${id}`; }

// ================================================================ filtros
function agravoAtual() { return estado.meta.agravos.find((a) => a.codigo === estado.f.agravo); }

function normalizarFiltros() {
  const m = estado.meta;
  if (!m.agravos.length) return;
  if (!agravoAtual()) estado.f.agravo = (m.agravos.find((a) => a.codigo === "DENG") || m.agravos[0]).codigo;
  const ag = agravoAtual();
  const anos = ag.anos;
  if (!anos.includes(estado.f.ini)) estado.f.ini = anos[0];
  if (!anos.includes(estado.f.fim)) estado.f.fim = anos[anos.length - 1];
  if (estado.f.ini > estado.f.fim) [estado.f.ini, estado.f.fim] = [estado.f.fim, estado.f.ini];
  if (estado.f.mun && !m.municipios.some((x) => x.cod6 === estado.f.mun)) estado.f.mun = "";
  estado.f.ufs = estado.f.ufs.filter((u) => m.ufs.includes(u));
  if (ag.todos_casos) estado.f.contagem = "todas";
  else if (estado.f.contagem === "provaveis" && !ag.provaveis) estado.f.contagem = "confirmados";
  else if (estado.f.contagem === "todas" && !ag.todos_casos && !estado.f._todasEscolhida) estado.f.contagem = "confirmados";
  guardar.gravar("filtros", estado.f);
}

function query(extra = {}) {
  const f = estado.f;
  const p = new URLSearchParams({ agravo: f.agravo, ini: f.ini, fim: f.fim, local: f.local, contagem: f.contagem,
                                  mun: f.mun, sexo: f.sexo.join(","), faixa: f.faixa.join(","), ufs: f.ufs.join(","), ...extra });
  return p.toString();
}

function mudarFiltro(mudancas) {
  Object.assign(estado.f, mudancas);
  if ("contagem" in mudancas) estado.f._todasEscolhida = mudancas.contagem === "todas";
  normalizarFiltros();
  estado.mapaSel = null;
  render();
}

function areaNome() {
  const m = estado.meta, f = estado.f;
  if (f.mun) {
    const mu = m.municipios.find((x) => x.cod6 === f.mun);
    return mu ? `${mu.municipio} (${mu.uf})` : f.mun;
  }
  const ufs = f.ufs.length ? f.ufs : m.ufs;
  if (m.brasil && !f.ufs.length) return "Brasil";
  if (ufs.length === 1) return m.ufs_nome[ufs[0]] || ufs[0];
  return ufs.join(", ");
}

function periodoTexto() {
  const f = estado.f;
  return f.ini === f.fim ? `${f.ini}` : `${f.ini} a ${f.fim}`;
}

function termo() {
  const ag = agravoAtual();
  if (ag.todos_casos) return "casos";
  return { confirmados: "casos confirmados", provaveis: "casos prováveis", todas: "notificações" }[estado.f.contagem];
}

function htmlFiltros() {
  const m = estado.meta, f = estado.f, ag = agravoAtual();
  const opcAg = m.agravos.map((a) => `<option value="${a.codigo}" ${a.codigo === f.agravo ? "selected" : ""}>${esc(a.nome)}</option>`).join("");
  const ufsArea = f.ufs.length ? f.ufs : m.ufs;
  const muns = m.municipios.filter((x) => !ufsArea.length || ufsArea.includes(x.uf));
  const variasUf = new Set(muns.map((x) => x.uf)).size > 1;
  const opcMun = `<option value="">Todos</option>` + muns.map((x) =>
    `<option value="${x.cod6}" ${x.cod6 === f.mun ? "selected" : ""}>${esc(x.municipio)}${variasUf || f.mun === x.cod6 ? ` (${x.uf})` : ""}</option>`).join("");
  const extras = f.sexo.length + f.faixa.length + f.ufs.length;
  let seg = "";
  if (!ag.todos_casos) {
    const ops = [["confirmados", "Confirmados"]];
    if (ag.provaveis) ops.push(["provaveis", "Prováveis"]);
    ops.push(["todas", "Notificações"]);
    seg = `<div class="filtros-fim"><div class="segmentado" role="group" aria-label="Contar">${ops.map(([v, r]) =>
      `<button data-contagem="${v}" aria-pressed="${f.contagem === v}">${r}</button>`).join("")}</div></div>`;
  } else {
    seg = `<div class="filtros-fim"><span class="pilula">Toda notificação é um caso</span></div>`;
  }
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
        <div class="grupo"><span class="rotulo">Sexo</span><div class="chips">${["Feminino", "Masculino", "Ignorado"].map((s) =>
          `<button class="chip" data-sexo="${s}" aria-pressed="${f.sexo.includes(s)}">${s}</button>`).join("")}</div></div>
        <div class="grupo"><span class="rotulo">Faixa etária (anos)</span><div class="chips">${m.faixas.map((s) =>
          `<button class="chip" data-faixa="${s}" aria-pressed="${f.faixa.includes(s)}">${s}</button>`).join("")}</div></div>
        <button class="btn-link" id="limpar-extras">Limpar estes filtros</button>
      </div>
    </div>
    ${seg}
  </section>`;
}

function ligarFiltros(raiz) {
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

let suspensoAberto = null;
function suspenso(el, botao, manterAberto = true) {
  if (!el) return;
  if (estado._reabrir === el.id) { el.classList.add("aberto"); suspensoAberto = el; }
  botao.onclick = (e) => {
    e.stopPropagation();
    const abrir = !el.classList.contains("aberto");
    fecharSuspensos();
    if (abrir) { el.classList.add("aberto"); suspensoAberto = el; estado._reabrir = manterAberto ? el.id : null; }
  };
  $(".suspenso-menu", el).onclick = (e) => e.stopPropagation();
}
function fecharSuspensos() {
  $$(".suspenso.aberto").forEach((s) => s.classList.remove("aberto"));
  suspensoAberto = null;
  estado._reabrir = null;
}
document.addEventListener("click", fecharSuspensos);
document.addEventListener("keydown", (e) => { if (e.key === "Escape") fecharSuspensos(); });

// ================================================================ blocos comuns
function htmlCabecalho(id, comExportar) {
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

function ligarExportar(raiz) {
  const el = $("#exportar", raiz);
  if (!el) return;
  suspenso(el, $("#exportar-btn", raiz), false);
  $$("[data-exportar]", raiz).forEach((b) => b.onclick = () => {
    fecharSuspensos();
    window.location = `/api/exportar?${query({ formato: b.dataset.exportar })}`;
  });
}

function htmlAlertas() {
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

function ligarAlertas(raiz) {
  $$("[data-dispensar]", raiz).forEach((b) => b.onclick = () => {
    estado.dispensados.add(b.dataset.dispensar);
    b.closest(".alerta").remove();
  });
}

function kpi(rotulo, valor, ajuda, sub = "", pilula = "") {
  return `<div class="card kpi"><div class="kpi-rotulo">${rotulo}
    <span class="info" data-tip="${esc(ajuda)}" tabindex="0" aria-label="${esc(ajuda)}">${ico("info")}</span></div>
    <div class="kpi-valor">${valor}</div>${sub ? `<div class="kpi-sub">${sub}</div>` : ""}${pilula ? `<span class="pilula">${pilula}</span>` : ""}</div>`;
}

function htmlKpis(ind) {
  const ag = agravoAtual();
  const t = termo();
  const pct = ind.notificacoes ? 100 * ind.confirmados / ind.notificacoes : null;
  const conf = ag.todos_casos
    ? kpi("Casos", fmt(ind.confirmados), "Para este agravo toda notificação é um caso.")
    : kpi("Confirmados", fmt(ind.confirmados), "Notificações com classificação final confirmada.", "",
          pct !== null && estado.f.contagem !== "confirmados" ? `${fmt(pct, 1)}% das notificações` : (pct !== null ? `${fmt(pct, 1)}% das notificações` : ""));
  const inc = ind.incidencia === null
    ? kpi("Incidência", "–", "Não é calculada quando há filtro de sexo ou faixa etária (não há população por esses grupos).")
    : kpi("Incidência", fmt(ind.incidencia, 1), `${cap(t)} por 100 mil habitantes${ind.n_anos > 1 ? " por ano (média do período)" : ""}. População: IBGE.`,
          ind.n_anos > 1 ? "por 100 mil hab./ano" : "por 100 mil hab.");
  const hosp = ind.hosp_informado
    ? kpi("Hospitalizados", fmt(ind.hospitalizados), "Casos confirmados com hospitalização registrada.", "",
          `${fmt(100 * ind.hospitalizados / ind.hosp_informado, 1)}% dos informados`)
    : kpi("Última notificação", ind.ultima_notificacao ? new Date(ind.ultima_notificacao + "T12:00").toLocaleDateString("pt-BR") : "–",
          "Data da notificação mais recente nos dados filtrados.");
  return `<section class="kpis" aria-label="Indicadores">
    ${kpi("Notificações", fmt(ind.notificacoes), "Total de fichas notificadas no período e área, qualquer que seja a classificação.")}
    ${conf}${inc}
    ${kpi("Óbitos", fmt(ind.obitos), "Óbitos pelo agravo notificado entre os casos confirmados (não inclui óbito por outras causas).")}
    ${kpi("Letalidade", ind.letalidade === null ? "–" : `${fmt(ind.letalidade, 2)}%`, "Óbitos pelo agravo ÷ casos confirmados × 100.")}
    ${hosp}
  </section>`;
}
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

function htmlRodape(esquerda) {
  const m = estado.meta;
  const quando = m.atualizado_em ? `Dados baixados em ${new Date(m.atualizado_em).toLocaleDateString("pt-BR")}` : "";
  return `<footer class="rodape"><span>${esquerda || quando}</span><span><b>${esc(nomeMarca())}</b> · Monitoramento para decisões em saúde</span></footer>`;
}

function nomeMarca() {
  const m = estado.meta;
  if (!m || m.brasil || m.ufs.length !== 1) return "Vigilância SINAN";
  return `Vigilância ${m.ufs[0]}`;
}

function esqueleto(alt) { return `<div class="esqueleto" style="height:${alt}px"></div>`; }

function erroHtml(e) { return `<div class="alerta erro">${ico("alerta")}<span>${esc(e.message || e)}</span></div>`; }

// tooltip dos ícones "i"
document.addEventListener("mouseover", (e) => {
  const alvo = e.target.closest("[data-tip]");
  const tip = $("#tooltip");
  if (!alvo) { tip.style.display = "none"; return; }
  tip.textContent = alvo.dataset.tip;
  tip.style.display = "block";
  const r = alvo.getBoundingClientRect();
  tip.style.left = Math.min(window.innerWidth - tip.offsetWidth - 8, Math.max(8, r.left - 10)) + "px";
  tip.style.top = (r.bottom + 8) + "px";
});

// ================================================================ gráficos (Plotly)
function layoutBase(extra = {}) {
  const fonte = { family: getComputedStyle(document.body).fontFamily, size: 13, color: css("--text-2") };
  return Object.assign({
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", font: fonte,
    margin: { l: 48, r: 12, t: 10, b: 40 }, showlegend: false, separators: ",.",
    hoverlabel: { bgcolor: css("--text"), bordercolor: css("--text"), font: { color: css("--bg"), size: 13, family: fonte.family } },
    xaxis: { gridcolor: css("--grid"), linecolor: css("--eixo"), zeroline: false, tickfont: { color: css("--text-2") }, fixedrange: true },
    yaxis: { gridcolor: css("--grid"), linecolor: css("--eixo"), zeroline: false, rangemode: "tozero", tickfont: { color: css("--text-2") },
             fixedrange: true, separatethousands: true },
  }, extra);
}
const CFG = { displayModeBar: false, responsive: true, locale: "pt-BR" };
const graficos = [];
function plot(el, traces, layout) {
  Plotly.react(el, traces, layout, CFG);
  if (!graficos.includes(el)) graficos.push(el);
}

function barrasHtml(lista, total) {
  const max = Math.max(1, ...lista.map((d) => d.casos));
  total = total || lista.reduce((s, d) => s + d.casos, 0) || 1;
  return `<div class="barras">${lista.map((d) => `
    <div class="barra-linha"><span class="barra-rotulo" title="${esc(d.valor)}">${esc(d.valor || "Ign/Branco")}</span>
      <div class="barra-trilho"><div class="barra-valor-barra" style="width:${100 * d.casos / max}%"></div></div>
      <span class="barra-num"><b>${fmt(d.casos)}</b> · ${fmt(100 * d.casos / total, 1)}%</span></div>`).join("")}</div>`;
}

// ================================================================ páginas
async function paginaVisao(raiz, n) {
  raiz.insertAdjacentHTML("beforeend", `
    <div id="kpis">${esqueleto(120)}</div>
    <section class="card card-corpo" style="margin-bottom:14px">
      <div class="card-titulo"><div><h2 id="t-semana">Casos por semana epidemiológica</h2>
        <p class="card-sub">Semana do início dos sintomas (ou do diagnóstico/notificação quando não informado). As últimas semanas costumam estar incompletas por atraso de notificação.</p></div>
        <div class="legenda" id="leg-semana"></div></div>
      <div id="g-semana" class="grafico" style="height:300px"></div>
    </section>
    <div class="grade g2">
      <section class="card card-corpo"><h2 id="t-ano">Casos por ano de notificação</h2><div id="g-ano" class="grafico" style="height:240px"></div></section>
      <section class="card card-corpo"><h2 id="t-mes">Casos por mês de início dos sintomas</h2><div id="g-mes" class="grafico" style="height:240px"></div></section>
    </div>`);
  let d;
  try { d = await api(`/api/visao?${query()}`); } catch (e) { $("#kpis").innerHTML = erroHtml(e); return; }
  if (n !== estado.pedido) return;
  $("#kpis").innerHTML = htmlKpis(d.indicadores);
  const t = cap(termo());
  $("#t-semana").textContent = `${t} por semana epidemiológica`;
  $("#t-ano").textContent = `${t} por ano de notificação`;
  $("#t-mes").textContent = `${t} por mês de início dos sintomas`;

  const desenhar = () => {
    const anos = [...new Set(d.semana.map((r) => r.ano_epi))].sort();
    const ult = anos.at(-1), pen = anos.at(-2);
    const traces = anos.map((a) => {
      const pts = d.semana.filter((r) => r.ano_epi === a);
      const cor = a === ult ? css("--serie-1") : a === pen ? css("--serie-2") : css("--serie-ctx");
      return { x: pts.map((r) => r.sem_epi), y: pts.map((r) => r.casos), name: String(a), type: "scatter", mode: "lines",
               line: { color: cor, width: a === ult ? 2.6 : a === pen ? 2 : 1.3 },
               hovertemplate: `${a}: %{y:,.0f}<extra></extra>` };
    });
    $("#leg-semana").innerHTML = anos.map((a) => {
      const cor = a === ult ? "--serie-1" : a === pen ? "--serie-2" : "--serie-ctx";
      return `<span><i style="border-color:var(${cor})"></i>${a}</span>`;
    }).join("");
    plot($("#g-semana"), traces, layoutBase({
      hovermode: "x unified",
      xaxis: { ...layoutBase().xaxis, title: { text: "Semana epidemiológica", font: { size: 13 } }, range: [0.5, 53.5], dtick: 4, tick0: 4, showgrid: false },
      yaxis: { ...layoutBase().yaxis, title: { text: t, font: { size: 13 } } },
      margin: { l: 58, r: 12, t: 10, b: 46 },
    }));
    plot($("#g-ano"), [{
      x: d.ano.map((r) => String(r.ano)), y: d.ano.map((r) => r.casos), type: "bar",
      marker: { color: css("--serie-1"), cornerradius: 4 }, text: d.ano.map((r) => fmt(r.casos)), textposition: "outside",
      textfont: { color: css("--text") }, cliponaxis: false, hovertemplate: "%{x}: %{y:,.0f}<extra></extra>",
    }], layoutBase({ bargap: 0.28, xaxis: { ...layoutBase().xaxis, type: "category", showgrid: false }, margin: { l: 44, r: 8, t: 22, b: 30 } }));
    plot($("#g-mes"), [{
      x: d.mes.map((r) => r.mes), y: d.mes.map((r) => r.casos), type: "bar",
      marker: { color: css("--serie-1"), cornerradius: 2 }, hovertemplate: "%{x|%m/%Y}: %{y:,.0f}<extra></extra>",
    }], layoutBase({ bargap: 0.18, xaxis: { ...layoutBase().xaxis, tickformat: "%m/%Y", showgrid: false, dtick: "M12" }, margin: { l: 44, r: 8, t: 10, b: 30 } }));
  };
  desenhar();
  redesenhar = desenhar;
}

// ---------------------------------------------------------------- mapa
async function paginaMapa(raiz, n) {
  const f = estado.f;
  raiz.insertAdjacentHTML("beforeend", `
    <div id="kpis">${esqueleto(120)}</div>
    <div class="grade g-mapa">
      <section class="card card-corpo">
        <h2>${f.mun ? "Mapa do município" : "Mapa dos municípios"}</h2>
        <div class="segmentado peq" style="margin-top:12px" role="group" aria-label="Colorir por">
          <button data-medida="incidencia" aria-pressed="${(estado.medida || "incidencia") === "incidencia"}">Incidência</button>
          <button data-medida="casos" aria-pressed="${estado.medida === "casos"}">${cap(termo())}</button>
        </div>
        <div class="mapa-area" id="mapa-area">${esqueleto(470)}</div>
      </section>
      <section class="card lateral" id="lateral">${esqueleto(300)}</section>
    </div>
    <section class="card card-corpo" style="margin-bottom:14px">
      <div class="card-titulo"><h2>${f.mun ? "Município selecionado" : "Municípios"}</h2>
        <div class="acoes-tabela">
          <div class="busca">${ico("busca")}<input id="busca-mun" type="search" placeholder="Buscar município..." aria-label="Buscar município"></div>
          <button class="btn" id="exp-mun">${ico("baixar")}Exportar</button>
        </div></div>
      <div id="tab-mun">${esqueleto(200)}</div>
    </section>`);
  let d, geo;
  try {
    d = await api(`/api/mapa?${query()}`);
    geo = await api(`/api/geo?ufs=${d.area.join(",")}`);
  } catch (e) { $("#kpis").innerHTML = erroHtml(e); return; }
  if (n !== estado.pedido) return;
  $("#kpis").innerHTML = htmlKpis(d.indicadores);
  $$("[data-medida]").forEach((b) => b.onclick = () => {
    estado.medida = b.dataset.medida;
    $$("[data-medida]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    desenharMapa(d, geo);
  });
  $("#exp-mun").onclick = () => { window.location = `/api/exportar?${query({ formato: "municipios" })}`; };
  desenharMapa(d, geo);
  desenharLateral(d);
  tabelaMunicipios(d);
  redesenhar = () => desenharMapa(d, geo);
}

function interpolarCor(a, b, t) {
  const p = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const [x, y] = [p(a), p(b)];
  return "#" + x.map((v, i) => Math.round(v + (y[i] - v) * t).toString(16).padStart(2, "0")).join("");
}
function rampa(t) {
  t = Math.max(0, Math.min(1, t));
  return t < 0.5 ? interpolarCor(css("--rampa-0"), css("--rampa-1"), t * 2) : interpolarCor(css("--rampa-1"), css("--rampa-2"), (t - 0.5) * 2);
}

function desenharMapa(d, geo) {
  const area = $("#mapa-area");
  if (!area) return;
  const medida = estado.medida || "incidencia";
  const porCod = Object.fromEntries(d.municipios.map((m) => [m.cod6, m]));
  const feats = estado.f.mun ? geo.features.filter((g) => g.properties.cod6 === estado.f.mun) : geo.features;
  if (!feats.length) { area.innerHTML = `<div class="vazio">Mapa indisponível para esta área.</div>`; return; }

  // projeção equiretangular corrigida pela latitude média
  let minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
  const aneis = (g) => g.type === "Polygon" ? g.coordinates : g.coordinates.flat();
  feats.forEach((ft) => aneis(ft.geometry).forEach((anel) => anel.forEach(([x, y]) => {
    minX = Math.min(minX, x); maxX = Math.max(maxX, x); minY = Math.min(minY, y); maxY = Math.max(maxY, y);
  })));
  const k = Math.cos(((minY + maxY) / 2) * Math.PI / 180);
  const W = 1000, H = 1000 * (maxY - minY) / ((maxX - minX) * k || 1);
  const sx = (x) => ((x - minX) * k) / ((maxX - minX) * k) * W;
  const sy = (y) => (maxY - y) / (maxY - minY) * H;
  const valores = feats.map((ft) => porCod[ft.properties.cod6]?.[medida] ?? 0).filter((v) => v !== null);
  let vmin = Math.min(...valores), vmax = Math.max(...valores);
  if (vmax - vmin < 1e-9) { const pad = Math.max(Math.abs(vmax) * 0.02, 0.5); vmin -= pad; vmax += pad; }
  if (!estado.f.mun) vmin = Math.min(0, vmin);

  const caminhos = feats.map((ft) => {
    const cod = ft.properties.cod6, m = porCod[cod] || {};
    const dd = aneis(ft.geometry).map((anel) => "M" + anel.map(([x, y]) => `${sx(x).toFixed(1)},${sy(y).toFixed(1)}`).join("L") + "Z").join("");
    const v = m[medida];
    const cor = v === null || v === undefined ? css("--mapa-vazio") : rampa((v - vmin) / (vmax - vmin));
    return `<path class="mun ${estado.mapaSel === cod ? "sel" : ""}" d="${dd}" fill="${cor}" data-cod="${cod}"></path>`;
  }).join("");
  let rotulo = "";
  if (feats.length === 1) {
    const anel = aneis(feats[0].geometry).sort((a, b) => b.length - a.length)[0];
    const cx = anel.reduce((s, p) => s + sx(p[0]), 0) / anel.length, cy = anel.reduce((s, p) => s + sy(p[1]), 0) / anel.length;
    rotulo = `<text class="rot" x="${cx}" y="${cy}" text-anchor="middle" dominant-baseline="middle" style="font-size:${W / 28}px">${esc(porCod[feats[0].properties.cod6]?.municipio || "")}</text>`;
  }
  const pad = 70;
  const vb0 = { x: -pad, y: -pad, w: W + 2 * pad + 190, h: H + 2 * pad };
  const ticks = [0, .25, .5, .75, 1].map((t) => vmax - t * (vmax - vmin));
  const casas = medida === "incidencia" || vmax - vmin < 10 ? 1 : 0;
  area.innerHTML = `
    <svg class="mapa" viewBox="${vb0.x} ${vb0.y} ${vb0.w} ${vb0.h}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Mapa de ${medida === "incidencia" ? "incidência" : "casos"} por município">${caminhos}${rotulo}</svg>
    <div class="zoom"><button data-z="1.4" aria-label="Aproximar">${ico("mais")}</button><button data-z="0.7" aria-label="Afastar">${ico("menos")}</button><button data-z="tela" aria-label="Tela cheia">${ico("tela")}</button></div>
    <div class="escala"><div class="escala-tit">${medida === "incidencia" ? "Incidência<br>(por 100 mil hab./ano)" : cap(termo())}</div>
      <div class="escala-corpo"><div class="escala-barra" style="background:linear-gradient(${rampa(1)}, ${rampa(.5)}, ${rampa(0)})"></div>
      <div class="escala-ticks">${ticks.map((t) => `<span>${fmt(t, casas)}</span>`).join("")}</div></div></div>
    <div class="mapa-nota">${estado.f.mun ? "Recorte municipal selecionado" : `${feats.length} municípios · clique para ver detalhes`}</div>`;

  // interação: dica, seleção, zoom e arrasto
  const svg = $("svg.mapa", area), tip = $("#tooltip");
  let vb = { ...vb0 };
  const aplicar = () => svg.setAttribute("viewBox", `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
  const zoom = (fator, cx = vb.x + vb.w / 2, cy = vb.y + vb.h / 2) => {
    const nw = Math.min(vb0.w * 1.5, Math.max(vb0.w / 12, vb.w / fator));
    const nh = nw * vb.h / vb.w;
    vb = { x: cx - (cx - vb.x) * nw / vb.w, y: cy - (cy - vb.y) * nh / vb.h, w: nw, h: nh };
    aplicar();
  };
  $$("[data-z]", area).forEach((b) => b.onclick = () => {
    if (b.dataset.z === "tela") {
      if (document.fullscreenElement) document.exitFullscreen(); else area.requestFullscreen?.();
    } else zoom(+b.dataset.z);
  });
  svg.addEventListener("wheel", (e) => {
    e.preventDefault();
    const pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY;
    const p = pt.matrixTransform(svg.getScreenCTM().inverse());
    zoom(e.deltaY < 0 ? 1.2 : 1 / 1.2, p.x, p.y);
  }, { passive: false });
  let arrasto = null, moveu = false;
  svg.addEventListener("pointerdown", (e) => { arrasto = { x: e.clientX, y: e.clientY, vb: { ...vb } }; moveu = false; });
  window.addEventListener("pointerup", () => { arrasto = null; }, { once: false });
  svg.addEventListener("pointermove", (e) => {
    if (arrasto) {
      const esc_ = vb.w / svg.clientWidth;
      const dx = (e.clientX - arrasto.x), dy = (e.clientY - arrasto.y);
      if (Math.abs(dx) + Math.abs(dy) > 3) moveu = true;
      vb = { ...arrasto.vb, x: arrasto.vb.x - dx * esc_, y: arrasto.vb.y - dy * esc_ };
      aplicar();
      tip.style.display = "none";
      return;
    }
    const alvo = e.target.closest("path.mun");
    if (!alvo) { tip.style.display = "none"; return; }
    const m = porCod[alvo.dataset.cod] || {};
    tip.innerHTML = `<b>${esc(m.municipio || alvo.dataset.cod)}</b><br>${cap(termo())}: ${fmt(m.casos)}<br>Incidência: ${fmt(m.incidencia, 1)} /100 mil hab./ano`;
    tip.style.display = "block";
    tip.style.left = Math.min(window.innerWidth - tip.offsetWidth - 8, e.clientX + 14) + "px";
    tip.style.top = (e.clientY + 14) + "px";
  });
  svg.addEventListener("pointerleave", () => { tip.style.display = "none"; });
  svg.addEventListener("click", (e) => {
    const alvo = e.target.closest("path.mun");
    if (!alvo || moveu) return;
    estado.mapaSel = estado.mapaSel === alvo.dataset.cod ? null : alvo.dataset.cod;
    $$("path.mun", svg).forEach((p) => p.classList.toggle("sel", p.dataset.cod === estado.mapaSel));
    desenharLateral(d);
  });
}

function desenharLateral(d) {
  const el = $("#lateral");
  if (!el) return;
  const m = estado.meta, f = estado.f;
  const cod = f.mun || estado.mapaSel;
  let nome, uf, inc, casos, obitos, botao;
  if (cod) {
    const r = d.municipios.find((x) => x.cod6 === cod) || {};
    nome = r.municipio; uf = m.ufs_nome[r.uf] || r.uf; inc = r.incidencia; casos = r.casos; obitos = r.obitos;
    botao = f.mun ? "Ver perfil dos casos" : "Filtrar este município";
  } else {
    nome = areaNome(); uf = d.area.length === 1 ? "Todos os municípios" : d.area.join(", ");
    inc = d.indicadores.incidencia; casos = d.indicadores.casos; obitos = d.indicadores.obitos;
    botao = "Ver perfil dos casos";
  }
  el.innerHTML = `
    <h2>${esc(nome)}</h2><div class="uf">${esc(uf)}</div>
    <h3>Indicadores do período selecionado</h3>
    <div class="mini-kpis">
      <div><div class="r">Incidência</div><div class="v">${fmt(inc, 1)}</div><div class="s">por 100 mil hab./ano</div></div>
      <div><div class="r">${cap(termo())}</div><div class="v">${fmt(casos)}</div></div>
      <div><div class="r">Óbitos</div><div class="v">${fmt(obitos)}</div></div>
    </div>
    ${!f.mun && estado.mapaSel ? `<p class="card-sub" style="margin-top:14px">Clique de novo no município para voltar ao total da área.</p>` : ""}
    <div class="acao"><button class="btn btn-prim btn-grande" id="ver-perfil"><span class="rot">${ico("vars")}${botao}</span>${ico("direita")}</button></div>`;
  $("#ver-perfil").onclick = () => {
    if (cod && !f.mun) { mudarFiltro({ mun: cod }); return; }
    irPara("perfil");
  };
}

function tabelaMunicipios(d) {
  const el = $("#tab-mun");
  let ordem = { col: "casos", desc: true }, busca = "";
  const cols = [["municipio", "Município"], ["uf", "UF"], ["casos", cap(termo()), "num"],
                ["incidencia", "Incidência (por 100 mil hab./ano)", "num"], ["obitos", "Óbitos", "num"], ["populacao", "População média", "num"]];
  const desenhar = () => {
    const norm = (s) => String(s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    let linhas = d.municipios.filter((r) => !busca || norm(r.municipio).includes(norm(busca)));
    linhas = [...linhas].sort((a, b) => {
      const x = a[ordem.col] ?? -1, y = b[ordem.col] ?? -1;
      const c = typeof x === "string" ? x.localeCompare(y, "pt-BR") : x - y;
      return ordem.desc ? -c : c;
    });
    el.innerHTML = `<div class="tabela-wrap"><table><thead><tr>${cols.map(([c, r, cl]) =>
      `<th class="ord ${cl || ""}" data-col="${c}" aria-sort="${ordem.col === c ? (ordem.desc ? "descending" : "ascending") : "none"}">${r}${ordem.col === c ? (ordem.desc ? " ↓" : " ↑") : ""}</th>`).join("")}</tr></thead>
      <tbody>${linhas.map((r) => `<tr><td>${esc(r.municipio)}</td><td>${esc(r.uf)}</td><td class="num">${fmt(r.casos)}</td>
        <td class="num">${fmt(r.incidencia, 1)}</td><td class="num">${fmt(r.obitos)}</td><td class="num">${fmt(r.populacao)}</td></tr>`).join("")
        || `<tr><td colspan="6">Nenhum município encontrado.</td></tr>`}</tbody></table></div>`;
    $$("th.ord", el).forEach((th) => th.onclick = () => {
      ordem = { col: th.dataset.col, desc: ordem.col === th.dataset.col ? !ordem.desc : th.dataset.col !== "municipio" && th.dataset.col !== "uf" };
      desenhar();
    });
  };
  $("#busca-mun").oninput = (e) => { busca = e.target.value; desenhar(); };
  desenhar();
}

// ---------------------------------------------------------------- perfil
async function paginaPerfil(raiz, n) {
  const ag = agravoAtual();
  raiz.insertAdjacentHTML("beforeend", `
    <div id="kpis">${esqueleto(120)}</div>
    <div class="grade g2">
      <section class="card card-corpo"><div class="card-titulo"><h2>Pirâmide etária</h2>
        <div class="legenda"><span><span class="q" style="background:var(--serie-1)"></span>Masculino</span><span><span class="q" style="background:var(--serie-2)"></span>Feminino</span></div></div>
        <p class="card-sub">${cap(termo())} por faixa etária (anos) e sexo</p><div id="g-pir" style="height:380px"></div></section>
      <section class="card card-corpo"><h2>Raça/cor</h2><p class="card-sub">${cap(termo())}</p><div id="b-raca">${esqueleto(300)}</div></section>
    </div>
    <div class="grade g2">
      ${ag.todos_casos ? "" : `<section class="card card-corpo"><h2>Situação das notificações</h2><p class="card-sub">Todas as notificações, pela classificação final</p><div id="b-situacao">${esqueleto(200)}</div></section>`}
      <section class="card card-corpo"><h2>Classificação final</h2><p class="card-sub">${ag.todos_casos ? "Casos" : "Todas as notificações"}</p><div id="b-classificacao">${esqueleto(200)}</div></section>
      <section class="card card-corpo"><h2>Evolução</h2><p class="card-sub">${cap(termo())}</p><div id="b-evolucao">${esqueleto(200)}</div></section>
      <section class="card card-corpo"><h2>Critério de confirmação</h2><p class="card-sub">${cap(termo())}</p><div id="b-criterio">${esqueleto(200)}</div></section>
      <section class="card card-corpo"><h2>Hospitalização</h2><p class="card-sub">${cap(termo())}</p><div id="b-hospitalizado">${esqueleto(160)}</div></section>
    </div>`);
  let d;
  try { d = await api(`/api/perfil?${query()}`); } catch (e) { $("#kpis").innerHTML = erroHtml(e); return; }
  if (n !== estado.pedido) return;
  $("#kpis").innerHTML = htmlKpis(d.indicadores);
  for (const k of ["raca", "situacao", "classificacao", "evolucao", "criterio", "hospitalizado"]) {
    const el = $(`#b-${k}`);
    if (el) el.innerHTML = d[k].length ? barrasHtml(d[k]) : `<p class="card-sub">Sem informação.</p>`;
  }
  const desenhar = () => {
    const faixas = estado.meta.faixas;
    const val = (sexo) => faixas.map((fx) => (d.piramide.find((r) => r.sexo === sexo && r.faixa_etaria === fx) || {}).casos || 0);
    const mas = val("Masculino"), fem = val("Feminino");
    const max = Math.max(1, ...mas, ...fem);
    const passo = Math.pow(10, Math.floor(Math.log10(max)));
    const lim = Math.ceil(max / passo) * passo;
    const ticks = [-lim, -lim / 2, 0, lim / 2, lim];
    plot($("#g-pir"), [
      { y: faixas, x: mas.map((v) => -v), customdata: mas, name: "Masculino", type: "bar", orientation: "h",
        marker: { color: css("--serie-1"), cornerradius: 3 }, hovertemplate: "Masculino, %{y}: %{customdata:,.0f}<extra></extra>" },
      { y: faixas, x: fem, customdata: fem, name: "Feminino", type: "bar", orientation: "h",
        marker: { color: css("--serie-2"), cornerradius: 3 }, hovertemplate: "Feminino, %{y}: %{customdata:,.0f}<extra></extra>" },
    ], layoutBase({ barmode: "relative", bargap: 0.14, margin: { l: 56, r: 12, t: 6, b: 30 },
      xaxis: { ...layoutBase().xaxis, tickvals: ticks, ticktext: ticks.map((t) => fmt(Math.abs(t))), range: [-lim * 1.05, lim * 1.05] },
      yaxis: { ...layoutBase().yaxis, showgrid: false, rangemode: undefined } }));
  };
  desenhar();
  redesenhar = desenhar;
}

// ---------------------------------------------------------------- outras variáveis
async function paginaVariaveis(raiz, n) {
  raiz.insertAdjacentHTML("beforeend", `
    <div class="grade g-vars">
      <section class="card card-corpo"><h2>Variáveis da ficha</h2>
        <p class="card-sub">Rótulos oficiais do TabNet/DATASUS</p>
        <div class="busca" style="margin-top:10px">${ico("busca")}<input id="busca-var" type="search" placeholder="Buscar variável..." style="width:100%" aria-label="Buscar variável"></div>
        <div class="lista-vars" id="lista-vars">${esqueleto(400)}</div></section>
      <section class="card card-corpo"><div class="card-titulo"><div><h2 id="var-titulo">Variável</h2><p class="card-sub" id="var-sub"></p></div></div>
        <div id="var-corpo">${esqueleto(360)}</div></section>
    </div>`);
  let lista;
  try { lista = await api(`/api/variaveis?agravo=${estado.f.agravo}`); } catch (e) { $("#var-corpo").innerHTML = erroHtml(e); return; }
  if (n !== estado.pedido) return;
  if (!lista.length) { $("#lista-vars").innerHTML = `<p class="card-sub" style="padding:12px">Não há tabela de rótulos para este agravo.</p>`; $("#var-corpo").innerHTML = ""; return; }
  if (!lista.some((v) => v.id === estado.varId)) estado.varId = lista[0].id;
  const desenharLista = (filtro = "") => {
    const norm = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    $("#lista-vars").innerHTML = lista.filter((v) => !filtro || norm(v.rotulo + v.campo).includes(norm(filtro))).map((v) =>
      `<button data-var="${v.id}" class="${v.id === estado.varId ? "ativo" : ""}">${esc(v.rotulo)}<small>${v.campo}</small></button>`).join("");
    $$("[data-var]").forEach((b) => b.onclick = () => { estado.varId = +b.dataset.var; desenharLista($("#busca-var").value); carregar(); });
  };
  const carregar = async () => {
    $("#var-corpo").innerHTML = esqueleto(360);
    const minhaVez = ++estado.pedidoVar;
    try {
      const d = await api(`/api/variavel?${query({ id: estado.varId })}`);
      if (minhaVez !== estado.pedidoVar) return;
      const total = d.valores.reduce((s, r) => s + r.casos, 0);
      $("#var-titulo").textContent = d.rotulo;
      $("#var-sub").textContent = `Campo ${d.campo} · ${fmt(total)} ${termo()}`;
      $("#var-corpo").innerHTML = barrasHtml(d.valores, total);
    } catch (e) { $("#var-corpo").innerHTML = erroHtml(e); }
  };
  estado.pedidoVar = 0;
  $("#busca-var").oninput = (e) => desenharLista(e.target.value);
  desenharLista();
  carregar();
}

// ---------------------------------------------------------------- dados
async function paginaDados(raiz, n) {
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
  $$("[data-exportar]", raiz).forEach((b) => b.onclick = () => { window.location = `/api/exportar?${query({ formato: b.dataset.exportar })}`; });
  const colunas = [["data_notificacao", "Notificação"], ["data_sintomas", "Início sintomas"], ["sem_epi", "Sem. epi."], ["mun_res", "Município de residência"],
                   ["mun_not", "Município de notificação"], ["idade", "Idade"], ["sexo", "Sexo"], ["raca", "Raça/cor"], ["classificacao", "Classificação"],
                   ["criterio_confirmacao", "Critério"], ["evolucao_caso", "Evolução"], ["hospitalizado", "Hospitalizado"]];
  const carregar = async (pagina) => {
    let d;
    try { d = await api(`/api/registros?${query({ pagina })}`); } catch (e) { $("#regs").innerHTML = erroHtml(e); return; }
    if (n !== estado.pedido) return;
    const ini = d.pagina * d.por_pagina;
    const paginas = Math.max(1, Math.ceil(d.total / d.por_pagina));
    $("#regs-sub").textContent = `${fmt(d.total)} ${termo()} · mais recentes primeiro`;
    const fmtCel = (c, v) => {
      if (v === null || v === undefined) return "";
      if (c.startsWith("data_")) return new Date(v + "T12:00").toLocaleDateString("pt-BR");
      if (c === "idade") return v < 1 ? "< 1" : fmt(Math.floor(v));
      return esc(v);
    };
    $("#regs").innerHTML = `<div class="tabela-wrap"><table><thead><tr>${colunas.map(([, r]) => `<th>${r}</th>`).join("")}</tr></thead>
      <tbody>${d.linhas.map((l) => `<tr>${colunas.map(([c]) => `<td class="${c === "idade" || c === "sem_epi" ? "num" : ""}">${fmtCel(c, l[c])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>
      <div class="paginacao"><span>${fmt(ini + 1)}–${fmt(Math.min(ini + d.por_pagina, d.total))} de ${fmt(d.total)}</span>
        <div class="btns"><button class="btn" id="pag-ant" ${d.pagina === 0 ? "disabled" : ""}>Anterior</button>
        <span style="align-self:center">Página ${d.pagina + 1} de ${paginas}</span>
        <button class="btn" id="pag-prox" ${d.pagina + 1 >= paginas ? "disabled" : ""}>Próxima</button></div></div>`;
    $("#pag-ant").onclick = () => carregar(d.pagina - 1);
    $("#pag-prox").onclick = () => carregar(d.pagina + 1);
  };
  carregar(0);
}

// ---------------------------------------------------------------- atualizar dados
let timerStatus = null;
async function paginaAtualizar(raiz) {
  raiz.insertAdjacentHTML("beforeend", `<div id="atu">${esqueleto(400)}</div>`);
  let d;
  try { d = await api("/api/dados"); } catch (e) { $("#atu").innerHTML = erroHtml(e); return; }
  const sel = { ufs: new Set(d.config.ufs), agravos: new Set(d.config.agravos), anos: new Set(d.config.anos) };
  const desenhar = () => {
    const anosDisp = [...new Set(d.catalogo.filter((c) => !sel.agravos.size || sel.agravos.has(c.codigo)).flatMap((c) => c.anos))].sort((a, b) => b - a);
    const anos = anosDisp.length ? anosDisp : Array.from({ length: 27 }, (_, i) => new Date().getFullYear() - i);
    const tamanho = d.catalogo.filter((c) => sel.agravos.has(c.codigo))
      .reduce((s, c) => s + [...sel.anos].reduce((t, a) => t + (c.tamanhos[a] || 0), 0), 0);
    const pronto = sel.ufs.size && sel.agravos.size && sel.anos.size;
    $("#atu").innerHTML = `
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
      <section class="card card-corpo" style="margin-bottom:14px">
        <div class="card-titulo"><div><h2>Dados no computador</h2><p class="card-sub">${d.inventario.length} arquivo(s)</p></div>
          <button class="btn" id="remover" disabled>Remover selecionados</button></div>
        ${d.inventario.length ? `<div class="tabela-wrap"><table><thead><tr><th></th><th>Agravo</th><th class="num">Ano</th><th>Dado</th><th class="num">Registros</th><th>UFs</th><th>No DATASUS</th><th>Baixado em</th></tr></thead>
          <tbody>${d.inventario.map((v) => `<tr><td><input type="checkbox" data-rem="${v.agravo}_${v.ano}" aria-label="Selecionar ${esc(v.nome)} ${v.ano}"></td><td>${esc(v.nome)}</td><td class="num">${v.ano}</td>
            <td>${v.situacao === "preliminar" ? "Preliminar" : "Final"}</td><td class="num">${fmt(v.registros)}</td><td>${esc(v.ufs.join(", "))}</td>
            <td>${{ em_dia: '<span class="status ok">Em dia</span>', nova: '<span class="status nova">Há versão nova</span>' }[v.status] || '<span class="status neutro">Não verificado</span>'}</td>
            <td>${new Date(v.processado_em).toLocaleString("pt-BR")}</td></tr>`).join("")}</tbody></table></div>`
          : `<div class="vazio">${ico("nuvem")}<h2>Nenhum dado ainda</h2><p>Escolha acima o que baixar.</p></div>`}
      </section>`;
    ligar();
    mostrarJob(d.job);
  };
  const alternar = (set, v) => set.has(v) ? set.delete(v) : set.add(v);
  const ligar = () => {
    $$("[data-s-uf]").forEach((b) => b.onclick = () => { alternar(sel.ufs, b.dataset.sUf); desenhar(); });
    $$("[data-s-ano]").forEach((b) => b.onclick = () => { alternar(sel.anos, +b.dataset.sAno); desenhar(); });
    $$("[data-s-ag]").forEach((c) => c.onchange = () => { alternar(sel.agravos, c.dataset.sAg); const b = $("#busca-ag").value; desenhar(); $("#busca-ag").value = b; filtrarAg(b); });
    $("#busca-ag").oninput = (e) => filtrarAg(e.target.value);
    $("#consultar").onclick = async (e) => {
      e.target.disabled = true; e.target.lastChild.textContent = "Consultando...";
      try { d = await api("/api/dados/listar", { method: "POST" }); desenhar(); }
      catch (err) { $("#job").innerHTML = erroHtml(err); e.target.disabled = false; e.target.lastChild.textContent = "Consultar DATASUS"; }
    };
    $("#iniciar").onclick = async () => {
      try {
        const job = await api("/api/dados/atualizar", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ufs: [...sel.ufs], agravos: [...sel.agravos], anos: [...sel.anos], forcar: $("#forcar").checked }) });
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
      d = await api("/api/dados/remover", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ itens }) });
      await recarregarMeta();
      desenhar();
    };
  };
  const filtrarAg = (t) => {
    const norm = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    $$("#lista-ag label").forEach((l) => { l.style.display = !t || norm(l.textContent).includes(norm(t)) ? "" : "none"; });
  };
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
        const res = job.resultado; d.job = job;
        desenhar();
        if (res) mostrarJob(job);
      }
    }, 1000);
  };
  desenhar();
  if (d.job.rodando) acompanhar();
}

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

// ---------------------------------------------------------------- sobre
function paginaSobre(raiz) {
  raiz.insertAdjacentHTML("beforeend", `
  <section class="card card-corpo texto" style="margin-bottom:14px;max-width:none">
    <h2>Fonte</h2>
    <p>Sistema de Informação de Agravos de Notificação (SINAN): microdados públicos e anonimizados do DATASUS/Ministério da Saúde
      (<code>ftp.datasus.gov.br/dissemin/publicos/SINAN</code>). População: IBGE (estimativas anuais e Censo 2022).
      Rótulos das variáveis: arquivos oficiais do tabulador TabNet. Mapa: malha municipal do IBGE.</p>
    <h2 style="margin-top:22px">Como os números são calculados</h2>
    <dl>
      <dt>Ano</dt><dd>Ano da notificação (igual ao arquivo do DATASUS e ao padrão do TabNet).</dd>
      <dt>Semana epidemiológica</dt><dd>Semana (domingo a sábado) do início dos sintomas; sem essa data, usa o diagnóstico ou a notificação. A semana 1 é a primeira com ao menos 4 dias no ano.</dd>
      <dt>Confirmado</dt><dd>Classificação final do caso. Dengue: dengue, com sinais de alarme e grave (e as classificações antigas antes de 2014). Chikungunya: código 13. Demais: rótulo “confirmado” da ficha. Em tuberculose, hanseníase, violência e acidentes de trabalho, toda notificação é um caso.</dd>
      <dt>Provável</dt><dd>Todas as notificações exceto as descartadas, medida usada nos boletins de arboviroses.</dd>
      <dt>Óbito</dt><dd>Evolução “óbito pelo agravo” (não conta óbito por outras causas nem em investigação).</dd>
      <dt>Letalidade</dt><dd>Óbitos pelo agravo ÷ casos confirmados × 100.</dd>
      <dt>Incidência</dt><dd>Casos ÷ população × 100 mil. Com vários anos, é a média anual (casos ÷ soma da população de cada ano).</dd>
      <dt>Residência × notificação</dt><dd>Por padrão os casos são contados no município onde a pessoa mora.</dd>
    </dl>
    <h2 style="margin-top:22px">Cuidados na interpretação</h2>
    <ul>
      <li>Os anos mais recentes são <b>preliminares</b> e mudam a cada atualização do DATASUS.</li>
      <li>As últimas semanas sempre parecem menores por causa do atraso entre o início dos sintomas e o registro.</li>
      <li>Municípios pequenos têm incidências instáveis: poucos casos mudam muito a taxa.</li>
      <li>Os arquivos de dengue do DATASUS não trazem os casos descartados.</li>
      <li>Na Amazônia Legal, a malária é notificada no SIVEP-Malária, não no SINAN.</li>
      <li>Para conferir números, compare com o TabNet: <a href="http://tabnet.datasus.gov.br" target="_blank" rel="noopener">tabnet.datasus.gov.br</a>.</li>
    </ul>
  </section>`);
}

// ================================================================ render
let redesenhar = null;
async function render() {
  const id = paginaAtual();
  const n = ++estado.pedido;
  redesenhar = null;
  graficos.forEach((g) => { try { Plotly.purge(g); } catch (e) { /* ok */ } });
  graficos.length = 0;
  montarMenu();
  $("#sidebar").classList.remove("aberta");
  document.title = `${PAGINAS[id].menu} · ${nomeMarca()}`;
  const raiz = $("#pagina");
  const p = PAGINAS[id];
  const temDados = estado.meta.agravos.length > 0;

  if (p.filtros && !temDados) {
    raiz.innerHTML = htmlCabecalho(id, false) + `<section class="card vazio">${ico("nuvem")}<h2>Ainda não há dados no computador</h2>
      <p>Baixe os dados do SINAN uma vez (precisa de internet). Depois o painel funciona offline.</p>
      <button class="btn btn-prim" onclick="location.hash='#/atualizar'">${ico("atualizar")}Ir para Atualizar dados</button></section>`;
    return;
  }
  const comExport = p.filtros;
  raiz.innerHTML = htmlCabecalho(id, comExport) + (p.filtros ? htmlFiltros() + htmlAlertas() : "");
  if (p.filtros) { ligarFiltros(raiz); ligarAlertas(raiz); }
  ligarExportar(raiz);
  const conteudo = document.createElement("div");
  raiz.appendChild(conteudo);
  const paginas = { "visao-geral": paginaVisao, "mapa": paginaMapa, "perfil": paginaPerfil, "variaveis": paginaVariaveis,
                    "dados": paginaDados, "atualizar": paginaAtualizar, "sobre": paginaSobre };
  await paginas[id](conteudo, n);
  if (n !== estado.pedido) return;
  raiz.insertAdjacentHTML("beforeend", htmlRodape(id === "mapa"
    ? "<b>Incidência</b> = casos ÷ soma da população dos anos selecionados × 100 mil (população estimada pelo IBGE; anos sem estimativa são interpolados)." : ""));
}

async function recarregarMeta() {
  estado.meta = await api("/api/meta");
  $("#brand-nome").textContent = nomeMarca();
  normalizarFiltros();
}

async function iniciar() {
  aplicarTema(document.documentElement.dataset.theme || "light");
  $$(".tema button").forEach((b) => b.onclick = () => aplicarTema(b.dataset.tema));
  $("#menu-abrir").onclick = () => $("#sidebar").classList.add("aberta");
  $("#menu-fechar").onclick = () => $("#sidebar").classList.remove("aberta");
  $("#sidebar-fundo").onclick = () => $("#sidebar").classList.remove("aberta");
  window.addEventListener("hashchange", () => { estado.mapaSel = null; render(); });
  window.addEventListener("tema", () => { if (redesenhar) redesenhar(); });
  try {
    await recarregarMeta();
  } catch (e) {
    $("#pagina").innerHTML = erroHtml("Não foi possível falar com o servidor do dashboard. Feche e abra de novo o ABRIR_DASHBOARD.bat.");
    return;
  }
  render();
}

// qualquer erro inesperado aparece na tela em vez de deixar a página em branco
function mostrarErroGlobal(e) {
  const el = $("#pagina");
  if (el) el.insertAdjacentHTML("afterbegin", erroHtml(`Erro na interface: ${e?.message || e}`));
}
window.addEventListener("error", (ev) => mostrarErroGlobal(ev.error || ev.message));
window.addEventListener("unhandledrejection", (ev) => mostrarErroGlobal(ev.reason));

iniciar();
