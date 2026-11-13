/* Lógica dos filtros: valores válidos, URL da API e textos que dependem deles. */

import { estado, guardar, renderizar } from "./estado.js";

/** Agravo escolhido (objeto de /api/meta). */
export function agravoAtual() { return estado.meta.agravos.find((a) => a.codigo === estado.f.agravo); }

/** Corrige filtros que não fazem sentido (ano sem dados, município de outra UF...). */
export function normalizarFiltros() {
  const m = estado.meta, f = estado.f;
  if (!m.agravos.length) return;
  if (!agravoAtual()) f.agravo = (m.agravos.find((a) => a.codigo === "DENG") || m.agravos[0]).codigo;
  const ag = agravoAtual();
  const anos = ag.anos;
  if (!anos.includes(f.ini)) f.ini = anos[0];
  if (!anos.includes(f.fim)) f.fim = anos[anos.length - 1];
  if (f.ini > f.fim) [f.ini, f.fim] = [f.fim, f.ini];
  if (f.mun && !m.municipios.some((x) => x.cod6 === f.mun)) f.mun = "";
  f.ufs = f.ufs.filter((u) => m.ufs.includes(u));
  if (ag.todos_casos) f.contagem = "todas";
  else if (f.contagem === "provaveis" && !ag.provaveis) f.contagem = "confirmados";
  else if (f.contagem === "todas" && !ag.todos_casos && !f._todasEscolhida) f.contagem = "confirmados";
  guardar.gravar("filtros", f);
}

/** Parâmetros da URL da API com os filtros atuais (mais ``extra``). */
export function query(extra = {}) {
  const f = estado.f;
  const p = new URLSearchParams({ agravo: f.agravo, ini: f.ini, fim: f.fim, local: f.local, contagem: f.contagem,
                                  mun: f.mun, sexo: f.sexo.join(","), faixa: f.faixa.join(","), ufs: f.ufs.join(","), ...extra });
  return p.toString();
}

/** Muda filtros e remonta a tela. */
export function mudarFiltro(mudancas) {
  Object.assign(estado.f, mudancas);
  if ("contagem" in mudancas) estado.f._todasEscolhida = mudancas.contagem === "todas";
  normalizarFiltros();
  estado.mapaSel = null;
  renderizar();
}

/** "Roraima", "Boa Vista (RR)", "RR, AM"... */
export function areaNome() {
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

export function periodoTexto() {
  const f = estado.f;
  return f.ini === f.fim ? `${f.ini}` : `${f.ini} a ${f.fim}`;
}

/** O que está sendo contado: "casos confirmados", "casos prováveis", "notificações". */
export function termo() {
  if (agravoAtual().todos_casos) return "casos";
  return { confirmados: "casos confirmados", provaveis: "casos prováveis", todas: "notificações" }[estado.f.contagem];
}
