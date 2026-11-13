/* Tela "Mapa e municípios": mapa colorido, painel lateral e tabela dos municípios. */

import { erroHtml, esqueleto } from "../componentes/blocos.js";
import { esconderDica, mostrarDica } from "../componentes/dica.js";
import { definirRedesenho } from "../componentes/graficos.js";
import { mostrarKpis } from "../componentes/kpis.js";
import { api, baixar } from "../nucleo/api.js";
import { estado } from "../nucleo/estado.js";
import { areaNome, mudarFiltro, query, termo } from "../nucleo/filtros.js";
import { ico } from "../nucleo/icones.js";
import { irPara } from "../nucleo/navegacao.js";
import { $, $$, cap, css, esc, fmt, norm } from "../nucleo/util.js";

export async function montar(raiz, pedido) {
  const f = estado.f;
  raiz.insertAdjacentHTML("beforeend", `
    <div id="kpis">${esqueleto(120)}</div>
    <div class="grade g-mapa">
      <section class="card card-corpo">
        <h2>${f.mun ? "Mapa do município" : "Mapa dos municípios"}</h2>
        <div class="segmentado peq" style="margin-top:12px" role="group" aria-label="Colorir por">
          <button data-medida="incidencia" aria-pressed="${estado.medida === "incidencia"}">Incidência</button>
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
  if (pedido !== estado.pedido) return;
  mostrarKpis(d.indicadores);
  $$("[data-medida]").forEach((b) => b.onclick = () => {
    estado.medida = b.dataset.medida;
    $$("[data-medida]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    desenharMapa(d, geo);
  });
  $("#exp-mun").onclick = () => baixar(`/api/exportar?${query({ formato: "municipios" })}`);
  desenharMapa(d, geo);
  desenharLateral(d);
  tabelaMunicipios(d);
  definirRedesenho(() => desenharMapa(d, geo));
}

// ---------------------------------------------------------------- cores
function interpolarCor(a, b, t) {
  const p = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const [x, y] = [p(a), p(b)];
  return "#" + x.map((v, i) => Math.round(v + (y[i] - v) * t).toString(16).padStart(2, "0")).join("");
}

/** Cor da escala para t entre 0 (menor valor) e 1 (maior). */
function rampa(t) {
  t = Math.max(0, Math.min(1, t));
  return t < 0.5 ? interpolarCor(css("--rampa-0"), css("--rampa-1"), t * 2) : interpolarCor(css("--rampa-1"), css("--rampa-2"), (t - 0.5) * 2);
}

// ---------------------------------------------------------------- mapa (SVG)
function desenharMapa(d, geo) {
  const area = $("#mapa-area");
  if (!area) return;
  const medida = estado.medida;
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
  ligarInteracao(area, vb0, porCod, d);
}

/** Dica ao passar o mouse, seleção ao clicar, zoom (botões e roda) e arrasto. */
function ligarInteracao(area, vb0, porCod, d) {
  const svg = $("svg.mapa", area);
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
  window.addEventListener("pointerup", () => { arrasto = null; });
  svg.addEventListener("pointermove", (e) => {
    if (arrasto) {
      const escala = vb.w / svg.clientWidth;
      const dx = (e.clientX - arrasto.x), dy = (e.clientY - arrasto.y);
      if (Math.abs(dx) + Math.abs(dy) > 3) moveu = true;
      vb = { ...arrasto.vb, x: arrasto.vb.x - dx * escala, y: arrasto.vb.y - dy * escala };
      aplicar();
      esconderDica();
      return;
    }
    const alvo = e.target.closest("path.mun");
    if (!alvo) { esconderDica(); return; }
    const m = porCod[alvo.dataset.cod] || {};
    mostrarDica(`<b>${esc(m.municipio || alvo.dataset.cod)}</b><br>${cap(termo())}: ${fmt(m.casos)}<br>Incidência: ${fmt(m.incidencia, 1)} /100 mil hab./ano`,
                e.clientX + 14, e.clientY + 14);
  });
  svg.addEventListener("pointerleave", esconderDica);
  svg.addEventListener("click", (e) => {
    const alvo = e.target.closest("path.mun");
    if (!alvo || moveu) return;
    estado.mapaSel = estado.mapaSel === alvo.dataset.cod ? null : alvo.dataset.cod;
    $$("path.mun", svg).forEach((p) => p.classList.toggle("sel", p.dataset.cod === estado.mapaSel));
    desenharLateral(d);
  });
}

// ---------------------------------------------------------------- painel lateral
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

// ---------------------------------------------------------------- tabela
function tabelaMunicipios(d) {
  const el = $("#tab-mun");
  let ordem = { col: "casos", desc: true }, busca = "";
  const cols = [["municipio", "Município"], ["uf", "UF"], ["casos", cap(termo()), "num"],
                ["incidencia", "Incidência (por 100 mil hab./ano)", "num"], ["obitos", "Óbitos", "num"], ["populacao", "População média", "num"]];
  const desenhar = () => {
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
      const col = th.dataset.col;
      ordem = { col, desc: ordem.col === col ? !ordem.desc : col !== "municipio" && col !== "uf" };
      desenhar();
    });
  };
  $("#busca-mun").oninput = (e) => { busca = e.target.value; desenhar(); };
  desenhar();
}
