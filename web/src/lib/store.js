// localStorage pode falhar (aba anônima, bloqueio). Por isso tudo em try/catch.
export const store = {
  get(k) {
    try { return localStorage.getItem(k); } catch { return null; }
  },
  set(k, v) {
    try { localStorage.setItem(k, v); } catch { /* ignora */ }
  },
};
