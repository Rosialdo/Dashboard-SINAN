/* Tela "Qualidade dos dados": notificação, digitação, investigação e encerramento no prazo. */

import { erroHtml, esqueleto } from "../componentes/blocos.js";
import { kpi } from "../componentes/kpis.js";
import { api } from "../nucleo/api.js";
import { estado } from "../nucleo/estado.js";
import { query } from "../nucleo/filtros.js";
import { $, dataBR, fmt } from "../nucleo/util.js";

const QUADROS = {
  notificacao: ["Notificação no prazo", "Casos avisados até 7 dias depois dos primeiros sintomas.", "meta: até 7 dias"],
  digitacao: ["Digitação no prazo", "Fichas lançadas no sistema até 7 dias depois da notificação.", "meta: até 7 dias"],
  investigacao: ["Investigação no prazo", "Casos investigados até 2 dias depois da notificação. Esse prazo vale para as doenças de notificação imediata; nas demais é só uma referência provisória, ainda não validada pela vigilância.", "referência provisória: até 2 dias"],
  encerramento: ["Encerramento no prazo", "Casos com data de encerramento até 60 dias depois da notificação. Fichas sem data de encerramento registrada há mais de 60 dias contam como fora do prazo.", "meta: até 60 dias"],
};

function quadro(p) {
  const [rotulo, ajuda, pilula] = QUADROS[p.id];
  if (!p.disponivel) return kpi(rotulo, "–", ajuda, "esta doença não tem essa data nos arquivos do DATASUS", pilula);
  if (!p.base) return kpi(rotulo, "–", ajuda, "nenhuma ficha avaliável", pilula);
  let sub = `${fmt(p.no_prazo)} de ${fmt(p.base)} fichas avaliáveis`;
  if (p.id === "encerramento" && p.sem_encerramento > 0)
    sub += ` · ${fmt(p.sem_encerramento)} sem data de encerramento registrada há mais de 60 dias`;
  return kpi(rotulo, `${fmt(p.pct, 1)}%`, ajuda, sub, pilula);
}

export async function montar(raiz, pedido) {
  raiz.insertAdjacentHTML("beforeend", `<div id="kpis">${esqueleto(120)}</div>`);
  let d;
  try { d = await api(`/api/qualidade?${query()}`); } catch (e) { $("#kpis").innerHTML = erroHtml(e); return; }
  if (pedido !== estado.pedido) return;
  $("#kpis").innerHTML = `
    <p class="card-sub">${fmt(d.notificacoes)} notificações no total no período e área.</p>
    <section class="kpis quatro">${d.prazos.map(quadro).join("")}</section>
    <p class="card-sub">Considera notificações confirmadas, prováveis e descartadas. O percentual é calculado sobre as fichas que possuem as datas necessárias preenchidas e válidas. Fichas com datas ausentes, inválidas ou inconsistentes ficam fora da base de cálculo, exceto no encerramento: nele, as fichas sem data de encerramento registrada há mais de 60 dias contam como fora do prazo.</p>
    ${d.referencia ? `<p class="card-sub">Casos sem data de encerramento avaliados considerando os dados disponíveis até ${dataBR(d.referencia)}.</p>` : ""}`;
}
