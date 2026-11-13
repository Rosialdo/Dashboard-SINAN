/* Ícones SVG (traço simples, herdam a cor do texto). */

const ICONES = {
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

/** ico("mapa") -> <svg>...</svg>. ``extra`` são atributos a mais no <svg>. */
export const ico = (nome, extra = "") => `<svg viewBox="0 0 24 24" ${extra}>${ICONES[nome]}</svg>`;
