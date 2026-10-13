import { useEffect, useState } from 'react';

const url = (id) => `${import.meta.env.BASE_URL}dados/futebol/${id}.json`;
const cache = {};

// Carrega o JSON de uma liga de futebol quando ela é aberta (e guarda para não baixar de novo).
export function useLiga(id) {
  const [state, setState] = useState({ data: cache[id] ?? null, loading: !cache[id], error: null });
  useEffect(() => {
    if (!id) return undefined;
    if (cache[id]) {
      setState({ data: cache[id], loading: false, error: null });
      return undefined;
    }
    let vivo = true;
    setState({ data: null, loading: true, error: null });
    fetch(url(id))
      .then((r) => {
        if (!r.ok) throw new Error(`Não achei ${url(id)} (${r.status})`);
        return r.json();
      })
      .then((data) => {
        cache[id] = data;
        if (vivo) setState({ data, loading: false, error: null });
      })
      .catch((e) => vivo && setState({ data: null, loading: false, error: e.message }));
    return () => { vivo = false; };
  }, [id]);
  return state;
}
