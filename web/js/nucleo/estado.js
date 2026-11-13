/* Estado compartilhado da interface e ganchos para redesenhar a tela.

Os ganchos evitam importação circular: o roteador registra a função que monta
a tela, e quem muda um filtro só chama renderizar().
*/

/** Telas do menu. ``filtros: true`` mostra a barra de filtros no topo. */
export const PAGINAS = {
  "visao-geral": { titulo: "Evolução epidemiológica", menu: "Visão geral", icone: "visao", secao: "ANÁLISE", filtros: true },
  "mapa": { titulo: "Distribuição territorial", menu: "Mapa e municípios", icone: "mapa", secao: "ANÁLISE", filtros: true },
  "perfil": { titulo: "Perfil dos casos", menu: "Perfil dos casos", icone: "perfil", secao: "ANÁLISE", filtros: true },
  "variaveis": { titulo: "Outras variáveis", menu: "Outras variáveis", icone: "vars", secao: "ANÁLISE", filtros: true },
  "dados": { titulo: "Dados e exportação", menu: "Dados e exportação", icone: "baixar", secao: "ANÁLISE", filtros: true },
  "atualizar": { titulo: "Atualizar dados", menu: "Atualizar dados", icone: "atualizar", secao: "GESTÃO" },
  "sobre": { titulo: "Sobre os dados", menu: "Sobre os dados", icone: "sobre", secao: "GESTÃO" },
};

/** Preferências guardadas no navegador (filtros, tema). Funciona mesmo sem localStorage. */
export const guardar = {
  ler(k, padrao) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : padrao; } catch (e) { return padrao; } },
  gravar(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* sem armazenamento */ } },
};

export const estado = {
  meta: null,             // resposta de /api/meta (agravos, anos, UFs, municípios)
  f: Object.assign({ agravo: "", ini: null, fim: null, mun: "", local: "res", contagem: "confirmados",
                     sexo: [], faixa: [], ufs: [] }, guardar.ler("filtros", {})),
  dispensados: new Set(), // avisos que o usuário fechou
  pedido: 0,              // aumenta a cada troca de tela: respostas antigas são ignoradas
  varId: null,            // variável aberta na tela "Outras variáveis"
  varAgravo: null,
  mapaSel: null,          // município clicado no mapa
  medida: "incidencia",   // cor do mapa: incidência ou casos
};

// ---------------------------------------------------------------- ganchos
let _render = () => {};
/** O roteador registra aqui a função que monta a tela atual. */
export function definirRender(fn) { _render = fn; }
/** Remonta a tela atual (depois de mudar filtros, por exemplo). */
export function renderizar() { return _render(); }
