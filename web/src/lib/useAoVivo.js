import { useEffect, useState } from 'react';
import { interpretar, urlPlacar } from './aoVivo.js';

const clamp = (x, a, b) => Math.min(b, Math.max(a, x));

// Consulta o placar de cada esporte e repete: a cada 30 s com jogo em andamento; sem jogo em andamento,
// espera até perto do próximo começo (entre 1 e 30 min). Pausa com a aba escondida. Erros são silenciosos.
export function useAoVivo(esportes) {
  const [live, setLive] = useState({});
  const chave = esportes.map((s) => s.id).join(',');

  useEffect(() => {
    let vivo = true;
    let timer;

    const ciclo = async () => {
      clearTimeout(timer);
      if (document.hidden) {
        timer = setTimeout(ciclo, 60_000);
        return;
      }
      const novo = {};
      let espera = 30 * 60_000;
      await Promise.all(
        esportes.map(async (s) => {
          try {
            const r = await fetch(urlPlacar(s.espn));
            if (!r.ok) throw new Error(String(r.status));
            const mapa = interpretar(await r.json());
            novo[s.id] = mapa;
            const evs = Object.values(mapa);
            if (evs.some((e) => e.estado === 'in')) espera = Math.min(espera, 30_000);
            const prox = evs.filter((e) => e.estado === 'pre' && e.inicio).map((e) => e.inicio - Date.now() - 5 * 60_000);
            if (prox.length) espera = Math.min(espera, clamp(Math.min(...prox), 60_000, 30 * 60_000));
          } catch {
            /* sem placar ao vivo: o site segue com os dados do dia */
          }
        })
      );
      if (!vivo) return;
      if (Object.keys(novo).length) setLive((antes) => ({ ...antes, ...novo }));
      timer = setTimeout(ciclo, espera);
    };

    const volta = () => !document.hidden && ciclo();
    ciclo();
    document.addEventListener('visibilitychange', volta);
    return () => {
      vivo = false;
      clearTimeout(timer);
      document.removeEventListener('visibilitychange', volta);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chave]);

  return live;
}
