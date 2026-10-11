// Placar ao vivo: consulta o placar público da ESPN direto do navegador (endereço não oficial) e
// mescla o resultado nos jogos do nosso JSON. Se a ESPN falhar, o site segue só com os dados do dia.
const PROXY = import.meta.env.VITE_PLACAR_PROXY; // opcional: veja cloudflare/placar-worker.js

export const urlPlacar = (esporte) =>
  PROXY
    ? `${PROXY}?esporte=${encodeURIComponent(esporte)}`
    : `https://site.api.espn.com/apis/site/v2/sports/${esporte}/scoreboard`;

// JSON da ESPN -> { id: { estado: 'pre'|'in'|'post', pontosCasa, pontosFora, detalhe, inicio } }
export function interpretar(json) {
  const mapa = {};
  for (const ev of json.events ?? []) {
    const comp = ev.competitions?.[0];
    const lados = Object.fromEntries((comp?.competitors ?? []).map((c) => [c.homeAway, c]));
    if (!lados.home || !lados.away) continue;
    const n = (c) => (c.score === undefined || c.score === '' ? null : Number(c.score));
    mapa[String(ev.id)] = {
      estado: ev.status?.type?.state,
      pontosCasa: n(lados.home),
      pontosFora: n(lados.away),
      detalhe: ev.status?.type?.shortDetail ?? '',
      inicio: ev.date ? Date.parse(ev.date) : null,
    };
  }
  return mapa;
}

// Aplica o placar ao vivo a um jogo nosso. Em andamento: mostra o placar e marca "ao vivo".
// Terminado: mostra o placar final e já diz se o palpite acertou (a probabilidade já está no JSON).
export function aplicarAoVivo(g, ev) {
  if (!ev || ev.estado === 'pre' || ev.pontosCasa == null || ev.pontosFora == null) return g;
  const placar = [ev.pontosFora, ev.pontosCasa]; // [visitante, mandante], como no JSON
  if (ev.estado === 'in') return { ...g, placar, aoVivo: true, detalhe: ev.detalhe };
  let ok = g.ok;
  if (g.p != null && placar[0] !== placar[1]) ok = g.p >= 0.5 === placar[1] > placar[0];
  return { ...g, placar, ok, final: true };
}

// Chave do jogo na ESPN: NFL tem o campo "espn"; na NBA o próprio id já é da ESPN.
export const chaveEspn = (g) => String(g.espn ?? g.id);
