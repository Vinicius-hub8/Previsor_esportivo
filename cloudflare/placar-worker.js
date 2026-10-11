// OPCIONAL. Só use se o navegador bloquear a consulta direta à ESPN (erro de CORS).
// Cloudflare Workers (plano gratuito): cria um endereço seu que repassa o placar da ESPN, com cache de 30 s.
//
// Como usar:
//   1) dash.cloudflare.com > Workers & Pages > Create > Worker > cole este código > Deploy.
//   2) Copie o endereço do Worker (ex.: https://placar.seunome.workers.dev).
//   3) Na pasta web, crie o arquivo .env.production com:  VITE_PLACAR_PROXY=https://placar.seunome.workers.dev
//   4) Publique de novo. O site passa a usar o seu endereço no lugar da ESPN.
const PERMITIDOS = ['football/nfl', 'basketball/nba']; // acrescente as ligas de futebol depois

export default {
  async fetch(request) {
    const esporte = new URL(request.url).searchParams.get('esporte');
    if (!PERMITIDOS.includes(esporte)) return new Response('esporte inválido', { status: 400 });
    const r = await fetch(`https://site.api.espn.com/apis/site/v2/sports/${esporte}/scoreboard`, {
      cf: { cacheTtl: 30, cacheEverything: true },
    });
    return new Response(r.body, {
      status: r.status,
      headers: { 'content-type': 'application/json', 'access-control-allow-origin': '*', 'cache-control': 'public, max-age=30' },
    });
  },
};
