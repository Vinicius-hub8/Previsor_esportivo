import { useEffect, useState } from 'react';

const url = (id) => `${import.meta.env.BASE_URL}dados/${id}.json`;

// Carrega o JSON de cada esporte ativo.
export function useSportsData(ids) {
  const [state, setState] = useState({ datas: {}, loading: true, error: null });
  const chave = ids.join(',');

  useEffect(() => {
    let vivo = true;
    Promise.all(
      ids.map((id) =>
        fetch(url(id)).then((r) => {
          if (!r.ok) throw new Error(`Não achei ${url(id)} (${r.status})`);
          return r.json();
        })
      )
    )
      .then((lista) => {
        if (!vivo) return;
        setState({ datas: Object.fromEntries(ids.map((id, i) => [id, lista[i]])), loading: false, error: null });
      })
      .catch((e) => vivo && setState({ datas: {}, loading: false, error: e.message }));
    return () => { vivo = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chave]);

  return state;
}
