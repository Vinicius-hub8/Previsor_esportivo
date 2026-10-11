export const pct = (x, d = 0) => (x * 100).toFixed(d).replace('.', ',') + '%';
export const num1 = (x) => x.toFixed(1).replace('.', ',');
export const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

// "2026-10-11" -> Date no fuso local (sem deslocar o dia)
export const parseDate = (s) => {
  const [y, m, d] = s.split('-').map(Number);
  return new Date(y, m - 1, d);
};
export const dayLong = (s) =>
  cap(parseDate(s).toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' }));
export const dayShort = (s) =>
  cap(parseDate(s).toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: '2-digit' }).replace('.', ''));
export const dateBR = (s) => parseDate(s).toLocaleDateString('pt-BR');

// Rótulo da temporada ("2026-27" na NBA). Sem rótulo no JSON, usa a própria chave (NFL: "2026").
export const rotTemp = (meta, s) => meta?.rotulos_temporada?.[s] ?? s;
// Esporte com linha de aposta (NFL) ou sem (NBA).
export const usaLinha = (meta) => meta.usa_linha !== false;
// Número de acerto de destaque de cada esporte.
export const accPrincipal = (meta) => meta.acc_com_linha ?? meta.acc;
export const semanaAtualRotulo = (meta) => meta.semana_rotulo ?? `Semana ${meta.semana_atual}`;

export const record = (v, d, e = 0) => `${v}–${d}${e ? '–' + e : ''}`;

export const confLabel = (q) =>
  q < 0.55 ? 'jogo equilibrado' : q < 0.65 ? 'favorito leve' : q < 0.75 ? 'favorito claro' : 'grande favorito';

export const avisos = (meta) => meta.avisos ?? [
  'Lesões, troca de quarterback, clima e suspensões não entram no modelo.',
  'Quanto mais distante o jogo, menos confiável: a força dos times é medida até hoje e não muda ao longo da projeção.',
  `Jogos sem linha de aposta usam um modelo menos preciso (cerca de ${pct(meta.acc_sem_linha)} de acerto, contra ${pct(meta.acc_com_linha)}).`,
  'A acurácia é uma média de várias temporadas. Numa única rodada, o resultado pode variar bastante.',
  'É um estudo estatístico, não uma recomendação de aposta.',
];
