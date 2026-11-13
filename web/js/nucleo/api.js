/* Conversa com o servidor local (pasta sinan/api no Python). */

/** GET (ou outro método via ``opcoes``). Erros viram exceção com a mensagem do servidor. */
export async function api(caminho, opcoes) {
  const r = await fetch(caminho, opcoes);
  const dados = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(dados.erro || `Erro ${r.status}`);
  return dados;
}

/** POST com corpo JSON (o servidor só aceita POST em JSON, por segurança). */
export const postJSON = (caminho, corpo = {}) => api(caminho, {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo),
});

/** Leva o navegador a baixar um arquivo da API (Excel/CSV). */
export function baixar(caminho) { window.location = caminho; }
