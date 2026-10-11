import { useCallback, useEffect, useState } from 'react';
import { store } from './store.js';

// 'light' | 'dark' | null (null = segue o sistema)
export function useTheme() {
  const [theme, setTheme] = useState(() => {
    const t = store.get('pv_theme');
    return t === 'light' || t === 'dark' ? t : null;
  });

  useEffect(() => {
    const root = document.documentElement;
    if (theme) root.dataset.theme = theme;
    else delete root.dataset.theme;
  }, [theme]);

  const toggle = useCallback(() => {
    const atual = theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    const prox = atual === 'dark' ? 'light' : 'dark';
    setTheme(prox);
    store.set('pv_theme', prox);
  }, [theme]);

  return { theme, toggle };
}
