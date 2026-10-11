import { Fragment, useEffect, useRef, useState } from 'react';
import GameCard from './GameCard.jsx';
import { dayLong, pct } from '../lib/format.js';

const confianca = (g) => (g.p == null ? 0 : Math.max(g.p, 1 - g.p));
const rotuloSemana = (w, info) =>
  info.tipo === 'REG' ? w : { WC: 'Wild Card', DIV: 'Divisional', CON: 'Conf.', SB: 'Super Bowl' }[info.tipo] || w;

export default function GamesTab({ data, season, week, onSelect }) {
  const { meta, semanas, times } = data;
  const temporadas = Object.keys(semanas).sort().reverse();
  const seasonKey = semanas[season] ? season : String(meta.temporada);
  const weeks = semanas[seasonKey];
  const semanaPadrao = seasonKey === String(meta.temporada) ? String(meta.semana_atual) : Object.keys(weeks)[0];
  const weekKey = weeks[week] ? week : weeks[semanaPadrao] ? semanaPadrao : Object.keys(weeks)[0];
  const info = weeks[weekKey];

  const [ordem, setOrdem] = useState('data');
  const chipsRef = useRef(null);
  useEffect(() => {
    chipsRef.current?.querySelector('[aria-pressed=true]')?.scrollIntoView({ inline: 'center', block: 'nearest' });
  }, [seasonKey, weekKey]);

  const jogos = info.jogos.slice();
  if (ordem === 'conf') jogos.sort((a, b) => confianca(b) - confianca(a));

  const feitos = info.jogos.filter((g) => g.placar);
  const avaliados = feitos.filter((g) => g.ok != null);
  const acertos = avaliados.filter((g) => g.ok).length;
  let resumo;
  if (!feitos.length) resumo = `${info.jogos.length} jogos · palpites ainda sem resultado`;
  else if (feitos.length < info.jogos.length)
    resumo = `${feitos.length} de ${info.jogos.length} jogos já foram disputados · acertos até agora: ${acertos} de ${avaliados.length}`;
  else resumo = `Acertamos ${acertos} de ${avaliados.length} (${pct(acertos / avaliados.length)}) · palpites feitos só com dados anteriores a cada jogo`;

  let ultimoDia = '';
  const cartoes = jogos.map((g) => {
    const novoDia = ordem === 'data' && g.data !== ultimoDia;
    if (novoDia) ultimoDia = g.data;
    return (
      <Fragment key={g.id}>
        {novoDia && <div className="day">{dayLong(g.data)}</div>}
        <GameCard g={g} times={times} />
      </Fragment>
    );
  });

  const temSemLinha = jogos.some((g) => g.p != null && !g.linha);
  const titulo = info.tipo === 'REG' ? `Semana ${weekKey}` : info.rotulo;

  return (
    <>
      <div className="ctrls">
        <div className="seg" role="group" aria-label="Temporada">
          {temporadas.map((s) => (
            <button key={s} aria-pressed={s === seasonKey} onClick={() => onSelect(s)}>{s}</button>
          ))}
        </div>
        <div className="weeks" role="group" aria-label="Semana" ref={chipsRef}>
          {Object.keys(weeks).map((w) => {
            const atual = seasonKey === String(meta.temporada) && Number(w) === meta.semana_atual;
            const nome = weeks[w].tipo === 'REG' ? `Semana ${w}` : weeks[w].rotulo;
            return (
              <button
                key={w}
                className={atual ? 'now' : ''}
                aria-pressed={w === weekKey}
                aria-label={nome + (atual ? ' (atual)' : '')}
                onClick={() => onSelect(seasonKey, w)}
              >
                {rotuloSemana(w, weeks[w])}
              </button>
            );
          })}
        </div>
      </div>

      <div className="wk-head">
        <div>
          <h2>{titulo} · {seasonKey}</h2>
          <div className="sum">{resumo}</div>
        </div>
        <div className="seg" role="group" aria-label="Ordenar">
          <button aria-pressed={ordem === 'data'} onClick={() => setOrdem('data')}>Por data</button>
          <button aria-pressed={ordem === 'conf'} onClick={() => setOrdem('conf')}>Mais confiantes</button>
        </div>
      </div>

      <div className="games">{cartoes}</div>
      {temSemLinha && (
        <p className="note">
          Jogos marcados com “sem linha de aposta” ainda não têm a linha divulgada. Nesses casos o palpite usa o modelo sem ela, que é menos preciso.
        </p>
      )}
    </>
  );
}
