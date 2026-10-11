import { useEffect, useState } from 'react';

const url = (id) => `${import.meta.env.BASE_URL}dados/${id}.json`;

// Carrega o JSON de cada esporte ativo (um que falhe não derruba os outros).
export function useSportsData(ids) {
  const [state, setState] = useState({ datas: {}, loading: true, error: null });
  const chave = ids.join(',');

  useEffect(() => {
    let vivo = true;
    Promise.allSettled(
      ids.map((id) =>
        fetch(url(id)).then((r) => {
          if (!r.ok) throw new Error(`Não achei ${url(id)} (${r.status})`);
          return r.json();
        })
      )
    ).then((res) => {
      if (!vivo) return;
      const datas = {};
      res.forEach((x, i) => { if (x.status === 'fulfilled') datas[ids[i]] = x.value; });
      const falhou = res.find((x) => x.status === 'rejected');
      // só mostra erro se NENHUM esporte carregou; senão o que falhou aparece como "Em breve"
      setState({ datas, loading: false, error: Object.keys(datas).length ? null : falhou?.reason?.message ?? 'erro desconhecido' });
    });
    return () => { vivo = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chave]);

  return state;
}
