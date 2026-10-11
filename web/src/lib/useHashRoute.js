import { useCallback, useEffect, useState } from 'react';

// Rotas por hash (#/nfl/jogos/2026/5). Funciona em qualquer hospedagem estática
// e permite mandar o link de uma tela específica para alguém.
const read = () => {
  const h = window.location.hash.replace(/^#\/?/, '');
  return h ? h.split('/').map(decodeURIComponent) : [];
};

export function useHashRoute() {
  const [parts, setParts] = useState(read);
  useEffect(() => {
    const on = () => setParts(read());
    window.addEventListener('hashchange', on);
    return () => window.removeEventListener('hashchange', on);
  }, []);
  const navigate = useCallback((...segs) => {
    const clean = segs.filter((s) => s !== undefined && s !== null);
    window.location.hash = '/' + clean.map((s) => encodeURIComponent(s)).join('/');
    window.scrollTo(0, 0);
  }, []);
  return [parts, navigate];
}
